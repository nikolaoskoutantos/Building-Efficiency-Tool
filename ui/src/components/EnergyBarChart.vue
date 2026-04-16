<template>
  <div class="energy-bar-chart">
    <div class="energy-bar-chart__header">
      <div>
        <div class="energy-bar-chart__eyebrow">{{ chartEyebrow }}</div>
        <h5 class="energy-bar-chart__title">{{ chartTitle }}</h5>
      </div>
      <div class="energy-bar-chart__legend">
        <span class="energy-bar-chart__legend-item">
          <span class="energy-bar-chart__legend-dot energy-bar-chart__legend-dot--consumption"></span>
          Projected Consumption
        </span>
        <span class="energy-bar-chart__legend-item">
          <span class="energy-bar-chart__legend-dot energy-bar-chart__legend-dot--efficiency"></span>
          Saved vs All On
        </span>
      </div>
    </div>

    <div class="energy-bar-chart__canvas">
      <CChartBar :data="barData" :options="barOptions" class="energy-bar-chart__chart" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { CChartBar } from '@coreui/vue-chartjs'
import { useColorModes } from '@coreui/vue'

const props = defineProps({
  optimizationSummary: {
    type: Object,
    default: null,
  },
})

const { colorMode } = useColorModes('coreui-free-vue-admin-template-theme')
const isDarkTheme = computed(() => colorMode.value === 'dark')

const mainData = Array.from({ length: 30 }, () => Math.floor(Math.random() * 10) + 10)
const efficiencyData = Array.from({ length: 30 }, (_, i) => ([4, 9, 14, 19, 24].includes(i) ? Math.floor(mainData[i] * 0.3) : 0))

function toChartNumber(value) {
  return typeof value === 'number' && Number.isFinite(value) ? Number(value.toFixed(3)) : null
}

const chartEyebrow = computed(() =>
  props.optimizationSummary ? 'Optimization Comparison' : 'Performance Overview',
)

const chartTitle = computed(() =>
  props.optimizationSummary ? 'Projected Energy Consumption - Next Hour' : 'Energy Consumption - Last 30 Days',
)

