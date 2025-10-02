<template>
  <div style="display: flex; justify-content: center; align-items: center; width: 100%; min-height: 500px;">
    <div style="flex: 1 1 0; display: flex; justify-content: center;">
      <div style="overflow-x: auto; width: 100%;">
        <div style="width: 100%; min-width: 350px;">
          <CChartBar :data="barData" :options="barOptions" style="width: 100%; height: 400px; min-width: 350px;" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { CChartBar } from '@coreui/vue-chartjs'

// Example: Only some days have efficiency achieved (green bar)
const mainData = Array.from({ length: 30 }, () => Math.floor(Math.random() * 10) + 10)
// Let's say days 5, 10, 15, 20, 25 have efficiency achieved
const efficiencyData = Array.from({ length: 30 }, (_, i) => ([4, 9, 14, 19, 24].includes(i) ? Math.floor(mainData[i] * 0.3) : 0))

const barData = ref({
  labels: Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`),
  datasets: [
    {
      label: 'Energy Consumption (kWh)',
      backgroundColor: '#0d6efd',
      data: mainData,
      stack: 'main',
    },
    {
      label: 'Efficiency Achieved',
      backgroundColor: 'green',
      data: efficiencyData,
      stack: 'main',
    },
  ],
})

const barOptions = ref({
  responsive: true,
  plugins: {
    legend: { display: false },
    title: {
      display: true,
      text: 'Energy Consumption - Last 30 Days',
    },
  },
  scales: {
    y: {
      title: {
        display: true,
        text: 'kWh',
      },
      beginAtZero: true,
      stacked: true,
    },
    x: {
      title: {
        display: true,
        text: 'Day',
      },
      ticks: {
        maxTicksLimit: 10,
      },
      stacked: true,
    },
  },
})
</script>
