<template>
  <div class="topo-node topo-node--sensor" :class="{ 'topo-node--fresh': isFresh, 'topo-node--controllable': data.is_controllable }">
    <Handle type="target" :position="Position.Left" class="topo-handle" />
    <div class="topo-node__body">
      <span class="topo-node__icon">{{ sensorIcon }}</span>
      <div class="topo-node__value">{{ valueDisplay }}</div>
      <div class="topo-node__status-dot" :class="isFresh ? 'topo-node__status-dot--live' : 'topo-node__status-dot--dead'" :title="isFresh ? 'Live — reported within 5 min' : 'No recent data'" />
      <div v-if="data.is_controllable" class="topo-node__ctrl-badge" title="Controllable — right-click to set setpoint">⚡</div>
    </div>
    <div class="topo-node__label">{{ shortType }}</div>
  </div>
</template>

<script setup>
import { Handle, Position } from '@vue-flow/core'
import { computed } from 'vue'
import { useControlStore } from '@/stores/control.js'

const props = defineProps({ data: { type: Object, required: true } })
const controlStore = useControlStore()

const ICONS = {
  temperature: '🌡',
  humidity: '💧',
  co2: '🌫',
  presence: '👤',
  occupancy: '👤',
  energy: '⚡',
  hvac_power: '⚡',
  hvac_status: '❄',
  setpoint: '🎯',
  default: '📡',
}

const sensorIcon = computed(() => {
  const t = (props.data.sensor_type || '').toLowerCase()
  return ICONS[t] || ICONS.default
})

const shortType = computed(() => {
  return (props.data.sensor_type || 'sensor')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
})

function formatNumeric(num, unit) {
  const formatted = Math.abs(num) < 10 ? num.toFixed(1) : Math.round(num).toString()
  return unit ? `${formatted}${unit}` : formatted
}

function setpointDisplay() {
  const zoneId = props.data.zone_id ?? null
  const sp = controlStore.getZoneSetpoint(zoneId) ?? props.data.zone_setpoint
  return sp != null ? formatNumeric(Number(sp), props.data.unit) : null
}

const valueDisplay = computed(() => {
  if (props.data.is_controllable) {
    const sp = setpointDisplay()
    if (sp != null) return sp
  }
  const { value, value_text, value_bool, unit } = props.data
  if (value != null) return formatNumeric(value, unit)
  if (value_text != null) return value_text
  if (value_bool != null) return value_bool ? 'ON' : 'OFF'
  return '--'
})

const isFresh = computed(() => {
  if (!props.data.last_seen) return false
  return (Date.now() - new Date(props.data.last_seen).getTime()) < 5 * 60 * 1000
})
</script>

<style scoped>
.topo-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  cursor: default;
  user-select: none;
}

.topo-node__body {
  position: relative;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(255,255,255,0.93) 0%, rgba(245,243,255,0.95) 100%);
  border: 2px solid rgba(129,140,248,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 1px;
  box-shadow: 0 4px 14px rgba(0,0,0,0.28);
  transition: border-color 0.3s, box-shadow 0.3s;
}

.topo-node--fresh .topo-node__body {
  border-color: #818cf8;
  box-shadow: 0 4px 14px rgba(0,0,0,0.28), 0 0 14px rgba(129,140,248,0.25);
}

.topo-node__icon { font-size: 18px; line-height: 1; }

.topo-node__value {
  font-size: 10px;
  font-weight: 700;
  color: #3730a3;
  line-height: 1;
  max-width: 44px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: center;
}

.topo-node__label {
  font-size: 9px;
  font-weight: 600;
  color: #334155;
  text-align: center;
  max-width: 70px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topo-node--controllable .topo-node__body {
  border-color: rgba(251, 191, 36, 0.6);
  box-shadow: 0 4px 14px rgba(0,0,0,0.28), 0 0 10px rgba(251,191,36,0.2);
}

.topo-node__ctrl-badge {
  position: absolute;
  top: 3px;
  left: 3px;
  font-size: 9px;
  line-height: 1;
  filter: drop-shadow(0 0 3px rgba(251,191,36,0.8));
}

.topo-node__status-dot {
  position: absolute;
  bottom: 4px;
  right: 4px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 2px solid rgba(255,255,255,0.9);
}

.topo-node__status-dot--live {
  background: #22c55e;
  box-shadow: 0 0 5px #22c55e;
  animation: dot-pulse 2s ease-in-out infinite;
}

.topo-node__status-dot--dead {
  background: #94a3b8;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}

.topo-handle {
  background: #818cf8 !important;
  border: 2px solid #0f172a !important;
  width: 7px !important;
  height: 7px !important;
}
</style>
