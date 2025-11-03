<template>
  <div class="efficiency-tool-page">
    <CRow class="mb-4" :xs="{ gutter: 4 }">
      <CCol :sm="4">
        <CWidgetStatsA color="primary">
          <template #value>{{ indoorTemp ?? '--' }}°C</template>
          <template #title>Indoor Temperature</template>
        </CWidgetStatsA>
      </CCol>
      <CCol :sm="4">
        <CWidgetStatsA color="info">
          <template #value>{{ outdoorTemp ?? '--' }}°C</template>
          <template #title>Outdoor Temperature</template>
        </CWidgetStatsA>
      </CCol>
      <CCol :sm="4">
        <CWidgetStatsA color="warning">
          <template #value>{{ forecastTemp ?? '--' }}°C</template>
          <template #title>Next Hour Forecast</template>
        </CWidgetStatsA>
      </CCol>
    </CRow>
    <CRow class="mb-4">
      <CCol :sm="6">
        <CWidgetStatsD
          class="mb-4"
          style="--cui-card-cap-bg: #43d96b"
          :values="[
            { title: 'Consumed Last 30 Days', value: '456.5 kWhr' },
            { title: 'Consumed Today', value: '16.4 kWhr' },
          ]"
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
          class="mb-4"
          style="--cui-card-cap-bg: #ffd700"
          :values="[
            { title: 'Saved Last 30 Days', value: '15.7 kWhr' },
            { title: 'Environmental Points Earned', value: '155' },
          ]"
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
    <CCard class="mb-4">
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
                <CDropdown class="me-2" :autoClose="false">
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
   <HvacScheduleTable @optimize="runOptimization" />
    <div v-if="optimizeLoading" class="d-flex justify-content-center align-items-center my-3">
      <CSpinner color="primary" size="lg" />
      <span class="ms-3">Optimizing HVAC control...</span>
    </div>
    <CAlert
      v-if="showOptimizeAlert"
      color="success"
      dismissible
      class="my-3"
      @close="showOptimizeAlert = false"
    >
      Your optimal HVAC control is ready!
    </CAlert>
    <div class="chart-wrapper" style="overflow-x: auto; width: 100%; height: 600px;">
      <div style="width: 100%; height: 600px;">
        <CChartLine :key="chartKey" :data="chartData" :options="chartOptions" class="mb-4" style="width: 100%; height: 600px;" />
      </div>
    </div>
    <EnergyBarChart class="mb-4" />
  </div>
</template>

<script setup>
import { CChartLine } from '@coreui/vue-chartjs'
import RatingOne from '@/components/Rating.vue'
import EnergyBarChart from '@/components/EnergyBarChart.vue'
import HvacScheduleTable from '@/components/HvacScheduleTable.vue'
import { ref, computed, watch } from 'vue'
import { CRow, CCol, CWidgetStatsA, CCard, CCardBody, CFormRange, CFormSwitch, CDropdown, CDropdownToggle, CDropdownMenu, CSpinner, CAlert } from '@coreui/vue'
import { useControlStore } from '@/stores/control.js'
import { useAlertsStore } from '@/stores/alerts.js'

// Helper function for random number generation
function getSecureRandom() {
  // Use crypto.getRandomValues if available (browsers), fallback to Math.random for compatibility
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    return crypto.getRandomValues(new Uint32Array(1))[0] / (0xffffffff + 1);
  }
  return Math.random();
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

function runOptimization() {
  optimizeLoading.value = true;
  showOptimizeAlert.value = false;
  setTimeout(() => {
    optimizedControl.value = Array.from({ length: 12 }, (_, i) => i < 6);
    optimizedIndoorForecast.value = Array.from({ length: 12 }, (_, i) => 23 + Math.sin(i / 3) * 0.15 + i * 0.02);
    chartKey.value++;
    optimizeLoading.value = false;
    showOptimizeAlert.value = true;
    alertsStore.addAlert({
      description: 'You will achieve 5.6 kWhr of energy consumption gains and 5.6 environmental points.',
      timestamp: new Date().toISOString()
    });
  }, 1800);
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
const chartLabels = Array.from({ length: totalPoints }, (_, i) => {
  const d = new Date(startDate.getTime() + i * 5 * 60000);
  return d.toISOString().slice(0, 16).replace('T', ' '); // 'YYYY-MM-DD HH:mm'
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

const chartData = computed(() => {
  const points = totalPoints;
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
        backgroundColor: 'rgba(54, 162, 235, 0.15)',
        borderColor: '#1976d2',
        data: indoor,
        fill: false,
        tension: 0.4,
        yAxisID: 'y'
      },
      {
        label: 'Outdoor Temperature (°C)',
        backgroundColor: 'rgba(255, 152, 0, 0.15)',
        borderColor: '#ff9800',
        data: outdoor,
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
      borderColor: '#388e3c',
      backgroundColor: 'rgba(76,175,80,0.1)',
      borderWidth: 2,
      stepped: true,
      fill: false,
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

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  stacked: false,
  plugins: {
    legend: { display: true },
    tooltip: { enabled: true },
  },
  scales: {
    y: {
      title: {
        display: true,
        text: 'Temperature (°C)'
      },
      position: 'left',
      min: undefined,
      max: undefined,
    },
    y1: {
      title: {
        display: true,
        text: 'Control Schedule'
      },
      position: 'right',
      min: 0,
      max: 1,
      grid: {
        drawOnChartArea: false,
      },
      ticks: {
        stepSize: 0.5,
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
        text: 'Time'
      }
    }
  }
};

// Get latest values from chartData for widgets
function lastValidNumber(arr) {
  for (let i = arr.length - 1; i >= 0; --i) {
    if (typeof arr[i] === 'number') return arr[i];
  }
  return null;
}
const indoorTemp = computed(() => {
  const val = lastValidNumber(chartData.value.datasets[0].data);
  return typeof val === 'number' ? val.toFixed(1) : '--';
});
const outdoorTemp = computed(() => {
  const val = lastValidNumber(chartData.value.datasets[1].data);
  return typeof val === 'number' ? val.toFixed(1) : '--';
});
const forecastTemp = computed(() => {
  // Find the index of the next hour after the last indoor/outdoor value
  const nextHourIdx = chartData.value.datasets[0].data.length;
  const val = chartData.value.datasets[2].data[nextHourIdx] ?? lastValidNumber(chartData.value.datasets[2].data);
  return typeof val === 'number' ? val.toFixed(1) : '--';
});

const controlStore = useControlStore()
const alertsStore = useAlertsStore()

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


</script>

<style scoped>
/* ...existing code... */
.efficiency-tool-page {
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: stretch;
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
