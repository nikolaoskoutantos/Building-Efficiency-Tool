import { defineStore } from 'pinia'

export const useControlStore = defineStore('control', {
  state: () => ({
    // ...other state...
    schedule: [],
    preferences: {
      switchValue: false,
      slider1: 50,
      slider2: 50,
    },
  }),
  actions: {
    setSchedule(newSchedule) {
      this.schedule = newSchedule
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