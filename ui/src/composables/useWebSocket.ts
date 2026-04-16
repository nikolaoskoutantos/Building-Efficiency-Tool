import { onBeforeUnmount, ref, unref, type Ref } from 'vue'

import { buildWebSocketUrl } from '@/config/api.js'

type MaybeRef<T> = T | Ref<T>

export type WebSocketStatus = 'idle' | 'connecting' | 'authing' | 'running' | 'done' | 'error'

export interface AuthMessage {
  type: 'auth'
  token: string
}

export interface ProgressMessage {
  type: 'progress'
  value: number
}

export interface AlertMessage {
  type: 'alert'
  level: 'info' | 'warning' | 'critical'
  message: string
}

export interface ResultMessage {
  type: 'result'
  data: Record<string, unknown>
}

export interface ErrorMessage {
  type: 'error'
  message: string
  code: string
}

export interface PingMessage {
  type: 'ping'
}

export interface PongMessage {
  type: 'pong'
}

type ServerMessage = ProgressMessage | AlertMessage | ResultMessage | ErrorMessage | PingMessage | PongMessage

const MAX_RETRIES = 5
const BASE_RETRY_DELAY_MS = 1000

export function useWebSocket(taskId: MaybeRef<string>, token: MaybeRef<string | null | undefined>) {
  const progress = ref<number>(0)
  const alerts = ref<AlertMessage[]>([])
  const result = ref<Record<string, unknown> | null>(null)
  const error = ref<ErrorMessage | null>(null)
  const status = ref<WebSocketStatus>('idle')

  let socket: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempts = 0
  let manuallyDisconnected = false

  const clearReconnectTimer = (): void => {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  const resetState = (): void => {
    progress.value = 0
    alerts.value = []
    result.value = null
    error.value = null
  }

  const getResolvedTaskId = (): string => String(unref(taskId))
  const getResolvedToken = (): string | null => {
    const resolvedToken = unref(token)
    return typeof resolvedToken === 'string' && resolvedToken.length > 0 ? resolvedToken : null
  }

  const sendMessage = (message: AuthMessage | PongMessage): void => {
    if (socket?.readyState !== WebSocket.OPEN) {
      return
    }
    socket.send(JSON.stringify(message))
  }

  const scheduleReconnect = (): void => {
    if (manuallyDisconnected || reconnectAttempts >= MAX_RETRIES) {
      return
    }

    const delay = BASE_RETRY_DELAY_MS * 2 ** reconnectAttempts
    reconnectAttempts += 1
    status.value = 'connecting'
    clearReconnectTimer()
    reconnectTimer = setTimeout(() => {
      void connect()
    }, delay)
  }

  const handleServerMessage = (message: ServerMessage): void => {
    switch (message.type) {
      case 'ping':
        sendMessage({ type: 'pong' })
        break
      case 'pong':
        break
      case 'progress':
        progress.value = message.value
        status.value = 'running'
        break
      case 'alert':
        alerts.value = [...alerts.value, message]
        if (status.value === 'authing' || status.value === 'connecting' || status.value === 'idle') {
          status.value = 'running'
        }
        break
      case 'result':
        result.value = message.data
        status.value = 'done'
        break
      case 'error':
        error.value = message
        status.value = 'error'
        break
    }
  }

  const disconnect = (): void => {
    manuallyDisconnected = true
    clearReconnectTimer()

    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close(1000, 'Client disconnect')
    }

    socket = null
    if (status.value !== 'done' && status.value !== 'error') {
      status.value = 'idle'
    }
  }

  const connect = async (): Promise<void> => {
    const resolvedToken = getResolvedToken()
    const resolvedTaskId = getResolvedTaskId()

    if (!resolvedTaskId) {
      error.value = { type: 'error', message: 'Missing task identifier.', code: 'missing_task_id' }
      status.value = 'error'
      return
    }

    if (!resolvedToken) {
      error.value = { type: 'error', message: 'Missing authentication token.', code: 'missing_token' }
      status.value = 'error'
      return
    }

    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      return
    }

    manuallyDisconnected = false
    clearReconnectTimer()
    resetState()
    status.value = 'connecting'

    const url = buildWebSocketUrl(`/ws/${encodeURIComponent(resolvedTaskId)}`)
    socket = new WebSocket(url)

    socket.onopen = () => {
      reconnectAttempts = 0
      status.value = 'authing'
      sendMessage({ type: 'auth', token: resolvedToken })
    }

    socket.onmessage = (event: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(event.data) as ServerMessage
        handleServerMessage(parsed)
      } catch {
        error.value = { type: 'error', message: 'Received malformed websocket payload.', code: 'invalid_json' }
        status.value = 'error'
      }
    }

    socket.onerror = () => {
      if (status.value !== 'done') {
        status.value = 'error'
      }
    }

    socket.onclose = (event: CloseEvent) => {
      socket = null

      if (manuallyDisconnected) {
        return
      }

      if (event.code === 4001) {
        error.value = {
          type: 'error',
          message: event.reason || 'WebSocket authentication failed.',
          code: 'auth_error',
        }
        status.value = 'error'
        return
      }

      if (status.value === 'done' && event.code === 1000) {
        return
      }

      if (status.value !== 'error') {
        error.value = {
          type: 'error',
          message: event.reason || 'WebSocket closed unexpectedly.',
          code: `close_${event.code}`,
        }
        status.value = 'error'
      }

      scheduleReconnect()
    }
  }

  onBeforeUnmount(() => {
    disconnect()
  })

  return {
    connect,
    disconnect,
    progress,
    alerts,
    result,
    error,
    status,
  }
}
