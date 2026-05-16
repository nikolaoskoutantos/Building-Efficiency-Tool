<template>
  <div class="efficiency-tool-page">
    <CRow class="mb-4" :xs="{ gutter: 4 }">
      <CCol :sm="4">
        <CWidgetStatsA color="primary" class="hero-widget hero-widget--indoor">
          <template #value>
            <div class="hero-value">
              <div>
                <span class="hero-number">{{ indoorTemp ?? '--' }}°C</span>
                <span class="hero-badge">Live</span>
              </div>
            </div>
          </template>
          <template #title>
            <div class="hero-title-wrap">
              <div class="hero-title">Indoor Temperature</div>
              <img src="/indoor-temp-icon.svg" alt="" class="hero-ornament hero-ornament--indoor" />
            </div>
          </template>
        </CWidgetStatsA>
      </CCol>
      <CCol :sm="4">
        <CWidgetStatsA color="info" class="hero-widget hero-widget--outdoor">
          <template #value>
            <div class="hero-value">
              <div>
                <span class="hero-number">{{ outdoorTemp ?? '--' }}°C</span>
                <span class="hero-badge">Ambient</span>
              </div>
            </div>
          </template>
          <template #title>
            <div class="hero-title-wrap">
              <div class="hero-title">Outdoor Temperature</div>
              <img src="/outdoor-temp-icon.svg" alt="" class="hero-ornament hero-ornament--outdoor" />
            </div>
          </template>
        </CWidgetStatsA>
      </CCol>
      <CCol :sm="4">
        <CWidgetStatsA color="warning" class="hero-widget hero-widget--forecast">
          <template #value>
            <div class="hero-value">
              <div>
                <span class="hero-number">{{ forecastTemp ?? '--' }}°C</span>
                <span class="hero-badge">Next Hour</span>
              </div>
            </div>
          </template>
          <template #title>
            <div class="hero-title-wrap">
              <div class="hero-title">Forecast Outlook</div>
              <img src="/forecast-icon.svg" alt="" class="hero-ornament hero-ornament--forecast" />
            </div>
          </template>
        </CWidgetStatsA>
      </CCol>
    </CRow>
    <CRow class="mb-4">
      <CCol :sm="6">
        <CWidgetStatsD
          class="mb-4 summary-widget summary-widget--energy"
          :values="energySummaryValues"
        >
          <template #icon>
            <img src="/energy-svgrepo-com.svg" alt="Energy" height="52" class="my-4" />
          </template>
        </CWidgetStatsD>
      </CCol>
      <CCol :sm="6">
        <CWidgetStatsD
          class="mb-4 summary-widget summary-widget--reward"
          :values="rewardSummaryValues"
        >
          <template #icon>
            <img src="/reward-svgrepo-com.svg" alt="Reward" height="52" class="my-4" />
          </template>
        </CWidgetStatsD>
      </CCol>
    </CRow>
    <!-- Card with CoreUI Switch and Text Pill moved after widgets -->
    <CCard class="mb-4 control-panel-card">
      <CCardBody>
        <div class="control-block-responsive">
          <div class="control-row">
            <div class="switch-col">
              <CFormSwitch size="xl" v-model="switchValue" :color="switchValue ? 'success' : 'danger'" />
              <span :class="['badge', 'rounded-pill', switchValue ? 'bg-success' : 'bg-danger', 'text-light', 'mt-2']">
                Switch is {{ switchValue ? 'On' : 'Off' }}
                <span style="font-weight: bold; color: #fff; font-size: 1.2em; margin-left: 0.3em;" v-c-tooltip="{ content: 'If you choose to turn off heating for 30 minutes you will achieve 30% more energy efficiency', placement: 'top' }">&#33;</span>
              </span>
            </div>
            <div class="button-group-col">
              <div class="button-group-flex">
                <CDropdown class="me-2" :autoClose="false" placement="right-start">
                  <CDropdownToggle color="secondary" outline>{{ dropdownLabel() }}</CDropdownToggle>
                  <CDropdownMenu class="p-3" style="min-width: 200px;">
                    <div v-for="service in availableServices" :key="service.value" class="form-check mb-2">
                      <input
                        class="form-check-input"
                        type="checkbox"
                        :id="service.value"
                        :checked="isChecked(service.value)"
                        @change="toggleService(service.value)"
                      >
                      <label class="form-check-label" :style="{ color: isChecked(service.value) ? '#4f46e5' : '#888' }" :for="service.value">
                        {{ service.label }}
                      </label>
                    </div>
                  </CDropdownMenu>
                </CDropdown>
                <RatingOne />
              </div>
            </div>
          </div>
          <div class="slider-row-responsive">
            <SetpointSlider v-model="slider1" :min="16" :max="30" label="Indoor Setpoint" />
          </div>
        </div>
      </CCardBody>
    </CCard>
    <HvacScheduleTable
      :optimize-loading="optimizeLoading"
      :optimize-disabled="!canOptimize"
      :optimize-button-label="optimizeButtonLabel"
      :schedule-saving="scheduleSaving"
      :schedule-save-message="scheduleSaveMessage"
      :devices="activeBuildingDevices"
      :selected-device-id="selectedDeviceId"
      :zones="zones"
      :selected-zone-id="selectedZoneId"
      :show-zone-selector="showZoneSelector"
      :current-setpoint="slider1"
      @optimize="runOptimization"
      @schedule-change="handleScheduleChange"
      @device-change="handleDeviceChange"
      @zone-change="handleZoneChange"
    />
    <CAlert
      v-if="optimizationReadinessMessage"
      color="warning"
      dismissible
      class="my-3"
      @close="dismissOptimizationReadiness = true"
    >
      {{ optimizationReadinessMessage }}
    </CAlert>
    <div v-if="optimizeLoading" class="d-flex justify-content-center align-items-center my-3">
      <CSpinner color="primary" size="lg" />
      <span class="ms-3">{{ optimizeStatus || 'Optimizing HVAC control...' }}</span>
    </div>
    <CAlert
      v-if="optimizeError"
      color="danger"
      dismissible
      class="my-3"
      @close="optimizeError = ''"
    >
      {{ optimizeError }}
    </CAlert>
    <CAlert
      v-if="showOptimizeAlert"
      color="success"
      dismissible
      class="my-3"
      @close="showOptimizeAlert = false"
    >
      {{ optimizeSuccessMessage }}
    </CAlert>
    <div class="chart-wrapper">
      <!-- Spinner overlay — shown while time grid or schedule is loading -->
      <Transition name="chart-overlay">
        <div v-if="chartLoading" class="chart-overlay" aria-hidden="true">
          <div class="chart-overlay__backdrop" />
          <div class="chart-overlay__spinner">
            <svg class="chart-spinner-ring" viewBox="0 0 44 44" xmlns="http://www.w3.org/2000/svg">
              <circle class="chart-spinner-ring__track" cx="22" cy="22" r="18" fill="none" stroke-width="3.5" />
              <circle class="chart-spinner-ring__arc"   cx="22" cy="22" r="18" fill="none" stroke-width="3.5"
                stroke-dasharray="90 200" stroke-linecap="round" />
            </svg>
            <span class="chart-overlay__label">Loading data…</span>
          </div>
        </div>
      </Transition>

      <!-- Chart — fades to 35% while loading so the overlay reads clearly -->
      <div :class="['chart-canvas-host', { 'chart-canvas-host--loading': chartLoading }]">
        <CChartLine :key="chartKey" :data="chartData" :options="chartOptions" style="width:100%;height:100%;" />
      </div>
    </div>
    <EnergyBarChart class="mb-4" />
  </div>
</template>

<script setup>
import { CChartLine } from '@coreui/vue-chartjs'
import RatingOne from '@/components/Rating.vue'
import SetpointSlider from '@/components/SetpointSlider.vue'
import EnergyBarChart from '@/components/EnergyBarChart.vue'
import HvacScheduleTable from '@/components/HvacScheduleTable.vue'
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { CRow, CCol, CWidgetStatsA, CCard, CCardBody, CFormSwitch, CDropdown, CDropdownToggle, CDropdownMenu, CSpinner, CAlert } from '@coreui/vue'
import { useThemeStore } from '@/stores/theme.js'
import { useControlStore } from '@/stores/control.js'
import { useAlertsStore } from '@/stores/alerts.js'
import { useDashboardStore } from '@/stores/dashboard.js'
import { useAuthStore } from '@/stores/auth.js'
import { buildApiUrl } from '@/config/api.js'

