<template>
  <div class="efficiency-tool-page">
    <CRow class="mb-4" :xs="{ gutter: 4 }">
      <CCol :sm="4">
        <CWidgetStatsA color="primary">
          <template #value>{{ indoorTemp }}°C</template>
          <template #title>Indoor Temperature</template>
        </CWidgetStatsA>
      </CCol>
      <CCol :sm="4">
        <CWidgetStatsA color="info">
          <template #value>{{ outdoorTemp }}°C</template>
          <template #title>Outdoor Temperature</template>
        </CWidgetStatsA>
      </CCol>
      <CCol :sm="4">
        <CWidgetStatsA color="warning">
          <template #value>{{ forecastTemp }}°C</template>
          <template #title>Next Hour Forecast</template>
        </CWidgetStatsA>
      </CCol>
    </CRow>
    <!-- Card with CoreUI Switch and Text Pill moved after widgets -->
    <CCard class="mb-4">
      <CCardBody class="d-flex align-items-center justify-content-between">
        <div class="d-flex align-items-center">
          <span v-c-tooltip="{ content: 'Last alert: All systems nominal', placement: 'top' }" style="display: flex; align-items: center;">
            <CFormSwitch size="xl" v-model="switchValue" :color="switchValue ? 'success' : 'danger'" class="me-3" />
          </span>
          <span :class="['badge', 'rounded-pill', switchValue ? 'bg-success' : 'bg-danger', 'text-light', 'ms-2']">
            Switch is {{ switchValue ? 'On' : 'Off' }}
            <span style="font-weight: bold; color: #fff; font-size: 1.2em; margin-left: 0.3em;" v-c-tooltip="{ content: 'If you choose to turn off heating for 30 minutes you will achieve 30% more energy efficiency', placement: 'top' }">&#33;</span>
          </span>
        </div>
        <div class="ms-auto">
          <RatingOne />
        </div>
      </CCardBody>
      <CCardBody>
        <CRow>
          <CCol :sm="6">
            <label for="slider1" class="form-label">Indoor Temperature</label>
            <div class="d-flex justify-content-between align-items-center mb-1">
              <span style="font-size: 0.95em; color: #0d6efd; font-weight: 500;">Cooler</span>
              <span style="font-size: 0.95em; color: #dc3545; font-weight: 500;">Warmer</span>
            </div>
            <CFormRange id="slider1" v-model="slider1" min="0" max="100" />
          </CCol>
          <CCol :sm="6">
            <label for="slider2" class="form-label">Rate Indoor Temperature</label>
            <div class="d-flex justify-content-between align-items-center mb-1">
              <span style="font-size: 0.95em; color: #0d6efd; font-weight: 500;">Cooler</span>
              <span style="font-size: 0.95em; color: #dc3545; font-weight: 500;">Warmer</span>
            </div>
            <CFormRange id="slider2" v-model="slider2" min="0" max="100" />
          </CCol>
        </CRow>
      </CCardBody>
    </CCard>
    <div class="chart-wrapper" style="overflow-x: auto; width: 100%;">
      <div style="min-width: 600px; width: 100%;">
        <CChartLine :key="chartKey" :data="chartData" :options="chartOptions" class="mb-4" style="width: 100%; min-width: 600px;" />
      </div>
    </div>
    <ServicesTable />
    <EnergyBarChart class="mb-4" />


  </div>
</template>

<script setup>
import { CChartLine } from '@coreui/vue-chartjs'
import ServicesTable from '@/components/ServicesTable.vue'
import RatingOne from '@/components/Rating.vue'
import EnergyBarChart from '@/components/EnergyBarChart.vue'
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { CRow, CCol, CWidgetStatsA, CCard, CCardBody, CButton, CTooltip, CFormRange, CFormSwitch } from '@coreui/vue'
import { useControlStore } from '@/stores/control.js'

const chartKey = ref(0)

