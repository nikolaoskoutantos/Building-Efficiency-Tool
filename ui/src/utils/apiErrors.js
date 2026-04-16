export function extractApiErrorMessage(payload, fallbackMessage = 'Request failed.') {
  if (!payload) {
    return fallbackMessage
  }

  if (typeof payload.detail === 'string') {
    return payload.detail
  }

  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map((entry) => {
        if (typeof entry === 'string') {
          return entry
        }
        if (entry && typeof entry === 'object') {
          const prefix = Array.isArray(entry.loc) ? `${entry.loc.join('.')}: ` : ''
          return `${prefix}${entry.msg || entry.message || JSON.stringify(entry)}`
        }
        return String(entry)
      })
      .join('; ')
  }

  if (typeof payload.message === 'string') {
    return payload.message
  }

  return fallbackMessage
}

export function buildRoleAwareErrorMessage(status, payload, fallbackMessage) {
  if (status === 401) {
    return 'Authentication required. Please log in again.'
  }

  if (status === 403) {
    const detail = extractApiErrorMessage(payload, '')
    if (detail.includes('Access requires one of')) {
      return 'Your current role does not have permission for this action.'
    }
    return detail || 'You do not have permission to access this feature.'
  }

  return extractApiErrorMessage(payload, fallbackMessage)
}

export async function parseApiErrorResponse(response, fallbackMessage = 'Request failed.') {
  const rawText = await response.text()

  try {
    const payload = JSON.parse(rawText)
    return buildRoleAwareErrorMessage(response.status, payload, fallbackMessage)
  } catch {
    if (response.status === 401) {
      return 'Authentication required. Please log in again.'
    }
    if (response.status === 403) {
      return 'Your current role does not have permission for this action.'
    }
    return rawText || fallbackMessage || `HTTP ${response.status}: ${response.statusText}`
  }
}

export function normalizeRole(role) {
  if (!role) {
    return ''
  }
  return String(role).replace('Role.', '').toUpperCase()
}