const controlStore = useControlStore()
const alertsStore = useAlertsStore()
const dashboardStore = useDashboardStore()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const isDarkTheme = computed(() => themeStore.theme === 'dark')

const chartKey = ref(0)

const optimizedControl = ref([]) // Array of 12 true/false
const optimizedIndoorForecast = ref([]) // Array of 12 numbers
const optimizeLoading = ref(false)
const showOptimizeAlert = ref(false)
const optimizeError = ref('')
const optimizeStatus = ref('')
const optimizationResult = ref(null)
const scheduleSaving = ref(false)
const scheduleSaveMessage = ref('')
const dismissOptimizationReadiness = ref(false)
const scheduleReloading = ref(false)
const chartLoading = computed(() =>
  scheduleReloading.value || dashboardStore.efficiencyTimeGrid.loading === true
)
const dashboardTimeGridRows = computed(() => dashboardStore.efficiencyTimeGrid.rows || [])
const dashboardTimeGridCurrentRow = computed(() => dashboardStore.efficiencyTimeGrid.currentRow || null)
const dashboardReferenceTime = computed(() => dashboardStore.efficiencyTimeGrid.referenceTime || null)
const optimizationContext = computed(() => dashboardStore.efficiencyTimeGrid.optimizationContext || null)
const activeBuildingDevices = computed(() => dashboardStore.activeBuildingDevices)
const selectedDeviceId = computed(() => dashboardStore.activeDevice?.id ?? null)
const zones = computed(() => dashboardStore.zones)
const selectedZoneId = computed(() => dashboardStore.activeZone?.id ?? null)
const showZoneSelector = computed(() => dashboardStore.showZoneSelector)
let scheduleSaveTimeout = null
let scheduleSaveMessageTimeout = null
let scheduleSaveRequestSequence = 0
const syncingTopControls = ref(false)
const optimizationRequestTimeoutMs = 120000

// Stable schedule ref for the chart — only updates when the schedule *structure* changes
// (start/end/enabled/timestamps), not when setpoints change. This breaks the reactive
// dependency between slider1 saves and chartData, preventing unnecessary chart redraws.
const chartSchedule = ref([])
watch(
  () => controlStore.editableSchedule
    .map(r => `${r.start}|${r.end}|${r.enabled ? '1' : '0'}|${r.start_ts ?? ''}|${r.end_ts ?? ''}`)
    .join(','),
  () => {
    chartSchedule.value = controlStore.editableSchedule.map(row => ({
      start: row.start,
      end: row.end,
      enabled: row.enabled,
      start_ts: row.start_ts,
      end_ts: row.end_ts,
    }))
  },
  { immediate: true },
)
const scheduleWindowHours = 12

