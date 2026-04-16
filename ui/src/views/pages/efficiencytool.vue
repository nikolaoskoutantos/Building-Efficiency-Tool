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
          <template #chart>
            <CChart
              class="position-absolute w-100 h-100"
              type="line"
              :data="{
                labels: [
                  'January',
                  'February',
                  'March',
                  'April',
                  'May',
                  'June',
                  'July',
                ],
                datasets: [
                  {
                    backgroundColor: 'rgba(255,255,255,.1)',
                    borderColor: 'rgba(255,255,255,.55)',
                    pointHoverBackgroundColor: '#fff',
                    borderWidth: 2,
                    data: [65, 59, 84, 84, 51, 55, 40],
                    fill: true,
                  },
                ],
              }"
              :options="{
                elements: {
                  line: {
                    tension: 0.4,
                  },
                  point: {
                    radius: 0,
                    hitRadius: 10,
                    hoverRadius: 4,
                    hoverBorderWidth: 3,
                  },
                },
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    display: false,
                  },
                },
                scales: {
                  x: {
                    display: false,
                  },
                  y: {
                    display: false,
                  },
                },
              }"
            />
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
          <template #chart>
            <CChart
              class="position-absolute w-100 h-100"
              type="line"
              :data="{
                labels: [
                  'January',
                  'February',
                  'March',
                  'April',
                  'May',
                  'June',
                  'July',
                ],
                datasets: [
                  {
                    backgroundColor: 'rgba(255,255,255,.1)',
                    borderColor: 'rgba(255,255,255,.55)',
                    pointHoverBackgroundColor: '#fff',
                    borderWidth: 2,
                    data: [1, 13, 9, 17, 34, 41, 38],
                    fill: true,
                  },
                ],
              }"
              :options="{
                elements: {
                  line: {
                    tension: 0.4,
                  },
                  point: {
                    radius: 0,
                    hitRadius: 10,
                    hoverRadius: 4,
                    hoverBorderWidth: 3,
                  },
                },
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    display: false,
                  },
                },
                scales: {
                  x: {
                    display: false,
                  },
                  y: {
                    display: false,
                  },
                },
              }"
            />
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
            <label for="slider1" class="form-label mb-1 text-center w-100" style="font-weight: 600;">
              Indoor Temperature Setpoint: {{ slider1 }}°C
            </label>
            <div class="slider-wrapper">
              <div class="d-flex justify-content-between align-items-center w-100 mb-1">
                <span style="font-size: 0.95em; color: #0d6efd; font-weight: 500;">0</span>
                <span style="font-size: 0.95em; color: #dc3545; font-weight: 500;">40</span>
              </div>
              <CFormRange id="slider1" v-model="slider1" min="0" max="40" />
            </div>
          </div>
        </div>
      </CCardBody>
    </CCard>
    <HvacScheduleTable
      :optimize-loading="optimizeLoading"
      :optimize-disabled="!canOptimize"
      :optimize-button-label="optimizeButtonLabel"
      :schedule-saving="scheduleSaving"
      @optimize="runOptimization"
      @schedule-change="handleScheduleChange"
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
    <div class="chart-wrapper" style="overflow: hidden; width: 100%; height: 600px;">
      <div style="width: 100%; height: 600px; overflow: hidden;">
        <CChartLine :key="chartKey" :data="chartData" :options="chartOptions" class="mb-4" style="width: 100%; height: 600px;" />
      </div>
    </div>
    <EnergyBarChart :optimization-summary="optimizationSummary" class="mb-4" />
  </div>
</template>

<script setup>
import { CChartLine } from '@coreui/vue-chartjs'
import RatingOne from '@/components/Rating.vue'
import EnergyBarChart from '@/components/EnergyBarChart.vue'
import HvacScheduleTable from '@/components/HvacScheduleTable.vue'
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { CRow, CCol, CWidgetStatsA, CCard, CCardBody, CFormRange, CFormSwitch, CDropdown, CDropdownToggle, CDropdownMenu, CSpinner, CAlert, useColorModes } from '@coreui/vue'
import { useControlStore } from '@/stores/control.js'
import { useAlertsStore } from '@/stores/alerts.js'
import { useDashboardStore } from '@/stores/dashboard.js'
import { useAuthStore } from '@/stores/auth.js'
import { buildApiUrl, apiRequest } from '@/config/api.js'

