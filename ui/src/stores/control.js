import { defineStore } from 'pinia'

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
    const previous = mergedRows[mergedRows.length - 1]

    // If a later row overlaps an earlier one, clip or drop it so the UI
    // always renders the minimum non-overlapping set of periods.
    if (previous && candidate.startMinutes < previous.endMinutes) {
      if (candidate.endMinutes <= previous.endMinutes) {
        continue
      }
      candidate.startMinutes = previous.endMinutes
    }

    if (
      previous &&
      previous.enabled === candidate.enabled &&
      (previous.enabled === false || previous.setpoint === candidate.setpoint) &&
      candidate.startMinutes <= previous.endMinutes
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
  }))
}

function normalizeRawScheduleRows(rows) {
  return mapRowsToTimeline(rows).map((row, index) => ({
    id: row.id ?? `${row.startMinutes}-${row.endMinutes}-${index}`,
    start: minutesToTimeLabel(row.startMinutes),
    end: minutesToTimeLabel(row.endMinutes),
    enabled: row.enabled,
    setpoint: row.enabled === false ? null : (row.setpoint ?? null),
  }))
}

function expandScheduleRows(rows, stepMinutes = 5) {
  const timelineRows = mapRowsToTimeline(rows)
  const expandedRows = []

  for (const row of timelineRows) {
    for (let cursor = row.startMinutes; cursor < row.endMinutes; cursor += stepMinutes) {
      const nextCursor = Math.min(cursor + stepMinutes, row.endMinutes)
      expandedRows.push({
        id: `${cursor}-${nextCursor}-${row.enabled ? 1 : 0}`,
        start: minutesToTimeLabel(cursor),
        end: minutesToTimeLabel(nextCursor),
        enabled: row.enabled,
        setpoint: row.enabled === false ? null : (row.setpoint ?? null),
      })
    }
  }

  return expandedRows
}

export const useControlStore = defineStore('control', {
  state: () => ({
    // ...other state...
    rawSchedule: [],
    scheduleLoaded: false,
    preferences: {
      switchValue: false,
      slider1: 50,
      slider2: 50,
    },
  }),
  getters: {
    schedule: (state) => mergeScheduleRows(state.rawSchedule),
  },
    actions: {
    setRawSchedule(newSchedule) {
      this.rawSchedule = normalizeRawScheduleRows(newSchedule)
      this.scheduleLoaded = true
      },
    setSchedule(newSchedule) {
      this.rawSchedule = expandScheduleRows(newSchedule)
      this.scheduleLoaded = true
      },
    setPreferences(prefs) {
      this.preferences = { ...this.preferences, ...prefs }
    },
    // ...other actions...
    /**
     * Returns a 24-hour array (0-23) with true/false for each hour, based on the current schedule.
     * All hours are off (false) by default. If a schedule row is enabled and covers an hour, that hour is set to true.
     * Start/end times are rounded down/up to the nearest hour.
     */
    get24HourSchedule() {
      // Start with all hours off
      const hours = Array(24).fill(false)
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