function formatDateForApi(dateString) {
  const date = new Date(dateString.replace(' ', 'T'))
  const pad = (value) => String(value).padStart(2, '0')
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function serializeScheduleRowsForApi(rows) {
  if (!Array.isArray(rows)) {
    return []
  }

  return rows.map((row) => {
    let numericId
    if (Number.isInteger(row?.id)) {
      numericId = row.id
    } else if (typeof row?.id === 'string' && /^\d+$/.test(row.id)) {
      numericId = Number(row.id)
    }

    return {
      ...(numericId === undefined ? {} : { id: numericId }),
      start: row?.start,
      end: row?.end,
      enabled: row?.enabled !== false,
      setpoint: row?.enabled === false ? null : Number(row?.setpoint ?? slider1.value ?? null),
    }
  })
}

function areScheduleRowsEquivalent(currentRows, incomingRows) {
  if (!Array.isArray(currentRows) || !Array.isArray(incomingRows) || currentRows.length !== incomingRows.length) {
    return false
  }

  const normalizeSetpoint = (row) => {
    if (row?.enabled === false) {
      return null
    }
    const value = row?.setpoint
    return value == null ? null : Number(value)
  }

  return currentRows.every((row, index) => {
    const incoming = incomingRows[index]
    if (!incoming) {
      return false
    }

    return (
      row?.start === incoming?.start &&
      row?.end === incoming?.end &&
      (row?.enabled !== false) === (incoming?.enabled !== false) &&
      normalizeSetpoint(row) === normalizeSetpoint(incoming)
    )
  })
}

function toFiniteNumber(value) {
  const n = +value
  return Number.isFinite(n) ? n : null
}

function energyRawToKwh(value) {
  const n = +value
  return Number.isFinite(n) ? n / 1000 : null
}

function formatEnergyValue(value) {
  return value == null ? '--' : `${value.toFixed(2)} kWh`
}

function formatPercentValue(value) {
  return value == null ? '--' : `${value.toFixed(1)}%`
}

function formatTemperatureDelta(value) {
  return value == null ? '--' : `${value.toFixed(2)}°C`
}

function formatRecommendationLabel(value) {
  if (!value) {
    return 'Awaiting run'
  }

  return String(value)
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

const optimizationSummary = computed(() => {
  const result = optimizationResult.value
  if (!result) {
    return null
  }

  const baselineAllOnKwh = energyRawToKwh(result?.baseline_all_on?.energy_consumption)
  const baselineAllOffKwh = energyRawToKwh(result?.baseline_all_off?.energy_consumption)
  const optimizedConsumptionKwh = energyRawToKwh(
    result?.energy_consumption ?? result?.optimized_candidate?.energy_consumption,
  )
  const savedKwh =
    baselineAllOnKwh != null && optimizedConsumptionKwh != null
      ? Math.max(baselineAllOnKwh - optimizedConsumptionKwh, 0)
      : null
  const savedPercentage =
    toFiniteNumber(result?.savings_percentage) ??
    (baselineAllOnKwh != null && optimizedConsumptionKwh != null && baselineAllOnKwh > 0
      ? ((baselineAllOnKwh - optimizedConsumptionKwh) / baselineAllOnKwh) * 100
      : null)
  const averageDeviation = toFiniteNumber(result?.avg_deviation_from_setpoint)
  const recommendedOperation = Array.isArray(result?.recommended_operation)
    ? result.recommended_operation.slice(0, 12).map(value => !!value)
    : []

  return {
    baselineAllOnKwh,
    baselineAllOffKwh,
    optimizedConsumptionKwh,
    savedKwh,
    savedPercentage,
    averageDeviation,
    strategy: result?.recommendation_type || null,
    activeIntervals: recommendedOperation.filter(Boolean).length,
  }
})

const energySummaryValues = computed(() => [
  {
    title: 'Baseline Next Hour',
    value: formatEnergyValue(optimizationSummary.value?.baselineAllOnKwh),
  },
  {
    title: 'Recommended Next Hour',
    value: formatEnergyValue(optimizationSummary.value?.optimizedConsumptionKwh),
  },
])

const rewardSummaryValues = computed(() => [
  {
    title: 'Estimated Savings',
    value:
      optimizationSummary.value?.savedKwh == null
        ? '--'
        : `${formatEnergyValue(optimizationSummary.value.savedKwh)} (${formatPercentValue(optimizationSummary.value.savedPercentage)})`,
  },
  {
    title: 'Avg Comfort Drift',
    value: formatTemperatureDelta(optimizationSummary.value?.averageDeviation),
  },
])

const optimizeSuccessMessage = computed(() => {
  if (!optimizationSummary.value) {
    return 'Your optimal HVAC control is ready!'
  }

  const scheduleMinutes = optimizationSummary.value.activeIntervals * 5
  const savingsText =
    optimizationSummary.value.savedKwh == null
      ? 'Optimization completed'
      : `${formatEnergyValue(optimizationSummary.value.savedKwh)} saved`

  return `${savingsText} with ${scheduleMinutes} minutes scheduled on (${formatRecommendationLabel(optimizationSummary.value.strategy)}).`
})

const missingOptimizationFields = computed(() => {
  const fields = optimizationContext.value?.missing_fields || []
  // slider1 always provides a valid setpoint that is sent with the optimization request,
  // so never block or warn on hvac_setpoint when slider1 has a finite value.
  return Number.isFinite(slider1.value)
    ? fields.filter(f => f !== 'hvac_setpoint')
    : fields
})
const optimizationReadinessMessage = computed(() => {
  if (dismissOptimizationReadiness.value || missingOptimizationFields.value.length === 0) {
    return ''
  }

  const labels = missingOptimizationFields.value.map((field) => {
    if (field === 'temperature') return 'indoor temperature'
    if (field === 'hvac_setpoint') return 'HVAC setpoint'
    if (field === 'outdoor_temperatures') return 'outdoor forecast'
    if (field === 'ts') return 'reference time'
    return field.replaceAll('_', ' ')
  })

  return `Optimization is waiting for ${labels.join(', ')} before it can run.`
})

function getDatasetByLabelFragment(fragment) {
  return chartData.value.datasets.find(dataset => dataset.label.includes(fragment))
}

function getStartingTemperature() {
  if (optimizationContext.value?.starting_temperature != null) {
    return Number(optimizationContext.value.starting_temperature)
  }
  const indoorDataset = getDatasetByLabelFragment('Indoor Temperature')
  const source = indoorDataset?.data || []
  for (let i = pastPoints - 1; i >= 0; i -= 1) {
    if (typeof source[i] === 'number') {
      return Number(source[i].toFixed(3))
    }
  }
  return Number.parseFloat(indoorTemp.value) || 24.5
}

function getOutdoorTemperaturesForOptimization() {
  if (optimizationContext.value?.outdoor_temperatures?.length) {
    return optimizationContext.value.outdoor_temperatures.map(Number)
  }
  const weatherDataset = getDatasetByLabelFragment('Outdoor Temperature')
  const forecastDataset = getDatasetByLabelFragment('Forecast')
  const weatherData = weatherDataset?.data || []
  const forecastData = forecastDataset?.data || []
  const values = []

  const currentOutdoor = weatherData[pastPoints - 1]
  values.push(typeof currentOutdoor === 'number' ? Number(currentOutdoor.toFixed(3)) : 22)

  for (let i = 0; i < 12; i += 1) {
    const forecastValue = forecastData[pastPoints + i]
    values.push(typeof forecastValue === 'number' ? Number(forecastValue.toFixed(3)) : values[values.length - 1])
  }

  return values
}

  function getOptimizationPayload() {
    const buildingId = dashboardStore.activeBuilding?.id
    if (!buildingId) {
      throw new Error('No building is selected for optimization.')
    }

    const deviceId = dashboardStore.activeDevice?.id ?? null
    const activeZoneId = dashboardStore.activeZone?.id ?? null

    return {
      building_id: buildingId,
      ...(deviceId == null ? {} : { device_id: deviceId }),
      ...(activeZoneId == null ? {} : { zone_id: activeZoneId }),
      starting_temperature: getStartingTemperature(),
      starting_time: optimizationContext.value?.starting_time || formatDateForApi(chartLabels[pastPoints]),
      outdoor_temperatures: getOutdoorTemperaturesForOptimization(),
      setpoint: Number(slider1.value),
      duration: optimizationContext.value?.duration || 12,
      optimization_type: optimizationContext.value?.optimization_type || 'normal',
    }
  }

  function getScheduleSetpoint(rows) {
    if (!Array.isArray(rows)) {
      return null
    }

    const firstEnabledWithSetpoint = rows.find((row) => row?.enabled && row?.setpoint != null)
    if (!firstEnabledWithSetpoint) {
      return null
    }

    const numericSetpoint = Number(firstEnabledWithSetpoint.setpoint)
    return Number.isFinite(numericSetpoint) ? numericSetpoint : null
  }

  const APP_TIME_ZONE = 'Europe/Athens'

  function getTimeZoneParts(value, timeZone = APP_TIME_ZONE) {
    const date = value instanceof Date ? value : new Date(value)
    if (Number.isNaN(date.getTime())) {
      return null
    }

    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })

    const parts = Object.fromEntries(
      formatter
        .formatToParts(date)
        .filter((part) => part.type !== 'literal')
        .map((part) => [part.type, part.value]),
    )

    return {
      year: Number(parts.year),
      month: Number(parts.month),
      day: Number(parts.day),
      hour: Number(parts.hour),
      minute: Number(parts.minute),
    }
  }

  function buildDateFromTimeZoneParts(parts, timeZone = APP_TIME_ZONE) {
    const utcGuess = new Date(Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute, 0, 0))
    const zonedGuess = getTimeZoneParts(utcGuess, timeZone)
    if (!zonedGuess) {
      return utcGuess
    }

    const targetUtcMinutes = Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute) / 60000
    const zonedUtcMinutes = Date.UTC(
      zonedGuess.year,
      zonedGuess.month - 1,
      zonedGuess.day,
      zonedGuess.hour,
      zonedGuess.minute,
    ) / 60000

    return new Date(utcGuess.getTime() + (targetUtcMinutes - zonedUtcMinutes) * 60000)
  }

  function addDaysToTimeZoneDateParts(parts, dayOffset) {
    const date = new Date(Date.UTC(parts.year, parts.month - 1, parts.day + dayOffset, 0, 0, 0, 0))
    return {
      year: date.getUTCFullYear(),
      month: date.getUTCMonth() + 1,
      day: date.getUTCDate(),
    }
  }

  function materializeScheduleRowsLocal(rows, referenceTime) {
    if (!Array.isArray(rows) || !referenceTime) {
      return []
    }

    const rowsWithAbsoluteTimestamps = rows
      .filter((row) => row?.start_ts && row?.end_ts)
      .map((row) => ({
        start: new Date(row.start_ts),
        end: new Date(row.end_ts),
        enabled: row.enabled !== false,
        setpoint: row.enabled === false ? null : Number(row.setpoint ?? null),
      }))
      .filter((row) => !Number.isNaN(row.start.getTime()) && !Number.isNaN(row.end.getTime()) && row.end > row.start)
      .sort((a, b) => a.start.getTime() - b.start.getTime())

    if (rowsWithAbsoluteTimestamps.length > 0) {
      return rowsWithAbsoluteTimestamps
    }

    const referenceDate = new Date(referenceTime)
    const referenceParts = getTimeZoneParts(referenceDate)
    if (Number.isNaN(referenceDate.getTime()) || !referenceParts) {
      return []
    }

    const refClockMinutes = referenceParts.hour * 60 + referenceParts.minute

    // Global accumulating dayOffset — matches backend _materialize_schedule_rows_local exactly
    let globalDayOffset = 0
    let previousStartClockMinutes = null

    return rows
      .filter((row) => typeof row?.start === 'string' && typeof row?.end === 'string')
      .map((row) => {
        const [startHour, startMinute] = row.start.split(':').map(Number)
        const [endHour, endMinute] = row.end.split(':').map(Number)
        const startClockMinutes = startHour * 60 + startMinute
        const endClockMinutes = endHour * 60 + endMinute

        if (previousStartClockMinutes === null) {
          if (startClockMinutes < refClockMinutes) {
            globalDayOffset = 1
          }
        } else if (startClockMinutes < previousStartClockMinutes) {
          globalDayOffset += 1
        }
        previousStartClockMinutes = startClockMinutes

        const startDateParts = addDaysToTimeZoneDateParts(referenceParts, globalDayOffset)
        const start = buildDateFromTimeZoneParts({ ...startDateParts, hour: startHour, minute: startMinute })

        const endDayOffset = endClockMinutes <= startClockMinutes ? globalDayOffset + 1 : globalDayOffset
        const endDateParts = addDaysToTimeZoneDateParts(referenceParts, endDayOffset)
        const end = buildDateFromTimeZoneParts({ ...endDateParts, hour: endHour, minute: endMinute })

        return {
          start,
          end,
          enabled: row.enabled !== false,
          setpoint: row.enabled === false ? null : Number(row.setpoint ?? null),
        }
      })
      .filter((row) => row.end > row.start)
      .sort((a, b) => a.start.getTime() - b.start.getTime())
  }

  function getNextRelevantScheduleRow(rows, referenceTime) {
    const materializedRows = materializeScheduleRowsLocal(rows, referenceTime)
    if (materializedRows.length === 0) {
      return null
    }

    const effectiveReference = new Date(referenceTime)
    if (Number.isNaN(effectiveReference.getTime())) {
      return materializedRows[0]
    }

    return (
      materializedRows.find((row) => row.start <= effectiveReference && row.end > effectiveReference) ||
      materializedRows.find((row) => row.start >= effectiveReference) ||
      materializedRows[0]
    )
  }

  function getScheduleFutureHours(rows, referenceTime) {
    const materializedRows = materializeScheduleRowsLocal(rows, referenceTime)
    if (materializedRows.length === 0) {
      return scheduleWindowHours
    }

    const effectiveReference = new Date(referenceTime)
    if (Number.isNaN(effectiveReference.getTime())) {
      return scheduleWindowHours
    }

    const latestEndTimestamp = Math.max(...materializedRows.map((row) => row.end.getTime()))
    const diffHours = Math.max((latestEndTimestamp - effectiveReference.getTime()) / 3600000, 0)
    return Math.max(scheduleWindowHours, Math.ceil(diffHours))
  }

  const SETPOINT_DEFAULT = 22

  async function syncTopControlsFromSchedule(rows, referenceTime, { updateSetpoint = true, updateSwitch = true } = {}) {
    const nextRelevantRow = getNextRelevantScheduleRow(rows, referenceTime)

    syncingTopControls.value = true

    if (updateSetpoint) {
      const activeZoneId = dashboardStore.activeZone?.id
      const loadedScheduleSetpoint = getScheduleSetpoint(rows)
      if (loadedScheduleSetpoint != null) {
        slider1.value = loadedScheduleSetpoint
        // Keep zone setpoints map in sync with what the schedule says
        if (activeZoneId != null) {
          controlStore.zoneSetpoints = {
            ...controlStore.zoneSetpoints,
            [activeZoneId]: loadedScheduleSetpoint,
          }
        }
      } else if (activeZoneId != null && controlStore.zoneSetpoints[activeZoneId] != null) {
        // No schedule rows yet — use the per-zone value set from the topology
        slider1.value = controlStore.zoneSetpoints[activeZoneId]
      }
      // Otherwise keep whatever value the user last set on this slider.
    }

    if (updateSwitch) {
      if (nextRelevantRow) {
        switchValue.value = Boolean(nextRelevantRow.enabled)
      } else if (dashboardTimeGridCurrentRow.value?.hvac_is_on != null) {
        switchValue.value = Boolean(dashboardTimeGridCurrentRow.value.hvac_is_on)
      }
    }
    await nextTick()
    syncingTopControls.value = false
  }

  function clearOptimizationResultState() {
    if (
      optimizationResult.value === null &&
      optimizedControl.value.length === 0 &&
      !showOptimizeAlert.value
    ) {
      return
    }
    optimizedControl.value = []
    optimizedIndoorForecast.value = []
    optimizationResult.value = null
    showOptimizeAlert.value = false
  }

  function restoreOptimizationResult(result) {
    if (!result || typeof result !== 'object') {
      return
    }

    const operation = Array.isArray(result.recommended_operation)
      ? result.recommended_operation.slice(0, 12)
      : []
    const temperatures = Array.isArray(result.temperatures)
      ? result.temperatures.slice(1, 13)
      : []

    if (operation.length === 0 || temperatures.length === 0) {
      return
    }

    optimizationResult.value = result
    optimizedControl.value = operation.map(value => !!value)
    optimizedIndoorForecast.value = temperatures
    // No chartKey increment — chartData reactive computed picks up the new datasets
  }

  async function loadDashboardSchedule(refNow = null, futureHours = scheduleWindowHours) {
    const buildingId = dashboardStore.activeBuilding?.id
    if (!buildingId) {
      return
    }

  const token = authStore.getJwtToken?.()
  const query = new URLSearchParams({ future_hours: String(futureHours) })
  if (refNow) {
    query.set('ref_now', refNow)
  }

  const deviceId = dashboardStore.activeDevice?.id
  const zoneId = dashboardStore.activeZone?.id
  if (deviceId) query.set('unit_id', String(deviceId))
  if (zoneId) query.set('zone_id', String(zoneId))
  const response = await fetch(buildApiUrl(`/dashboard/hvac-schedule/${buildingId}?${query.toString()}`), {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    credentials: 'include',
  })

  if (!response.ok) {
    scheduleReloading.value = false
    throw new Error(`Failed to load HVAC schedule: ${response.status}`)
  }
  
    const payload = await response.json()
    const rows = payload.rows || []
    if (rows.length === 0) {
      const hour = Number.parseInt(
        new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Athens', hour: '2-digit', hour12: false }).format(new Date()),
        10,
      )
      rows.push({ start: `${String((hour + 1) % 24).padStart(2, '0')}:00`, end: '23:59', enabled: false, setpoint: null })
    }
    controlStore.setRawSchedule(rows)
    scheduleReloading.value = false
    return { ...payload, rows }
  }