const controlStore = useControlStore()
const alertsStore = useAlertsStore()
const dashboardStore = useDashboardStore()
const authStore = useAuthStore()
const { colorMode } = useColorModes('coreui-free-vue-admin-template-theme')
const isDarkTheme = computed(() => colorMode.value === 'dark')

// Helper function for cryptographically secure random number generation
function getSecureRandom() {
  // Always use crypto.getRandomValues - no fallback to Math.random()
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    return crypto.getRandomValues(new Uint32Array(1))[0] / (0xffffffff + 1);
  }
  
  // If crypto is not available, return a deterministic value for demo purposes
  // This is safe since it's only used for chart visualization, not security
  return 0.5;
}

function randn_bm() {
  let u = 0, v = 0;
  while(u === 0) u = getSecureRandom();
  while(v === 0) v = getSecureRandom();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

const chartKey = ref(0)

// Optimization mock data
const optimizedControl = ref([]) // Array of 12 true/false
const optimizedIndoorForecast = ref([]) // Array of 12 numbers
const optimizeLoading = ref(false)
const showOptimizeAlert = ref(false)
const optimizeError = ref('')
const optimizeStatus = ref('')
const optimizationResult = ref(null)
const scheduleSaving = ref(false)
const dismissOptimizationReadiness = ref(false)
const dashboardTimeGridRows = computed(() => dashboardStore.efficiencyTimeGrid.rows || [])
const dashboardTimeGridCurrentRow = computed(() => dashboardStore.efficiencyTimeGrid.currentRow || null)
const dashboardReferenceTime = computed(() => dashboardStore.efficiencyTimeGrid.referenceTime || null)
const optimizationContext = computed(() => dashboardStore.efficiencyTimeGrid.optimizationContext || null)
let scheduleSaveTimeout = null
const syncingTopControls = ref(false)
const applyingOptimizedSchedule = ref(false)

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
    const numericId =
      Number.isInteger(row?.id)
        ? row.id
        : (typeof row?.id === 'string' && /^\d+$/.test(row.id) ? Number(row.id) : undefined)

      return {
        ...(numericId !== undefined ? { id: numericId } : {}),
        start: row?.start,
        end: row?.end,
        enabled: row?.enabled !== false,
        setpoint: row?.enabled === false ? null : Number(row?.setpoint ?? slider1.value ?? null),
      }
    })
  }

function extractApiErrorDetail(body, fallbackMessage) {
  if (typeof body?.detail === 'string' && body.detail.trim()) {
    return body.detail.trim()
  }
  if (Array.isArray(body?.detail) && body.detail.length > 0) {
    return body.detail
      .map((item) => item?.msg || JSON.stringify(item))
      .filter(Boolean)
      .join(' | ')
  }
  if (typeof body?.message === 'string' && body.message.trim()) {
    return body.message.trim()
  }
  return fallbackMessage
}

