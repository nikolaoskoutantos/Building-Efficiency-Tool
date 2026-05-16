import { defineStore } from 'pinia'
import { buildApiUrl } from '@/config/api.js'
import { useAuthStore } from '@/stores/auth.js'

function isValidTimeLabel(value) {
  return typeof value === 'string' && /^([01]\d|2[0-3]):[0-5]\d$/.test(value)
}

function timeLabelToMinutes(value) {
  const [hours, minutes] = value.split(':').map(Number)
  return hours * 60 + minutes
}

function minutesToTimeLabel(totalMinutes) {
  const normalized = ((totalMinutes % 1440) + 1440) % 1440
  const hours = Math.floor(normalized / 60)
  const minutes = normalized % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

function mapRowsToTimeline(rows) {
  if (!Array.isArray(rows)) {
    return []
  }

  const normalizedRows = rows
    .filter(row => isValidTimeLabel(row?.start) && isValidTimeLabel(row?.end))
    .map((row, index) => ({
      id: row.id ?? `${row.start}-${row.end}-${index}`,
      start: row.start,
      end: row.end,
      enabled: row.enabled !== false,
      setpoint: row?.enabled === false ? null : (row?.setpoint ?? null),
      start_ts: row?.start_ts ?? null,
      end_ts: row?.end_ts ?? null,
    }))

  const timelineRows = []
  let dayOffset = 0
  let previousStartMinutes = null

  for (const row of normalizedRows) {
    const rawStartMinutes = timeLabelToMinutes(row.start)
    const rawEndMinutes = timeLabelToMinutes(row.end)

    if (previousStartMinutes !== null && rawStartMinutes < previousStartMinutes) {
      dayOffset += 1440
    }

    const startMinutes = rawStartMinutes + dayOffset
    let endMinutes = rawEndMinutes + dayOffset
    if (rawEndMinutes <= rawStartMinutes) {
      endMinutes += 1440
    }

    timelineRows.push({
      ...row,
      startMinutes,
      endMinutes,
    })
    previousStartMinutes = rawStartMinutes
  }

  return timelineRows
}

function mergeScheduleRows(rows) {
  const timelineRows = mapRowsToTimeline(rows)
  const mergedRows = []
  for (const row of timelineRows) {
    const candidate = { ...row }
    const previous = mergedRows.at(-1)

    // If a later row overlaps an earlier one, clip or drop it so the UI
    // always renders the minimum non-overlapping set of periods.
    if (previous && candidate.startMinutes < previous.endMinutes) {
      if (candidate.endMinutes <= previous.endMinutes) {
        continue
      }
      candidate.startMinutes = previous.endMinutes
    }

    if (
      previous?.enabled === candidate.enabled &&
      (previous?.enabled === false || previous?.setpoint === candidate.setpoint) &&
      candidate.startMinutes <= (previous?.endMinutes ?? -1)
    ) {
      previous.endMinutes = Math.max(previous.endMinutes, candidate.endMinutes)
      continue
    }
    mergedRows.push(candidate)
  }

  return mergedRows.map((row, index) => ({
    id: row.id ?? `${row.startMinutes}-${row.endMinutes}-${index}`,
    start: minutesToTimeLabel(row.startMinutes),
    end: minutesToTimeLabel(row.endMinutes),
    enabled: row.enabled,
    setpoint: row.enabled === false ? null : (row.setpoint ?? null),
    start_ts: row.start_ts ?? null,
    end_ts: row.end_ts ?? null,
  }))
}

function normalizeRawScheduleRows(rows) {
  return mapRowsToTimeline(rows).map((row, index) => ({
    id: row.id ?? `${row.startMinutes}-${row.endMinutes}-${index}`,
    start: minutesToTimeLabel(row.startMinutes),
    end: minutesToTimeLabel(row.endMinutes),
    enabled: row.enabled,
    setpoint: row.enabled === false ? null : (row.setpoint ?? null),
    start_ts: row.start_ts ?? null,
    end_ts: row.end_ts ?? null,
  }))
}

export const useControlStore = defineStore('control', {
  state: () => ({
    rawSchedule: [],
    scheduleLoaded: false,
    preferences: {
      switchValue: false,
      slider1: 21,
      slider2: 50,
    },
    zoneSetpoints: {},   // { [zone_id]: number } — persists per-zone setpoint across views
  }),
  getters: {
    schedule: (state) => mergeScheduleRows(state.rawSchedule),
    editableSchedule: (state) => normalizeRawScheduleRows(state.rawSchedule),
    getZoneSetpoint: (state) => (zoneId) =>
      zoneId != null && state.zoneSetpoints[zoneId] != null
        ? state.zoneSetpoints[zoneId]
        : state.preferences.slider1,
  },
  actions: {
    setRawSchedule(newSchedule) {
      this.rawSchedule = normalizeRawScheduleRows(newSchedule)
      this.scheduleLoaded = true
    },
    setSchedule(newSchedule) {
      this.rawSchedule = normalizeRawScheduleRows(newSchedule)
      this.scheduleLoaded = true
    },
    clearSchedule() {
      this.rawSchedule = []
      this.scheduleLoaded = false
    },
    clearZoneSetpoints() {
      this.zoneSetpoints = {}
    },
    setPreferences(prefs) {
      this.preferences = { ...this.preferences, ...prefs }
    },
    /**
     * Update the setpoint from any view (dashboard or topology) and persist to the schedule DB.
     * Both the slider value and the schedule rows are kept in sync.
     */
    async saveSetpointToSchedule({ buildingId, unitId, zoneId, value }) {
      // 1. Update per-zone setpoint only — never write preferences.slider1 here.
      //    The dashboard slider owns preferences.slider1; writing it from here
      //    causes cross-zone contamination when there are no schedule rows.
      if (zoneId != null) {
        this.zoneSetpoints = { ...this.zoneSetpoints, [zoneId]: Number(value) }
      }

      // 2. Update schedule rows if a schedule is already loaded
      if (this.scheduleLoaded && this.rawSchedule.length > 0) {
        const updated = this.editableSchedule.map(row => ({
          ...row,
          setpoint: row.enabled ? Number(value) : null,
        }))
        this.setRawSchedule(updated)
      }

      // 3. Persist to DB via the same endpoint the dashboard uses
      const authStore = useAuthStore()
      const token = authStore.getJwtToken ? authStore.getJwtToken() : authStore.jwtToken
      const params = new URLSearchParams()
      if (unitId) params.set('unit_id', String(unitId))
      if (zoneId)  params.set('zone_id',  String(zoneId))
      const query = params.toString() ? `?${params.toString()}` : ''

      // If no schedule rows exist yet, create a default full-day enabled row
      // so the setpoint is always persisted even before the user configures a schedule.
      const rows = (this.scheduleLoaded && this.rawSchedule.length > 0)
        ? this.editableSchedule
        : [{ start: '00:00', end: '23:59', enabled: true, setpoint: Number(value) }]

      const res = await fetch(buildApiUrl(`/dashboard/hvac-schedule/${buildingId}${query}`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: 'include',
        body: JSON.stringify({
          reference_time: new Date().toISOString(),
          future_hours: 12,
          rows,
        }),
      })

      if (!res.ok) throw new Error(`Failed to save setpoint: ${res.status}`)
      const payload = await res.json()
      if (payload.rows) this.setRawSchedule(payload.rows)
      return payload
    },

    /**
     * Returns a 24-hour array (0-23) with true/false for each hour, based on the current schedule.
     * All hours are off (false) by default. If a schedule row is enabled and covers an hour, that hour is set to true.
     * Start/end times are rounded down/up to the nearest hour.
     */
    get24HourSchedule() {
      // Start with all hours off
      const hours = new Array(24).fill(false)
      for (const row of this.schedule) {
        if (!row.enabled) continue
        // Parse start and end, round to nearest hour
        const [startH, startM] = row.start.split(':').map(Number)
        const [endH, endM] = row.end.split(':').map(Number)
        let startHour = startM >= 30 ? (startH + 1) % 24 : startH
        let endHour = endM >= 30 ? (endH + 1) % 24 : endH
        // If endHour <= startHour, treat as next day (not supported, so clamp to 24)
        if (endHour <= startHour) endHour = 24
        for (let h = startHour; h < endHour; h++) {
          hours[h % 24] = true
        }
      }
      return hours
    },
  },
})