async function saveDashboardSchedule(rows, requestId) {
  const buildingId = dashboardStore.activeBuilding?.id
  if (!buildingId) {
    return
  }

  const token = authStore.getJwtToken?.()
  const referenceTime = dashboardReferenceTime.value || dashboardTimeGridCurrentRow.value?.ts || new Date().toISOString()
  const futureHours = getScheduleFutureHours(rows, referenceTime)
  const unitId = dashboardStore.activeDevice?.id
  const zoneIdForPut = dashboardStore.activeZone?.id
  const putParams = new URLSearchParams()
  if (unitId) putParams.set('unit_id', String(unitId))
  if (zoneIdForPut) putParams.set('zone_id', String(zoneIdForPut))
  const putQuery = putParams.toString() ? `?${putParams.toString()}` : ''
  const response = await fetch(buildApiUrl(`/dashboard/hvac-schedule/${buildingId}${putQuery}`), {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    credentials: 'include',
    body: JSON.stringify({
      reference_time: referenceTime,
      future_hours: futureHours,
      rows: serializeScheduleRowsForApi(rows),
    }),
  })

  if (!response.ok) {
    throw new Error(`Failed to update HVAC schedule: ${response.status}`)
  }
  const payload = await response.json()
  if (requestId !== scheduleSaveRequestSequence) {
    return null
  }
  if (!areScheduleRowsEquivalent(controlStore.editableSchedule, payload.rows || [])) {
    controlStore.setRawSchedule(payload.rows || [])
  }
  await syncTopControlsFromSchedule(
    payload.rows || rows,
    payload.reference_time || referenceTime,
    { updateSetpoint: false, updateSwitch: false },
  )
  return payload
}

function handleScheduleChange(rows) {
  scheduleSaveMessage.value = ''

  if (scheduleSaveMessageTimeout) {
    clearTimeout(scheduleSaveMessageTimeout)
    scheduleSaveMessageTimeout = null
  }

  void syncTopControlsFromSchedule(
    rows,
    dashboardReferenceTime.value || dashboardTimeGridCurrentRow.value?.ts || new Date().toISOString(),
    { updateSetpoint: false, updateSwitch: false },
  )

  if (scheduleSaveTimeout) {
    clearTimeout(scheduleSaveTimeout)
  }

  scheduleSaveTimeout = setTimeout(async () => {
    const requestId = ++scheduleSaveRequestSequence
    scheduleSaving.value = true
    try {
      await saveDashboardSchedule(rows, requestId)
      if (requestId !== scheduleSaveRequestSequence) {
        return
      }
      // Schedule already fresh from save response — skip redundant re-fetch
      await loadDashboardTimeGrid(true, true)
      scheduleSaveMessage.value = 'Schedule updated in the database.'
      scheduleSaveMessageTimeout = setTimeout(() => {
        scheduleSaveMessage.value = ''
        scheduleSaveMessageTimeout = null
      }, 3500)
    } catch (error) {
      optimizeError.value = error.message || 'Failed to save HVAC schedule.'
    } finally {
      scheduleSaving.value = false
    }
  }, 400)
}

  async function loadDashboardTimeGrid(force = false, skipScheduleReload = false) {
    const buildingId = dashboardStore.activeBuilding?.id
    if (!buildingId) {
      return
    }

    if (skipScheduleReload) {
      // Called after a user-initiated schedule save — time-grid data is unchanged so skip
      // the fetch to avoid a chart re-render. Don't touch slider or main switch.
      const refTime = dashboardReferenceTime.value || dashboardTimeGridCurrentRow.value?.ts || null
      await syncTopControlsFromSchedule(controlStore.editableSchedule, refTime, {
        updateSetpoint: false,
        updateSwitch: false,
      })
      return
    }

    const unitId = dashboardStore.activeDevice?.id ?? null
    const payload = await dashboardStore.loadEfficiencyTimeGrid(buildingId, { force, unitId })
    const refTime = dashboardReferenceTime.value || payload?.current_row?.ts || null

    const schedulePayload = await loadDashboardSchedule(refTime, scheduleWindowHours)
    await syncTopControlsFromSchedule(
      schedulePayload?.rows || controlStore.editableSchedule,
      refTime,
    )

    restoreOptimizationResult(payload?.latest_optimization_result)
  }