const barData = computed(() => {
  if (props.optimizationSummary) {
    const baselineAllOff = toChartNumber(props.optimizationSummary.baselineAllOffKwh)
    const baselineAllOn = toChartNumber(props.optimizationSummary.baselineAllOnKwh)
    const optimized = toChartNumber(props.optimizationSummary.optimizedConsumptionKwh)

    const labels = []
    const consumptionValues = []
    const savingsValues = []

    if (baselineAllOff != null) {
      labels.push('All Off')
      consumptionValues.push(baselineAllOff)
      savingsValues.push(0)
    }

    if (baselineAllOn != null) {
      labels.push('All On')
      consumptionValues.push(baselineAllOn)
      savingsValues.push(0)
    }

    if (optimized != null) {
      labels.push('Recommended')
      consumptionValues.push(optimized)
      savingsValues.push(
        baselineAllOn != null ? Number(Math.max(baselineAllOn - optimized, 0).toFixed(3)) : 0,
      )
    }

    if (labels.length > 0) {
      return {
        labels,
        datasets: [
          {
            label: 'Projected Consumption (kWh)',
            backgroundColor: 'rgba(39, 122, 226, 0.88)',
            borderColor: '#277ae2',
            borderWidth: 1,
            borderRadius: 10,
            borderSkipped: false,
            maxBarThickness: 34,
            data: consumptionValues,
            stack: 'main',
          },
          {
            label: 'Saved vs All On (kWh)',
            backgroundColor: 'rgba(47, 179, 91, 0.92)',
            borderColor: '#2fb35b',
            borderWidth: 1,
            borderRadius: 10,
            borderSkipped: false,
            maxBarThickness: 34,
            data: savingsValues,
            stack: 'main',
          },
        ],
      }
    }
  }

  return {
    labels: Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`),
    datasets: [
      {
        label: 'Energy Consumption (kWh)',
        backgroundColor: 'rgba(39, 122, 226, 0.88)',
        borderColor: '#277ae2',
        borderWidth: 1,
        borderRadius: 10,
        borderSkipped: false,
        maxBarThickness: 22,
        data: mainData,
        stack: 'main',
      },
      {
        label: 'Efficiency Achieved',
        backgroundColor: 'rgba(47, 179, 91, 0.92)',
        borderColor: '#2fb35b',
        borderWidth: 1,
        borderRadius: 10,
        borderSkipped: false,
        maxBarThickness: 22,
        data: efficiencyData,
        stack: 'main',
      },
    ],
  }
})

const barOptions = computed(() => {
  const axisColor = isDarkTheme.value ? '#cbd5e1' : '#334155'
  const tickColor = isDarkTheme.value ? '#94a3b8' : '#5c6b84'
  const gridColor = isDarkTheme.value ? 'rgba(148, 163, 184, 0.12)' : 'rgba(97, 124, 168, 0.12)'

  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: isDarkTheme.value ? 'rgba(15, 23, 42, 0.96)' : 'rgba(20, 28, 45, 0.94)',
        titleColor: '#f8fafc',
        bodyColor: '#e5eefc',
        padding: 12,
        cornerRadius: 12,
        displayColors: true,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        stacked: true,
        ticks: {
          color: tickColor,
          padding: 8,
        },
        grid: {
          color: gridColor,
          drawBorder: false,
        },
        border: {
          display: false,
        },
        title: {
          display: true,
          text: 'kWh',
          color: axisColor,
          font: {
            weight: '600',
          },
        },
      },
      x: {
        ticks: {
          maxTicksLimit: 10,
          color: tickColor,
          padding: 8,
        },
        stacked: true,
        grid: {
          display: false,
          drawBorder: false,
        },
        border: {
          display: false,
        },
        title: {
          display: true,
          text: props.optimizationSummary ? 'Scenario' : 'Day',
          color: axisColor,
          font: {
            weight: '600',
          },
        },
      },
    },
  }
})
</script>

<style scoped>
.energy-bar-chart {
  margin: 1.25rem 0 1.75rem;
  border: 1px solid rgba(172, 199, 255, 0.35);
  border-radius: 26px;
  padding: 1.6rem 1.75rem 1.9rem;
  background:
    linear-gradient(180deg, rgba(248, 251, 255, 0.98), rgba(239, 246, 255, 0.9));
  box-shadow:
    0 20px 45px rgba(106, 137, 179, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.energy-bar-chart__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.energy-bar-chart__eyebrow {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #6b87b3;
  margin-bottom: 0.3rem;
}

.energy-bar-chart__title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: #22324d;
}

.energy-bar-chart__legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.9rem 1.1rem;
  padding-top: 0.15rem;
}

.energy-bar-chart__legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.88rem;
  font-weight: 600;
  color: #50627e;
}

.energy-bar-chart__legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
}

.energy-bar-chart__legend-dot--consumption {
  background: #277ae2;
  box-shadow: 0 0 0 4px rgba(39, 122, 226, 0.14);
}

.energy-bar-chart__legend-dot--efficiency {
  background: #2fb35b;
  box-shadow: 0 0 0 4px rgba(47, 179, 91, 0.14);
}

.energy-bar-chart__canvas {
  min-height: 390px;
}

.energy-bar-chart__chart {
  width: 100%;
  height: 390px;
}

:global([data-coreui-theme='dark']) .energy-bar-chart {
  border-color: rgba(148, 163, 184, 0.18);
  background:
    radial-gradient(circle at top right, rgba(96, 165, 250, 0.1), transparent 34%),
    linear-gradient(180deg, rgba(30, 41, 59, 0.98), rgba(15, 23, 42, 1));
  box-shadow:
    0 22px 46px rgba(2, 6, 23, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

:global([data-coreui-theme='dark']) .energy-bar-chart__eyebrow {
  color: #8eb5ff;
}

:global([data-coreui-theme='dark']) .energy-bar-chart__title,
:global([data-coreui-theme='dark']) .energy-bar-chart__legend-item {
  color: #e2e8f0;
}

@media (max-width: 768px) {
  .energy-bar-chart {
    padding: 1.2rem 1rem 1.35rem;
    border-radius: 20px;
  }

  .energy-bar-chart__header {
    flex-direction: column;
  }

  .energy-bar-chart__legend {
    justify-content: flex-start;
  }

  .energy-bar-chart__canvas,
  .energy-bar-chart__chart {
    min-height: 330px;
    height: 330px;
  }
}
</style>