function toFiniteNumber(value) {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue : null
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
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

const optimizationSummary = computed(() => {
  const result = optimizationResult.value
  if (!result) {
    return null
  }

  const baselineAllOnKwh = toFiniteNumber(result?.baseline_all_on?.energy_consumption)
  const baselineAllOffKwh = toFiniteNumber(result?.baseline_all_off?.energy_consumption)
  const optimizedConsumptionKwh = toFiniteNumber(
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
    ? result.recommended_operation.slice(0, 12).map(value => Boolean(value))
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
      optimizationSummary.value?.savedKwh != null
        ? `${formatEnergyValue(optimizationSummary.value.savedKwh)} (${formatPercentValue(optimizationSummary.value.savedPercentage)})`
        : '--',
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
    optimizationSummary.value.savedKwh != null
      ? `${formatEnergyValue(optimizationSummary.value.savedKwh)} saved`
      : 'Optimization completed'

  return `${savingsText} with ${scheduleMinutes} minutes scheduled on (${formatRecommendationLabel(optimizationSummary.value.strategy)}).`
})

const missingOptimizationFields = computed(() => optimizationContext.value?.missing_fields || [])
const optimizationReadinessMessage = computed(() => {
  if (dismissOptimizationReadiness.value || optimizationContext.value?.is_ready !== false || missingOptimizationFields.value.length === 0) {
    return ''
  }

  const labels = missingOptimizationFields.value.map((field) => {
    if (field === 'temperature') return 'indoor temperature'
    if (field === 'hvac_setpoint') return 'HVAC setpoint'
    if (field === 'outdoor_temperatures') return 'outdoor forecast'
    if (field === 'ts') return 'reference time'
    return field.replace(/_/g, ' ')
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
    return optimizationContext.value.outdoor_temperatures.map(value => Number(value))
  }
  const weatherDataset = getDatasetByLabelFragment('Outdoor Temperature')
  const forecastDataset = getDatasetByLabelFragment('Forecast')
  const weatherData = weatherDataset?.data || []
  const forecastData = forecastDataset?.data || []
  const values = []

  const currentOutdoor = weatherData[pastPoints - 1]
  values.push(typeof currentOutdoor === 'number' ? Number(currentOutdoor.toFixed(3)) : 22.0)

  for (let i = 0; i < 12; i += 1) {
    const forecastValue = forecastData[pastPoints + i]
    values.push(typeof forecastValue === 'number' ? Number(forecastValue.toFixed(3)) : values[values.length - 1])
  }

  return values
}

  function getOptimizationPayload() {
    const buildingId = dashboardStore.defaultBuilding?.id
    if (!buildingId) {
      throw new Error('No default building is available for optimization.')
  }

  return {
    building_id: buildingId,
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

  function formatTimeLabelFromDate(value) {
    const date = value instanceof Date ? value : new Date(value)
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  }

  function materializeScheduleRowsLocal(rows, referenceTime) {
    if (!Array.isArray(rows) || !referenceTime) {
      return []
    }

    const localRef = new Date(referenceTime)
    if (Number.isNaN(localRef.getTime())) {
      return []
    }

    const refClockMinutes = localRef.getHours() * 60 + localRef.getMinutes()
    let dayOffset = 0
    let previousStartMinutes = null

    return rows
      .filter((row) => typeof row?.start === 'string' && typeof row?.end === 'string')
      .map((row, index) => {
        const [startHour, startMinute] = row.start.split(':').map(Number)
        const [endHour, endMinute] = row.end.split(':').map(Number)
        const startClockMinutes = startHour * 60 + startMinute
        const endClockMinutes = endHour * 60 + endMinute

        if (index === 0 && startClockMinutes < refClockMinutes) {
          dayOffset = 1
        } else if (previousStartMinutes !== null && startClockMinutes < previousStartMinutes) {
          dayOffset += 1
        }

        const start = new Date(localRef)
        start.setHours(startHour, startMinute, 0, 0)
        start.setDate(start.getDate() + dayOffset)

        const end = new Date(localRef)
        end.setHours(endHour, endMinute, 0, 0)
        end.setDate(end.getDate() + dayOffset)
        if (endClockMinutes <= startClockMinutes) {
          end.setDate(end.getDate() + 1)
        }

        previousStartMinutes = startClockMinutes

        return {
          start,
          end,
          enabled: row.enabled !== false,
          setpoint: row.enabled === false ? null : Number(row.setpoint ?? slider1.value ?? null),
        }
      })
      .filter((row) => row.end > row.start)
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

  async function syncTopControlsFromSchedule(rows, referenceTime) {
    const nextRelevantRow = getNextRelevantScheduleRow(rows, referenceTime)
    const loadedScheduleSetpoint = getScheduleSetpoint(rows)

    syncingTopControls.value = true
    if (loadedScheduleSetpoint != null) {
      slider1.value = loadedScheduleSetpoint
    } else if (optimizationContext.value?.setpoint != null) {
      slider1.value = Number(optimizationContext.value.setpoint)
    }
    if (nextRelevantRow) {
      switchValue.value = Boolean(nextRelevantRow.enabled)
    } else if (dashboardTimeGridCurrentRow.value?.hvac_is_on != null) {
      switchValue.value = Boolean(dashboardTimeGridCurrentRow.value.hvac_is_on)
    }
    await nextTick()
    syncingTopControls.value = false
  }

  function clearOptimizationResultState() {
    optimizedControl.value = []
    optimizedIndoorForecast.value = []
    optimizationResult.value = null
    showOptimizeAlert.value = false
    chartKey.value += 1
  }

  function buildOptimizedSegments(operation, optimizationStart, setpoint) {
    if (!Array.isArray(operation) || operation.length === 0) {
      return []
    }

    const segments = []
    const stepMinutes = 5
    let currentEnabled = null
    let segmentStart = null

    for (let index = 0; index < operation.length; index += 1) {
      const enabled = Boolean(operation[index])
      const intervalStart = new Date(optimizationStart.getTime() + index * stepMinutes * 60000)

      if (currentEnabled === null) {
        currentEnabled = enabled
        segmentStart = intervalStart
        continue
      }

      if (enabled !== currentEnabled) {
        segments.push({
          start: segmentStart,
          end: intervalStart,
          enabled: currentEnabled,
          setpoint: currentEnabled ? Number(setpoint) : null,
        })
        currentEnabled = enabled
        segmentStart = intervalStart
      }
    }

    segments.push({
      start: segmentStart,
      end: new Date(optimizationStart.getTime() + operation.length * stepMinutes * 60000),
      enabled: currentEnabled,
      setpoint: currentEnabled ? Number(setpoint) : null,
    })

    return segments
  }

  function overlayOptimizedScheduleRows(existingRows, operation, referenceTime, setpoint) {
    const optimizationStart = new Date(referenceTime)
    if (Number.isNaN(optimizationStart.getTime())) {
      return Array.isArray(existingRows) ? existingRows : []
    }

    const optimizedSegments = buildOptimizedSegments(operation, optimizationStart, setpoint)
    if (optimizedSegments.length === 0) {
      return Array.isArray(existingRows) ? existingRows : []
    }

    const optimizationEnd = optimizedSegments[optimizedSegments.length - 1].end
    const preservedSegments = []

    for (const row of materializeScheduleRowsLocal(existingRows, referenceTime)) {
      if (row.end <= optimizationStart || row.start >= optimizationEnd) {
        preservedSegments.push(row)
        continue
      }

      if (row.start < optimizationStart) {
        preservedSegments.push({
          ...row,
          end: optimizationStart,
        })
      }

      if (row.end > optimizationEnd) {
        preservedSegments.push({
          ...row,
          start: optimizationEnd,
        })
      }
    }

    const mergedSegments = [...preservedSegments, ...optimizedSegments]
      .filter((row) => row.end > row.start)
      .sort((a, b) => a.start.getTime() - b.start.getTime())
      .reduce((accumulator, row) => {
        const previous = accumulator[accumulator.length - 1]
        if (
          previous &&
          previous.end.getTime() === row.start.getTime() &&
          previous.enabled === row.enabled &&
          ((previous.enabled === false && row.enabled === false) || previous.setpoint === row.setpoint)
        ) {
          previous.end = row.end
          return accumulator
        }

        accumulator.push({ ...row })
        return accumulator
      }, [])

    return mergedSegments.map((row, index) => ({
      id: `optimized-${row.start.getTime()}-${index}`,
      start: formatTimeLabelFromDate(row.start),
      end: formatTimeLabelFromDate(row.end),
      enabled: row.enabled,
      setpoint: row.enabled ? row.setpoint : null,
    }))
  }
  
  async function loadDashboardSchedule(refNow = null) {
    const buildingId = dashboardStore.defaultBuilding?.id
    if (!buildingId) {
      return
  }

  const token = authStore.getJwtToken?.()
  const query = new URLSearchParams({ future_hours: '3' })
  if (refNow) {
    query.set('ref_now', refNow)
  }

  const response = await fetch(buildApiUrl(`/dashboard/hvac-schedule/${buildingId}?${query.toString()}`), {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    credentials: 'include',
  })

  if (!response.ok) {
    throw new Error(`Failed to load HVAC schedule: ${response.status}`)
    }
  
    const payload = await response.json()
    controlStore.setRawSchedule(payload.rows || [])
    return payload
  }

async function saveDashboardSchedule(rows) {
  const buildingId = dashboardStore.defaultBuilding?.id
  if (!buildingId) {
    return
  }

  const token = authStore.getJwtToken?.()
  const response = await fetch(buildApiUrl(`/dashboard/hvac-schedule/${buildingId}`), {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    credentials: 'include',
    body: JSON.stringify({
      reference_time: dashboardReferenceTime.value,
      future_hours: 3,
      rows: serializeScheduleRowsForApi(rows),
    }),
  })

  if (!response.ok) {
    throw new Error(`Failed to update HVAC schedule: ${response.status}`)
  }
  // Keep the optimistic local schedule instead of overwriting it with the
  // backend response, which may still return split 5-minute boundary rows.
  await response.json()
}

function handleScheduleChange(rows) {
  if (!applyingOptimizedSchedule.value) {
    clearOptimizationResultState()
  }

  void syncTopControlsFromSchedule(
    rows,
    dashboardReferenceTime.value || dashboardTimeGridCurrentRow.value?.ts || new Date().toISOString(),
  )

  if (scheduleSaveTimeout) {
    clearTimeout(scheduleSaveTimeout)
  }

  scheduleSaveTimeout = setTimeout(async () => {
    scheduleSaving.value = true
    try {
      await saveDashboardSchedule(rows)
    } catch (error) {
      optimizeError.value = error.message || 'Failed to save HVAC schedule.'
    } finally {
      scheduleSaving.value = false
    }
  }, 400)
}

  async function loadDashboardTimeGrid(force = false) {
    const buildingId = dashboardStore.defaultBuilding?.id
    if (!buildingId) {
      return
  }

    const payload = await dashboardStore.loadEfficiencyTimeGrid(buildingId, { force })
    const schedulePayload = await loadDashboardSchedule(dashboardReferenceTime.value || payload?.current_row?.ts || null)
    await syncTopControlsFromSchedule(
      schedulePayload?.rows || controlStore.schedule,
      dashboardReferenceTime.value || payload?.current_row?.ts || null,
    )
  }

const canOptimize = computed(() =>
  Boolean(dashboardStore.defaultBuilding?.id) &&
  Boolean(optimizationContext.value) &&
  optimizationContext.value?.is_ready !== false &&
  scheduleSaving.value === false &&
  optimizeLoading.value === false,
)

const optimizeButtonLabel = computed(() => {
  if (optimizeLoading.value) {
    return 'Optimizing...'
  }
  if (scheduleSaving.value) {
    return 'Saving schedule...'
  }
  if (!optimizationContext.value) {
    return 'Loading optimization...'
  }
  if (optimizationContext.value?.is_ready === false) {
    return 'Optimization unavailable'
  }
  return 'Optimize'
})

function runOptimization() {
  if (!canOptimize.value) {
    optimizeError.value = optimizationReadinessMessage.value || 'Optimization inputs are not ready yet.'
    return
  }

  optimizeLoading.value = true
  showOptimizeAlert.value = false
  optimizeError.value = ''
  optimizeStatus.value = 'Running optimization...'

  ;(async () => {
    try {
      const payload = getOptimizationPayload()
      const response = await apiRequest('/predict/hvac/optimize', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      const responseBody = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(
          extractApiErrorDetail(
            responseBody,
            `Optimization failed: ${response.status}`,
          ),
        )
      }

      const result = responseBody?.result || {}
      const operation = Array.isArray(result.recommended_operation) ? result.recommended_operation.slice(0, 12) : []
      const temperatures = Array.isArray(result.temperatures) ? result.temperatures.slice(1, 13) : []

      optimizationResult.value = result
      optimizedControl.value = operation.map(value => Boolean(value))
      optimizedIndoorForecast.value = temperatures

      if (operation.length > 0) {
        const nextSchedule = overlayOptimizedScheduleRows(
          controlStore.schedule,
          operation,
          dashboardReferenceTime.value || dashboardTimeGridCurrentRow.value?.ts,
          Number(slider1.value),
        )
        applyingOptimizedSchedule.value = true
        controlStore.setSchedule(nextSchedule)
        handleScheduleChange(nextSchedule)
        await syncTopControlsFromSchedule(
          nextSchedule,
          dashboardReferenceTime.value || dashboardTimeGridCurrentRow.value?.ts || new Date().toISOString(),
        )
        applyingOptimizedSchedule.value = false
      }

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
      applyingOptimizedSchedule.value = false
      optimizeError.value = error.message || 'Optimization failed.'
      alertsStore.addAlert({
        description: `HVAC optimization failed: ${optimizeError.value}`,
        timestamp: new Date().toISOString()
      })
      optimizeLoading.value = false
      optimizeStatus.value = ''
    }
  })()
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
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) {
    return String(value)
  }
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

const chartLabels = Array.from({ length: totalPoints }, (_, i) => {
  const d = new Date(startDate.getTime() + i * 5 * 60000);
  return formatLocalDateTimeLabel(d)
});

// Helper function to generate control schedule data
function generateControlScheduleData(points, startDate, controlStore) {
  const control = new Array(points).fill(0);
  if (!Array.isArray(controlStore.schedule)) {
    return control;
  }
  
  for (const period of controlStore.schedule) {
    if (!period.enabled) continue;
    
    const [sh, sm] = period.start.split(':').map(Number);
    const [eh, em] = period.end.split(':').map(Number);
    let schedStart = new Date(startDate);
    schedStart.setHours(sh, sm, 0, 0);
    let schedEnd = new Date(startDate);
    schedEnd.setHours(eh, em, 0, 0);
    
    if (schedEnd <= schedStart) {
      schedEnd.setDate(schedEnd.getDate() + 1);
    }
    
    for (let i = 0; i < points; i++) {
      const t = new Date(startDate.getTime() + i * 5 * 60000);
      if (t >= schedStart && t < schedEnd) {
        control[i] = 0.5;
      }
    }
  }
  
  return control;
}

function isScheduleActiveAtTimestamp(ts, schedule) {
  const timestamp = new Date(ts)
  if (Number.isNaN(timestamp.getTime()) || !Array.isArray(schedule)) {
    return false
  }

  for (const period of schedule) {
    if (!period?.enabled || typeof period.start !== 'string' || typeof period.end !== 'string') {
      continue
    }

    const [startHour, startMinute] = period.start.split(':').map(Number)
    const [endHour, endMinute] = period.end.split(':').map(Number)
    if (![startHour, startMinute, endHour, endMinute].every(Number.isFinite)) {
      continue
    }

    const scheduleStart = new Date(timestamp)
    scheduleStart.setHours(startHour, startMinute, 0, 0)
    const scheduleEnd = new Date(timestamp)
    scheduleEnd.setHours(endHour, endMinute, 0, 0)

    if (scheduleEnd <= scheduleStart) {
      if (timestamp < scheduleEnd) {
        scheduleStart.setDate(scheduleStart.getDate() - 1)
      } else {
        scheduleEnd.setDate(scheduleEnd.getDate() + 1)
      }
    }

    if (timestamp >= scheduleStart && timestamp < scheduleEnd) {
      return true
    }
  }

  return false
}

function generateControlScheduleFromRows(rows, controlStore) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return []
  }

  return rows.map(row => (isScheduleActiveAtTimestamp(row?.ts, controlStore.schedule) ? 0.5 : 0))
}

const chartData = computed(() => {
  const points = totalPoints;
  if (dashboardTimeGridRows.value.length > 0) {
    const labels = dashboardTimeGridRows.value.map(row => formatLocalDateTimeLabel(row.ts))
    const referenceTime = dashboardReferenceTime.value || dashboardTimeGridCurrentRow.value?.ts || new Date().toISOString()
    const indoor = dashboardTimeGridRows.value.map(row => (row.ts <= referenceTime ? row.temperature : null))
      const forecast = dashboardTimeGridRows.value.map(row => (row.ts >= referenceTime ? row.outdoor_temperature : null))
      const upper = forecast.map(value => (typeof value === 'number' ? value + 0.3 : null))
      const lower = forecast.map(value => (typeof value === 'number' ? value - 0.3 : null))
      const userSchedule = generateControlScheduleFromRows(dashboardTimeGridRows.value, controlStore)
      const hasLoadedSchedule = controlStore.scheduleLoaded === true
      const backendSchedule = dashboardTimeGridRows.value.map(row => row.hvac_is_on ? 0.5 : 0)

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
          data: hasLoadedSchedule ? userSchedule : backendSchedule,
          type: 'line',
          borderColor: '#388e3c',
        backgroundColor: 'rgba(76,175,80,0.1)',
        borderWidth: 2,
        stepped: true,
        fill: false,
        yAxisID: 'y1',
        pointRadius: 0,
        order: 2
      }
    ]

    if (optimizedControl.value.length === 12 && optimizedIndoorForecast.value.length === 12) {
      const startIdx = Math.max(labels.length - 36, 0)
      const optControlArr = new Array(labels.length).fill(null)
      const optIndoorArr = new Array(labels.length).fill(null)
      for (let i = 0; i < 12 && startIdx + i < labels.length; i++) {
        optControlArr[startIdx + i] = optimizedControl.value[i] ? 0.5 : 0
        optIndoorArr[startIdx + i] = optimizedIndoorForecast.value[i]
      }
      datasets.push({
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
      })
      datasets.push({
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
      })
    }

    return { labels, datasets }
  }

  const indoor = Array.from({ length: points }, (_, i) =>
    i < pastPoints ? 23 + 0.01 * i + randn_bm() * 0.15 : null
  );
  const outdoor = Array.from({ length: points }, (_, i) =>
    i < pastPoints ? 22 + 0.008 * i + randn_bm() * 0.18 : null
  );
  let lastOutdoor = outdoor[pastPoints - 1] ?? 22;
  const forecast = Array.from({ length: points }, (_, i) =>
    i >= pastPoints ? lastOutdoor + 0.01 * (i - pastPoints) + randn_bm() * 0.2 : null
  );
  const upper = Array.from({ length: points }, (_, i) =>
    i >= pastPoints ? (forecast[i] ?? 0) + 0.3 : null
  );
  const lower = Array.from({ length: points }, (_, i) =>
    i >= pastPoints ? (forecast[i] ?? 0) - 0.3 : null
  );

  // Map dropdown service to datasets
  const serviceToDataset = {
    weather: [
      {
        label: 'Indoor Temperature (°C)',
        backgroundColor: 'rgba(21, 101, 192, 0.12)',
        borderColor: '#1565c0',
        data: indoor,
        fill: false,
        tension: 0.32,
        borderWidth: 3,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHitRadius: 10,
        cubicInterpolationMode: 'monotone',
        yAxisID: 'y'
      },
      {
        label: 'Outdoor Temperature (°C)',
        backgroundColor: 'rgba(255, 152, 0, 0.12)',
        borderColor: '#ff8f00',
        data: outdoor,
        fill: false,
        tension: 0.28,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 3,
        pointHitRadius: 8,
        cubicInterpolationMode: 'monotone',
        yAxisID: 'y'
      },
      {
        label: 'Forecast (°C)',
        backgroundColor: 'rgba(255, 179, 0, 0.12)',
        borderColor: '#ffa000',
        borderDash: [4, 5],
        data: forecast,
        fill: false,
        tension: 0.28,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 3,
        pointHitRadius: 8,
        cubicInterpolationMode: 'monotone',
        pointStyle: 'rectRot',
        yAxisID: 'y'
      },
      {
        label: 'Forecast Upper Bound',
        data: upper,
        borderColor: 'rgba(255, 193, 7, 0.0)',
        backgroundColor: 'rgba(255, 193, 7, 0.12)',
        borderWidth: 0,
        fill: '+1',
        pointRadius: 0,
        tension: 0.28,
        order: 1,
        yAxisID: 'y'
      },
      {
        label: 'Forecast Lower Bound',
        data: lower,
        borderColor: 'rgba(255, 193, 7, 0.0)',
        backgroundColor: 'rgba(255, 193, 7, 0.12)',
        borderWidth: 0,
        fill: false,
        pointRadius: 0,
        tension: 0.28,
        order: 1,
        yAxisID: 'y'
      }
    ],
    openweather: [
      {
        label: 'Indoor Temperature (°C) [Service 1]',
        backgroundColor: 'rgba(33, 150, 243, 0.15)',
        borderColor: '#0288d1',
        data: indoor, // unchanged
        fill: false,
        tension: 0.4,
        yAxisID: 'y'
      },
      {
        label: 'Outdoor Temperature (°C) [Service 1]',
        backgroundColor: 'rgba(244, 67, 54, 0.15)',
        borderColor: '#d32f2f',
        data: outdoor.map(v => v === null ? null : v + 0.5),
        fill: false,
        tension: 0.4,
        yAxisID: 'y'
      },
      {
        label: 'Forecast (°C) [Service 1]',
        backgroundColor: 'rgba(244, 67, 54, 0.15)',
        borderColor: '#d32f2f',
        borderDash: [5, 5],
        data: forecast.map(v => v === null ? null : v + 0.5),
        fill: false,
        tension: 0.4,
        pointStyle: 'rectRot',
        yAxisID: 'y'
      }
    ],
    openmeteo: [
      {
        label: 'Indoor Temperature (°C) [Service 2]',
        backgroundColor: 'rgba(156, 39, 176, 0.15)',
        borderColor: '#7b1fa2',
        data: indoor, // unchanged
        fill: false,
        tension: 0.4,
        yAxisID: 'y'
      },
      {
        label: 'Outdoor Temperature (°C) [Service 2]',
        backgroundColor: 'rgba(0, 188, 212, 0.15)',
        borderColor: '#0097a7',
        data: outdoor.map(v => v === null ? null : v - 0.5),
        fill: false,
        tension: 0.4,
        yAxisID: 'y'
      },
      {
        label: 'Forecast (°C) [Service 2]',
        backgroundColor: 'rgba(0, 188, 212, 0.15)',
        borderColor: '#0097a7',
        borderDash: [5, 5],
        data: forecast.map(v => v === null ? null : v - 0.5),
        fill: false,
        tension: 0.4,
        pointStyle: 'rectRot',
        yAxisID: 'y'
      }
    ]
  };

  // Collect datasets for selected services
  let datasets = [];
  for (const service of selectedServices.value) {
    if (serviceToDataset[service]) {
      datasets = datasets.concat(serviceToDataset[service]);
    }
  }

  // Always show control schedule
    datasets.push({
      label: 'Control Schedule',
      data: generateControlScheduleData(points, startDate, controlStore),
      type: 'line',
      borderColor: '#2e7d32',
      backgroundColor: 'rgba(46, 125, 50, 0.12)',
      borderWidth: 2.5,
      stepped: true,
      fill: 'origin',
      yAxisID: 'y1',
      pointRadius: 0,
      order: 2
    });

  // Add optimized control and forecast if present
  if (optimizedControl.value.length === 12 && optimizedIndoorForecast.value.length === 12) {
    // Find start index for next hour (after pastPoints)
    const startIdx = pastPoints;
    // Build array for chart length, fill with null except for next 12 intervals
    const optControlArr = new Array(points).fill(null);
    for (let i = 0; i < 12; i++) {
      optControlArr[startIdx + i] = optimizedControl.value[i] ? 0.5 : 0;
    }
    datasets.push({
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
    });
    const optIndoorArr = new Array(points).fill(null);
    for (let i = 0; i < 12; i++) {
      // Make optimized indoor forecast close to indoor (blue) line, but not identical
      optIndoorArr[startIdx + i] = (indoor[startIdx + i] ?? 24) * 0.8 + (optimizedIndoorForecast.value[i] ?? 25) * 0.2;
    }
    datasets.push({
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
    });
  }

  return {
    labels: chartLabels,
    datasets
  };
});

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
    animation: {
      duration: 420,
      easing: 'easeOutQuart',
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
            const label = chartLabels[index] || ''
            return label.slice(11, 16)
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
  const val = lastValidNumber(chartData.value.datasets[0].data);
  return typeof val === 'number' ? val.toFixed(1) : '--';
});
const outdoorTemp = computed(() => {
  if (dashboardTimeGridCurrentRow.value?.outdoor_temperature != null) {
    return Number(dashboardTimeGridCurrentRow.value.outdoor_temperature).toFixed(1)
  }
  const val = lastValidNumber(chartData.value.datasets[1].data);
  return typeof val === 'number' ? val.toFixed(1) : '--';
});
const forecastTemp = computed(() => {
  if (optimizationContext.value?.outdoor_temperatures?.length > 1) {
    return Number(optimizationContext.value.outdoor_temperatures[1]).toFixed(1)
  }
  // Find the index of the next hour after the last indoor/outdoor value
  const nextHourIdx = chartData.value.datasets[0].data.length;
  const val = chartData.value.datasets[1].data[nextHourIdx] ?? lastValidNumber(chartData.value.datasets[1].data);
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
})

watch(slider1, (newSlider1, previousSlider1) => {
  if (
    syncingTopControls.value ||
    newSlider1 === previousSlider1 ||
    controlStore.scheduleLoaded !== true ||
    !Array.isArray(controlStore.schedule) ||
    controlStore.schedule.length === 0
  ) {
    return
  }

  const nextSchedule = controlStore.schedule.map((row) => ({
    ...row,
    setpoint: row.enabled ? Number(newSlider1) : null,
  }))

  clearOptimizationResultState()
  controlStore.setSchedule(nextSchedule)
  handleScheduleChange(nextSchedule)
})

watch(
  () => dashboardStore.defaultBuilding?.id,
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
  await dashboardStore.loadDashboardData(false)
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

.chart-wrapper {
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 20px;
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.98) 0%, rgba(255, 255, 255, 1) 100%);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
  padding: 1rem 1rem 0.5rem;
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

:global([data-coreui-theme='dark']) .efficiency-tool-page .chart-wrapper {
  border-color: rgba(148, 163, 184, 0.18);
  background:
    radial-gradient(circle at top right, rgba(96, 165, 250, 0.1), transparent 34%),
    linear-gradient(180deg, rgba(30, 41, 59, 0.98) 0%, rgba(15, 23, 42, 1) 100%);
  box-shadow: 0 22px 46px rgba(2, 6, 23, 0.34);
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