const canOptimize = computed(() =>
  Boolean(dashboardStore.activeBuilding?.id) &&
  Boolean(optimizationContext.value) &&
  missingOptimizationFields.value.length === 0 &&
  scheduleSaving.value === false &&
  optimizeLoading.value === false,
)

const optimizeButtonLabel = computed(() => {
  if (optimizeLoading.value) {
    return 'Optimizing...'
  }
  if (!optimizationContext.value) {
    return 'Loading optimization...'
  }
  if (missingOptimizationFields.value.length > 0) {
    return 'Optimization unavailable'
  }
  return 'Optimize'
})

function formatOptimizationStatus(status) {
  if (status === 'accepted') {
    return 'Optimization request accepted...'
  }
  if (status === 'initializing_optimizer') {
    return 'Preparing HVAC optimizer...'
  }
  if (status === 'optimizer_ready') {
    return 'Optimizer ready...'
  }
  if (status === 'running_optimization') {
    return 'Running optimization...'
  }
  return 'Optimizing HVAC control...'
}

async function runOptimizationRequest(payload) {
  const token = authStore.getJwtToken?.()
  if (!token) {
    throw new Error('You must be logged in before running optimization.')
  }

  const controller = new AbortController()
  const timeoutId = setTimeout(() => {
    controller.abort()
  }, optimizationRequestTimeoutMs)

  try {
    optimizeStatus.value = formatOptimizationStatus('running_optimization')
    const response = await fetch(buildApiUrl('/predict/hvac/optimize'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      credentials: 'include',
      signal: controller.signal,
      body: JSON.stringify(payload),
    })

    const responseBody = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(
        responseBody?.detail ||
        responseBody?.message ||
        `Optimization failed: ${response.status}`,
      )
    }

    return responseBody
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Optimization timed out. Please try again.')
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

async function runOptimization() {
  if (!canOptimize.value) {
    optimizeError.value = optimizationReadinessMessage.value || 'Optimization inputs are not ready yet.'
    return
  }

  optimizeLoading.value = true
  showOptimizeAlert.value = false
  optimizeError.value = ''
  optimizeStatus.value = 'Running optimization...'

  try {
    const payload = getOptimizationPayload()
    const responseBody = await runOptimizationRequest(payload)
    const result = responseBody?.result || {}
    const operation = Array.isArray(result.recommended_operation) ? result.recommended_operation.slice(0, 12) : []
    const temperatures = Array.isArray(result.temperatures) ? result.temperatures.slice(1, 13) : []

    optimizationResult.value = result
    optimizedControl.value = operation.map(value => !!value)
    optimizedIndoorForecast.value = temperatures

    chartKey.value += 1
    optimizeLoading.value = false
    optimizeStatus.value = 'Optimization completed.'
    showOptimizeAlert.value = true

    const savings = typeof result.savings_percentage === 'number'
      ? `${result.savings_percentage.toFixed(1)}% savings`
      : 'optimization completed'

    alertsStore.addAlert({
      description: `HVAC optimization completed: ${savings}.`,
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    optimizeError.value = error.message || 'Optimization failed.'
    alertsStore.addAlert({
      description: `HVAC optimization failed: ${optimizeError.value}`,
      timestamp: new Date().toISOString()
    })
    optimizeLoading.value = false
    optimizeStatus.value = ''
  }
}


// Generate datetime labels: 6h real data (past) + 6h forecast (future), 5min intervals, split at now
const now = new Date();
now.setMilliseconds(0);
now.setSeconds(0);
let min = now.getMinutes();
if (min % 5 === 0) {
  now.setMinutes(min);
} else {
  now.setMinutes(min + (5 - (min % 5)));
}
const pastPoints = 72; // 6h * 60 / 5 = 72
const futurePoints = 73; // 6h * 60 / 5 + 1 = 73
const totalPoints = pastPoints + futurePoints;
const startDate = new Date(now.getTime() - pastPoints * 5 * 60000);
function formatLocalDateTimeLabel(value) {
  const parts = getTimeZoneParts(value)
  if (!parts) {
    return String(value)
  }
  return `${parts.year}-${String(parts.month).padStart(2, '0')}-${String(parts.day).padStart(2, '0')} ${String(parts.hour).padStart(2, '0')}:${String(parts.minute).padStart(2, '0')}`
}

const chartLabels = Array.from({ length: totalPoints }, (_, i) => {
  const d = new Date(startDate.getTime() + i * 5 * 60000);
  return formatLocalDateTimeLabel(d)
});

// Helper function to generate control schedule data
function generateControlScheduleFromRows(rows, scheduleRows, referenceTime) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return []
  }

  const materializedSchedule = materializeScheduleRowsLocal(scheduleRows, referenceTime)
  return rows.map((row) => {
    const timestamp = new Date(row?.ts)
    if (Number.isNaN(timestamp.getTime())) {
      return 0
    }

    return materializedSchedule.some(
      (period) => period.enabled && timestamp >= period.start && timestamp < period.end,
    )
      ? 0.5
      : 0
  })
}

function hasOptimizedOverlay() {
  return optimizedControl.value.length === 12 && optimizedIndoorForecast.value.length === 12
}

function buildDashboardOptimizedDatasets(labelCount, rows) {
  if (!hasOptimizedOverlay()) {
    return []
  }

  let startIdx = Math.max(labelCount - 36, 0)
  const windowStart = optimizationResult.value?.window_start
  if (windowStart && Array.isArray(rows) && rows.length) {
    const wsMs = new Date(windowStart).getTime()
    const found = rows.findIndex(row => new Date(row.ts).getTime() >= wsMs)
    if (found !== -1) startIdx = found
  }

  const optControlArr = new Array(labelCount).fill(null)
  const optIndoorArr = new Array(labelCount).fill(null)

  for (let i = 0; i < 12 && startIdx + i < labelCount; i++) {
    optControlArr[startIdx + i] = optimizedControl.value[i] ? 0.5 : 0
    optIndoorArr[startIdx + i] = optimizedIndoorForecast.value[i]
  }

  return [
    {
      label: 'Optimized Control',
      data: optControlArr,
      type: 'line',
      borderColor: '#d32f2f',
      backgroundColor: 'rgba(244,67,54,0.10)',
      borderWidth: 2,
      borderDash: [6, 4],
      stepped: true,
      fill: false,
      yAxisID: 'y1',
      pointRadius: 2,
      order: 3
    },
    {
      label: 'Optimized Indoor Forecast',
      data: optIndoorArr,
      type: 'line',
      borderColor: '#d32f2f',
      backgroundColor: 'rgba(244,67,54,0.10)',
      borderWidth: 2,
      borderDash: [6, 4],
      fill: false,
      yAxisID: 'y',
      pointRadius: 2,
      order: 4
    },
  ]
}

function buildDashboardChartData(rows) {
  const labels = rows.map(row => formatLocalDateTimeLabel(row.ts))
  const referenceTime = dashboardReferenceTime.value || dashboardTimeGridCurrentRow.value?.ts || new Date().toISOString()
  const refMs = new Date(referenceTime).getTime()
  const indoor = rows.map(row => (new Date(row.ts).getTime() <= refMs ? row.temperature : null))
  const forecast = rows.map(row => (new Date(row.ts).getTime() >= refMs ? row.outdoor_temperature : null))
  const upper = forecast.map(value => (typeof value === 'number' ? value + 0.3 : null))
  const lower = forecast.map(value => (typeof value === 'number' ? value - 0.3 : null))
  const userSchedule = generateControlScheduleFromRows(
    rows,
    chartSchedule.value,
    referenceTime,
  )
  const backendSchedule = rows.map(row => row.hvac_is_on ? 0.5 : 0)

  const datasets = [
    {
      label: 'Indoor Temperature (°C)',
      backgroundColor: 'rgba(54, 162, 235, 0.15)',
      borderColor: '#1976d2',
      data: indoor,
      fill: false,
      tension: 0.4,
      yAxisID: 'y'
    },
    {
      label: 'Forecast (°C)',
      backgroundColor: 'rgba(255, 193, 7, 0.15)',
      borderColor: '#ffa000',
      borderDash: [5, 5],
      data: forecast,
      fill: false,
      tension: 0.4,
      pointStyle: 'rectRot',
      yAxisID: 'y'
    },
    {
      label: 'Forecast Upper Bound',
      data: upper,
      borderColor: 'rgba(255, 193, 7, 0.1)',
      backgroundColor: 'rgba(255, 193, 7, 0.1)',
      borderWidth: 0,
      fill: '+1',
      pointRadius: 0,
      tension: 0.4,
      order: 1,
      yAxisID: 'y'
    },
    {
      label: 'Forecast Lower Bound',
      data: lower,
      borderColor: 'rgba(255, 193, 7, 0.1)',
      backgroundColor: 'rgba(255, 193, 7, 0.1)',
      borderWidth: 0,
      fill: false,
      pointRadius: 0,
      tension: 0.4,
      order: 1,
      yAxisID: 'y'
    },
    {
      label: 'Control Schedule',
      data: (() => {
        if (scheduleReloading.value) return rows.map(() => null)
        return controlStore.scheduleLoaded === true ? userSchedule : backendSchedule
      })(),
      type: 'line',
      borderColor: '#388e3c',
      backgroundColor: 'rgba(76,175,80,0.1)',
      borderWidth: 2,
      stepped: true,
      fill: false,
      yAxisID: 'y1',
      pointRadius: 0,
      order: 2
    },
    ...buildDashboardOptimizedDatasets(labels.length, rows),
  ]

  return { labels, datasets }
}

const chartData = computed(() => {
  if (dashboardTimeGridRows.value.length > 0) {
    return buildDashboardChartData(dashboardTimeGridRows.value)
  }

  return {
    labels: [],
    datasets: [],
  }
})

const chartOptions = computed(() => {
  const axisColor = isDarkTheme.value ? '#cbd5e1' : '#445066'
  const tickColor = isDarkTheme.value ? '#94a3b8' : '#5f6b7a'
  const xTickColor = isDarkTheme.value ? '#a8b4c7' : '#6b7280'
  const gridColor = isDarkTheme.value ? 'rgba(148, 163, 184, 0.12)' : 'rgba(68, 80, 102, 0.08)'
  const xGridColor = isDarkTheme.value ? 'rgba(148, 163, 184, 0.08)' : 'rgba(68, 80, 102, 0.05)'
  const tooltipBg = isDarkTheme.value ? 'rgba(15, 23, 42, 0.96)' : 'rgba(255, 255, 255, 0.96)'
  const tooltipTitle = isDarkTheme.value ? '#f8fafc' : '#1f2a37'
  const tooltipBody = isDarkTheme.value ? '#dbe7fb' : '#445066'
  const tooltipBorder = isDarkTheme.value ? 'rgba(148, 163, 184, 0.16)' : 'rgba(21, 101, 192, 0.12)'

  return {
    responsive: true,
    maintainAspectRatio: false,
    // Initial draw: left-to-right reveal. Data updates: short smooth fade-in.
    animation: { duration: 0 },
    animations: {
      x: {
        type: 'number',
        easing: 'easeInOutSine',
        duration: (ctx) => (ctx.initial ? 600 : 0),
        from: (ctx) => (ctx.initial ? Number.NaN : undefined),
        delay: (ctx) => (ctx.initial ? ctx.dataIndex * 2 : 0),
      },
      y: {
        type: 'number',
        easing: 'easeOutQuart',
        duration: (ctx) => (ctx.initial ? 500 : 280),
        from: (ctx) => (ctx.initial ? (ctx.chart.scales?.y?.min ?? 0) : undefined),
        delay: (ctx) => (ctx.initial ? ctx.dataIndex * 2 : 0),
      },
    },
    transitions: {
      active: { animation: { duration: 280 } },
    },
    layout: {
      padding: {
        top: 10,
        right: 12,
        bottom: 8,
        left: 8,
      },
    },
    interaction: { mode: 'index', intersect: false },
    stacked: false,
    plugins: {
      legend: {
        display: true,
        position: 'top',
        align: 'center',
        labels: {
          usePointStyle: true,
          boxWidth: 10,
          boxHeight: 10,
          color: axisColor,
          padding: 16,
          filter: (item) => !['Forecast Upper Bound', 'Forecast Lower Bound'].includes(item.text),
        },
      },
      tooltip: {
        enabled: true,
        backgroundColor: tooltipBg,
        titleColor: tooltipTitle,
        bodyColor: tooltipBody,
        borderColor: tooltipBorder,
        borderWidth: 1,
        padding: 12,
        displayColors: true,
        callbacks: {
          title: (items) => items?.[0]?.label || '',
        },
      },
    },
    scales: {
      y: {
        title: {
          display: true,
          text: 'Temperature (°C)',
          color: axisColor,
          font: {
            weight: '600',
          },
        },
        position: 'left',
        min: undefined,
        max: undefined,
        grid: {
          color: gridColor,
          drawBorder: false,
        },
        ticks: {
          color: tickColor,
          padding: 8,
        },
      },
      y1: {
        title: {
          display: true,
          text: 'Control Schedule',
          color: axisColor,
          font: {
            weight: '600',
          },
        },
        position: 'right',
        min: 0,
        max: 1,
        grid: {
          drawOnChartArea: false,
        },
        ticks: {
          stepSize: 0.5,
          color: tickColor,
          callback: v => {
            if (v === 0) return 'Off';
            if (v === 0.5) return 'On';
            return '';
          },
        },
      },
      x: {
        title: {
          display: true,
          text: 'Time',
          color: axisColor,
          font: {
            weight: '600',
          },
        },
        grid: {
          color: xGridColor,
          drawBorder: false,
        },
        ticks: {
          color: xTickColor,
          autoSkip: false,
          maxRotation: 0,
          minRotation: 0,
          callback: (value, index) => {
            if (index % 6 !== 0) {
              return ''
            }
            const labels = chartData.value?.labels
            const label = Array.isArray(labels) ? (labels[index] ?? '') : ''
            return typeof label === 'string' ? label.slice(11, 16) : ''
          },
        },
      }
    }
  }
});

// Get latest values from chartData for widgets
function lastValidNumber(arr) {
  for (let i = arr.length - 1; i >= 0; --i) {
    if (typeof arr[i] === 'number') return arr[i];
  }
  return null;
}
const indoorTemp = computed(() => {
  if (dashboardTimeGridCurrentRow.value?.temperature != null) {
    return Number(dashboardTimeGridCurrentRow.value.temperature).toFixed(1)
  }
  const val = lastValidNumber(chartData.value.datasets[0]?.data || []);
  return typeof val === 'number' ? val.toFixed(1) : '--';
});
const outdoorTemp = computed(() => {
  if (dashboardTimeGridCurrentRow.value?.outdoor_temperature != null) {
    return Number(dashboardTimeGridCurrentRow.value.outdoor_temperature).toFixed(1)
  }
  const val = lastValidNumber(chartData.value.datasets[1]?.data || []);
  return typeof val === 'number' ? val.toFixed(1) : '--';
});
const forecastTemp = computed(() => {
  if (optimizationContext.value?.outdoor_temperatures?.length > 1) {
    return Number(optimizationContext.value.outdoor_temperatures[1]).toFixed(1)
  }
  // Find the index of the next hour after the last indoor/outdoor value
  const nextHourIdx = chartData.value.datasets[0]?.data?.length || 0;
  const forecastData = chartData.value.datasets[1]?.data || []
  const val = forecastData[nextHourIdx] ?? lastValidNumber(forecastData);
  return typeof val === 'number' ? val.toFixed(1) : '--';
});

const isOn = ref(false)
const tempAdjust = ref(0)
const isBlockOn = ref(false)
const switchValue = ref(controlStore.preferences.switchValue)
const slider1 = ref(26)
const slider2 = ref(controlStore.preferences.slider2)

watch([switchValue, slider1, slider2], ([newSwitch, newSlider1, newSlider2]) => {
  controlStore.setPreferences({
    switchValue: newSwitch,
    slider1: newSlider1,
    slider2: newSlider2
  })
}, { immediate: true })

// Keep local slider in sync if another view (e.g. topology) updates the store value
watch(() => controlStore.preferences.slider1, (storeVal) => {
  if (storeVal !== slider1.value) slider1.value = storeVal
})

watch(slider1, (newSlider1, previousSlider1) => {
  if (
    syncingTopControls.value ||
    newSlider1 === previousSlider1 ||
    controlStore.scheduleLoaded !== true ||
    !Array.isArray(controlStore.editableSchedule) ||
    controlStore.editableSchedule.length === 0
  ) {
    return
  }

  // Persist per-zone setpoint immediately so zone switches can restore it
  const activeZoneId = dashboardStore.activeZone?.id
  if (activeZoneId != null) {
    controlStore.zoneSetpoints = { ...controlStore.zoneSetpoints, [activeZoneId]: Number(newSlider1) }
  }

  const nextSchedule = controlStore.editableSchedule.map((row) => ({
    ...row,
    setpoint: row.enabled ? Number(newSlider1) : null,
  }))

  // Don't write rawSchedule here — it would invalidate chartData on every tick while
  // the user drags the slider.
  handleScheduleChange(nextSchedule)
})

async function handleDeviceChange(deviceId) {
  scheduleReloading.value = true
  dashboardStore.setSelectedDevice(deviceId)
  controlStore.clearSchedule()
  clearOptimizationResultState()
  dismissOptimizationReadiness.value = false
  const buildingId = dashboardStore.activeBuilding?.id
  if (buildingId) {
    await dashboardStore.loadZonesForUnit(buildingId, deviceId)
  }
  await loadDashboardTimeGrid(true)
}

async function handleZoneChange(zoneId) {
  scheduleReloading.value = true
  dashboardStore.setSelectedZone(zoneId)
  controlStore.clearSchedule()
  clearOptimizationResultState()
  dismissOptimizationReadiness.value = false
  await loadDashboardTimeGrid(true)
}

watch(
  () => dashboardStore.activeBuilding?.id,
  async (buildingId, previousBuildingId) => {
    if (buildingId && (buildingId !== previousBuildingId || dashboardTimeGridRows.value.length === 0)) {
      if (buildingId !== previousBuildingId) {
        clearOptimizationResultState()
      }
      dismissOptimizationReadiness.value = false
      await loadDashboardTimeGrid()
    }
  },
  { immediate: true }
)

watch(
  () => optimizationContext.value?.missing_fields,
  () => {
    dismissOptimizationReadiness.value = false
  },
  { deep: true }
)

const sliderGradient = (val) => {
  const percent = (val / 100) * 100;
  return {
    background: `linear-gradient(to right, #0d6efd 0%, #0d6efd ${percent}%, #dc3545 ${percent}%, #dc3545 100%)`
  };
}

function toggleOnOff() {
  isOn.value = !isOn.value
}

function getSliderLabel(val) {
  if (val === 0) return 'Neutral'
  if (val < 0) return `Cooler (${val})`
  return `Warmer (+${val})`
}

// Dropdown options and selection state
const availableServices = [
  { label: 'Weather Data', value: 'weather' },
  { label: 'Service 1', value: 'openweather' },
  { label: 'Service 2', value: 'openmeteo' }
]
const selectedServices = ref(['weather'])

function toggleService(service) {
  const idx = selectedServices.value.indexOf(service)
  if (idx === -1) {
    selectedServices.value.push(service)
  } else if (selectedServices.value.length > 1) {
    // Only allow deselection if more than one is selected
    selectedServices.value.splice(idx, 1)
    // If all are deselected, auto-select 'weather'
    if (selectedServices.value.length === 0) {
      selectedServices.value.push('weather');
    }
  }
}

function isChecked(service) {
  return selectedServices.value.includes(service)
}

function dropdownLabel() {
  if (selectedServices.value.length === 1) {
    const service = availableServices.find(s => s.value === selectedServices.value[0])
    return service ? service.label : ''
  }
  // If more than one selected, show 'Custom'
  return 'Custom'
}

onMounted(async () => {
  await dashboardStore.loadDashboardData(true)
  const buildingId = dashboardStore.activeBuilding?.id
  const deviceId = dashboardStore.activeDevice?.id
  if (buildingId && deviceId) {
    await dashboardStore.loadZonesForUnit(buildingId, deviceId)
  }
  loadDashboardTimeGrid(true)
})

</script>

<style scoped>
/* ...existing code... */
.efficiency-tool-page {
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

/* ── Chart wrapper — fixed height, never reflows ── */
.chart-wrapper {
  position: relative;
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.98) 0%, rgba(255, 255, 255, 1) 100%);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
  padding: 1rem 1rem 0.5rem;
  /* Lock height so layout never shifts when data changes */
  height: 620px;
  min-height: 620px;
  overflow: hidden;
  contain: layout size;
}