const chartData = ref({
  labels: ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00'],
  datasets: [
    {
      label: 'Indoor Temperature (°C)',
      backgroundColor: 'rgba(54, 162, 235, 0.2)',
      borderColor: 'rgba(54, 162, 235, 1)',
      data: [23, 23.1, 23.2, 23.3, 23.4, 23.5, 23.6],
      fill: false,
      tension: 0.4,
    },
    {
      label: 'Outdoor Temperature (°C)',
      backgroundColor: 'rgba(255, 99, 132, 0.2)',
      borderColor: 'rgba(255, 99, 132, 1)',
      data: [22, 22.2, 22.3, 22.4, 22.5, 22.6, 22.7],
      fill: false,
      tension: 0.4,
    },
    {
      label: 'Forecast (°C)',
      backgroundColor: 'rgba(255, 206, 86, 0.2)',
      borderColor: 'rgba(255, 206, 86, 1)',
      borderDash: [5, 5],
      data: [23.7, 23.8, 23.9, 24, 24.1, 24.2, 24.3, 24.5, 24.6, 24.75, 24.9, 25, 25.2],
      fill: false,
      tension: 0.4,
      pointStyle: 'rectRot',
    },
    {
      label: 'Forecast Upper Bound',
      data: [24, 24.3, 24.1, 24.5, 24.6, 24.8, 24.7, 25, 25.2, 25.1, 25.4, 25.3, 25.7],
      borderColor: 'rgba(255, 206, 86, 0.1)',
      backgroundColor: 'rgba(255, 206, 86, 0.1)',
      borderWidth: 0,
      fill: '+1',
      pointRadius: 0,
      tension: 0.4,
      order: 1,
    },
    {
      label: 'Forecast Lower Bound',
      data: [23.4, 23.6, 23.7, 23.8, 23.9, 24, 24.1, 24.2, 24.3, 24.4, 24.5, 24.6, 24.7],
      borderColor: 'rgba(255, 206, 86, 0.1)',
      backgroundColor: 'rgba(255, 206, 86, 0.1)',
      borderWidth: 0,
      fill: false,
      pointRadius: 0,
      tension: 0.4,
      order: 1,
    },
  ],
})

const chartOptions = ref({
  responsive: true,
  plugins: {
    legend: {
      position: 'top',
    },
    title: {
      display: true,
      text: 'Indoor & Outdoor Temperature with Forecast',
    },
  },
  scales: {
    y: {
      title: {
        display: true,
        text: 'Temperature (°C)'
      }
    },
    x: {
      title: {
        display: true,
        text: 'Time'
      }
    }
  }
})

// Get latest values from chartData for widgets
const indoorTemp = computed(() => chartData.value.datasets[0].data.at(-1))
const outdoorTemp = computed(() => chartData.value.datasets[1].data.at(-1))
const forecastTemp = computed(() => {
  // Find the index of the next hour after the last indoor/outdoor value
  const nextHourIdx = chartData.value.datasets[0].data.length
  return chartData.value.datasets[2].data[nextHourIdx] ?? chartData.value.datasets[2].data.at(-1)
})

const controlStore = useControlStore()

const isOn = ref(false)
const tempAdjust = ref(0)
const isBlockOn = ref(false)
const switchValue = ref(controlStore.preferences.switchValue)
const slider1 = ref(controlStore.preferences.slider1)
const slider2 = ref(controlStore.preferences.slider2)

watch([switchValue, slider1, slider2], ([newSwitch, newSlider1, newSlider2]) => {
  controlStore.setPreferences({
    switchValue: newSwitch,
    slider1: newSlider1,
    slider2: newSlider2
  })
})

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

onMounted(() => {
  function handleResize() {
    chartKey.value++
  }
  window.addEventListener('resize', handleResize)
  onBeforeUnmount(() => {
    window.removeEventListener('resize', handleResize)
  })
})
</script>

<style scoped>
.efficiency-tool-page {
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
.control-block {
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}
.chart-wrapper {
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
.chart-wrapper canvas {
  width: 100%;
  height: 500px;
  max-width: 100%;
  min-width: 0;
}
.fullwidth-block {
  width: 100%;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  padding: 1.5rem 1rem;
  display: flex;
  align-items: center;
  justify-content: flex-start;
}
@media (max-width: 600px) {
  .chart-wrapper canvas {
    height: 420px;
    min-height: 300px;
    width: 100vw;
    margin-left: -16px;
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