/* Canvas fills the wrapper exactly */
.chart-canvas-host {
  width: 100%;
  height: 100%;
  transition: opacity 0.22s ease;
}

.chart-canvas-host--loading {
  opacity: 0.35;
}

/* ── Overlay ── */
.chart-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 20px;
  pointer-events: none;
}

.chart-overlay__backdrop {
  position: absolute;
  inset: 0;
  border-radius: 20px;
  background: rgba(248, 250, 255, 0.55);
  backdrop-filter: blur(3px);
}

.chart-overlay__spinner {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.chart-overlay__label {
  font-size: 0.82rem;
  font-weight: 600;
  color: #334155;
  letter-spacing: 0.01em;
}

/* SVG spinner ring */
.chart-spinner-ring {
  width: 44px;
  height: 44px;
  animation: chart-spin 1.1s linear infinite;
}

.chart-spinner-ring__track {
  stroke: rgba(37, 99, 235, 0.12);
}

.chart-spinner-ring__arc {
  stroke: #2563eb;
  animation: chart-arc 1.4s ease-in-out infinite;
  transform-origin: center;
}

@keyframes chart-spin {
  to { transform: rotate(360deg); }
}

@keyframes chart-arc {
  0%   { stroke-dashoffset: 280; }
  50%  { stroke-dashoffset: 60; }
  100% { stroke-dashoffset: 280; }
}

/* Overlay enter/leave transitions */
.chart-overlay-enter-active,
.chart-overlay-leave-active {
  transition: opacity 0.2s ease;
}

.chart-overlay-enter-from,
.chart-overlay-leave-to {
  opacity: 0;
}

.control-panel-card {
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.control-panel-card :deep(.card-body) {
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.08), transparent 32%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 1) 100%);
  padding: 1.35rem 1.5rem;
}

.hero-widget {
  position: relative;
}

.hero-widget :deep(.card) {
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 22px;
  overflow: hidden;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.06);
}

.hero-widget :deep(.card-body) {
  position: relative;
  min-height: 136px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 1.25rem 1.35rem;
}

.hero-value {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.hero-number {
  font-size: 2rem;
  line-height: 1;
  font-weight: 700;
  letter-spacing: -0.04em;
  color: rgba(255, 255, 255, 0.95);
}

.hero-title {
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.72);
  position: relative;
  z-index: 2;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 0.35rem 0.7rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: rgba(255, 255, 255, 0.82);
  color: #36506b;
  border: 1px solid rgba(255, 255, 255, 0.25);
  white-space: nowrap;
}

.hero-title-wrap {
  min-height: 32px;
}

.hero-ornament {
  position: absolute;
  right: 0.05rem;
  bottom: -0.05rem;
  width: 102px;
  height: auto;
  opacity: 0.34;
  pointer-events: none;
  filter: drop-shadow(0 14px 24px rgba(255, 255, 255, 0.12));
  z-index: 1;
}

.hero-ornament--outdoor {
  width: 110px;
  opacity: 0.36;
}

.hero-ornament--forecast {
  width: 114px;
  opacity: 0.35;
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .hero-widget .card {
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 16px 30px rgba(2, 6, 23, 0.28);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .hero-widget .card-body {
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .hero-badge {
  background: rgba(255, 255, 255, 0.88);
  color: #24364d;
  border-color: rgba(255, 255, 255, 0.18);
  box-shadow: 0 10px 18px rgba(15, 23, 42, 0.16);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .hero-title {
  color: rgba(255, 255, 255, 0.8);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .hero-number {
  text-shadow: 0 8px 20px rgba(15, 23, 42, 0.22);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .hero-ornament {
  opacity: 0.28;
  filter: drop-shadow(0 14px 24px rgba(15, 23, 42, 0.16));
}

.summary-widget :deep(.card) {
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 20px 42px rgba(15, 23, 42, 0.08);
}

.summary-widget--energy {
  --cui-card-cap-bg: #43d96b;
}

.summary-widget--reward {
  --cui-card-cap-bg: #ffd700;
}

.summary-widget :deep(.card-body) {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 1) 100%);
}

.summary-widget--energy :deep(.card-body) {
  background:
    radial-gradient(circle at top right, rgba(67, 217, 107, 0.16), transparent 34%),
    linear-gradient(180deg, #ffffff 0%, #f3fff7 100%);
}

.summary-widget--reward :deep(.card-body) {
  background:
    radial-gradient(circle at top right, rgba(255, 215, 0, 0.18), transparent 34%),
    linear-gradient(180deg, #fffef7 0%, #fff7cf 100%);
}

.summary-widget :deep(.card-title),
.summary-widget :deep(.text-body-secondary),
.summary-widget :deep(.text-medium-emphasis) {
  color: #5f6b7a !important;
}

.summary-widget :deep(.fs-4),
.summary-widget :deep(.fw-semibold),
.summary-widget :deep(.h4) {
  color: #132238 !important;
}

.summary-widget :deep(img) {
  filter: drop-shadow(0 10px 18px rgba(15, 23, 42, 0.1));
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget .card {
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: 0 20px 42px rgba(2, 6, 23, 0.32);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget .card-body {
  color: #e2e8f0;
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget--energy .card-body {
  background:
    radial-gradient(circle at top right, rgba(67, 217, 107, 0.14), transparent 34%),
    linear-gradient(180deg, rgba(22, 101, 52, 0.34) 0%, rgba(15, 23, 42, 0.98) 100%);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget--reward .card-body {
  background:
    radial-gradient(circle at top right, rgba(250, 204, 21, 0.18), transparent 34%),
    linear-gradient(180deg, rgba(133, 77, 14, 0.24) 0%, rgba(15, 23, 42, 0.98) 100%);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget .text-body-secondary,
:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget .text-medium-emphasis,
:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget .small,
:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget .card-title {
  color: #94a3b8 !important;
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget .fs-4,
:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget .fw-semibold,
:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget .h4 {
  color: #f8fafc !important;
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget .vr {
  color: rgba(148, 163, 184, 0.2);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .summary-widget img {
  filter: brightness(1.05) drop-shadow(0 12px 22px rgba(2, 6, 23, 0.22));
}

.control-block-responsive {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
  .control-row {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    gap: 1rem;
    width: 100%;
    justify-content: space-between;
  }
.button-group-col {
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  flex: 0 0 auto;
}
.button-group-flex {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 0.5rem;
}
.switch-col {
  min-width: 110px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.dropdown-col {
  min-width: 140px;
  display: flex;
  align-items: center;
}
.rate-col {
  min-width: 80px;
  display: flex;
  align-items: center;
}
 .slider-row-responsive {
  margin-top: -2.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 950px;
  margin-left: auto;
  margin-right: auto;
}

.slider-wrapper {
  width: 60%;

}

:global([data-coreui-theme='dark']) .efficiency-tool-page .chart-wrapper {
  border-color: rgba(148, 163, 184, 0.18);
  background:
    radial-gradient(circle at top right, rgba(96, 165, 250, 0.1), transparent 34%),
    linear-gradient(180deg, rgba(30, 41, 59, 0.98) 0%, rgba(15, 23, 42, 1) 100%);
  box-shadow: 0 22px 46px rgba(2, 6, 23, 0.34);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .chart-overlay__backdrop {
  background: rgba(15, 23, 42, 0.55);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .chart-overlay__label {
  color: #cbd5e1;
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .chart-spinner-ring__arc {
  stroke: #60a5fa;
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .control-panel-card {
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: 0 20px 42px rgba(2, 6, 23, 0.32);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .control-panel-card .card-body {
  background:
    radial-gradient(circle at top right, rgba(96, 165, 250, 0.12), transparent 34%),
    linear-gradient(180deg, rgba(30, 41, 59, 0.98) 0%, rgba(15, 23, 42, 1) 100%);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .control-panel-card .form-label,
:global([data-coreui-theme='dark']) .efficiency-tool-page .control-panel-card .badge,
:global([data-coreui-theme='dark']) .efficiency-tool-page .control-panel-card .dropdown-toggle,
:global([data-coreui-theme='dark']) .efficiency-tool-page .control-panel-card .form-check-label {
  color: #e2e8f0 !important;
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .control-panel-card .dropdown-toggle {
  background: rgba(71, 85, 105, 0.78);
  border-color: rgba(148, 163, 184, 0.18);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .control-panel-card .dropdown-menu {
  background: rgba(15, 23, 42, 0.98);
  border-color: rgba(148, 163, 184, 0.16);
  box-shadow: 0 18px 34px rgba(2, 6, 23, 0.34);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .control-panel-card .form-range::-webkit-slider-runnable-track {
  background: rgba(148, 163, 184, 0.28);
}

:global([data-coreui-theme='dark']) .efficiency-tool-page .control-panel-card .form-range::-moz-range-track {
  background: rgba(148, 163, 184, 0.28);
}


@media (max-width: 600px) {
  .slider-wrapper {
    width: 100%;
    margin-top: 0.5rem;
  }
  .control-row {
    flex-direction: row;
    gap: 0.5rem;
    align-items: stretch;
    width: 100%;
    justify-content: space-between;
  }
  .switch-col {
    min-width: 0;
    flex: 0 1 auto;
    align-items: flex-start;
    justify-content: flex-start;
  }
  .button-group-col {
    flex: 0 1 auto;
    align-items: flex-end;
    justify-content: flex-end;
    display: flex;
  }
  .button-group-flex {
    justify-content: flex-end;
  }
  .slider-row-responsive {
    margin-top: 1rem;
    width: 100%;
    max-width: 100vw;
  }
}
.control-block {
@media (max-width: 600px) {
  .control-row {
    flex-direction: row;
    gap: 0.5rem;
    align-items: stretch;
    width: 100%;
    justify-content: space-between;
  }
  .switch-col {
    min-width: 0;
    flex: 1 1 0;
    width: 100%;
    align-items: center;
    justify-content: flex-start;
  }
  .button-group-col {
    flex: 0 0 auto;
    width: auto;
    align-items: flex-start;
    justify-content: flex-end;
  }
  .button-group-flex {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    gap: 0.5rem;
    justify-content: flex-end;
  }
  .slider-row-responsive {
    margin-top: 0.5rem;
    width: 100%;
    max-width: 100vw;
  }
}
  .efficiency-tool-page {
    padding: 0.1rem;
  }
  .control-block {
    max-width: 100vw;
    margin-left: 0;
    margin-right: 0;
  }
}
</style>
