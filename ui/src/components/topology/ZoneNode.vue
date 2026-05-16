<template>
  <div class="topo-node topo-node--zone" :class="{ 'topo-node--active': data.hvac_is_on, 'topo-node--controllable': data.is_controllable }">
    <Handle type="target" :position="Position.Left" class="topo-handle" />
    <Handle type="source" :position="Position.Right" class="topo-handle" />
    <div class="topo-node__body">
      <div v-if="data.hvac_is_on" class="topo-node__active-ring" />
      <div class="topo-node__temp">
        <span class="topo-node__temp-value">{{ tempDisplay }}</span>
        <span class="topo-node__temp-unit">°C</span>
      </div>
      <div v-if="data.hvac_is_on" class="topo-node__on-badge">ON</div>
      <div v-if="data.is_controllable" class="topo-node__ctrl-badge" :title="`Controllable — ${data.thermostat_name || 'thermostat'} — right-click to set setpoint`">⚡</div>
    </div>
    <div class="topo-node__label">{{ data.name }}</div>
    <div v-if="data.is_controllable && data.thermostat_name" class="topo-node__ctrl-label">{{ data.thermostat_name }}</div>
  </div>
</template>

<script setup>
import { Handle, Position } from '@vue-flow/core'
import { computed } from 'vue'

const props = defineProps({ data: { type: Object, required: true } })

const tempDisplay = computed(() =>
  props.data.temperature == null ? '--' : props.data.temperature.toFixed(1)
)
</script>

<style scoped>
.topo-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: default;
  user-select: none;
}

.topo-node__body {
  position: relative;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(255,255,255,0.94) 0%, rgba(240,253,244,0.96) 100%);
  border: 2px solid rgba(100,116,139,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 1px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.06);
  transition: border-color 0.3s, box-shadow 0.3s;
}

.topo-node--active .topo-node__body {
  border-color: #34d399;
  box-shadow: 0 4px 16px rgba(0,0,0,0.3), 0 0 18px rgba(52,211,153,0.3);
}

.topo-node__active-ring {
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  border: 2px solid rgba(52, 211, 153, 0.4);
  animation: zone-pulse 2s ease-in-out infinite;
  pointer-events: none;
}

@keyframes zone-pulse {
  0%, 100% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.1); opacity: 0.3; }
}

.topo-node__temp {
  display: flex;
  align-items: baseline;
  gap: 1px;
}

.topo-node__temp-value {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1;
}

.topo-node__temp-unit {
  font-size: 10px;
  color: #475569;
  font-weight: 600;
}

.topo-node--active .topo-node__temp-value { color: #059669; }

.topo-node__on-badge {
  font-size: 8px;
  font-weight: 800;
  color: #059669;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.topo-node__label {
  font-size: 11px;
  font-weight: 700;
  color: #0f172a;
  text-align: center;
  max-width: 90px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topo-node__sub {
  font-size: 10px;
  color: #475569;
  font-weight: 500;
}

.topo-node--controllable .topo-node__body {
  border-color: rgba(251, 191, 36, 0.7);
  box-shadow: 0 4px 16px rgba(0,0,0,0.3), 0 0 14px rgba(251,191,36,0.22);
}

.topo-node__ctrl-badge {
  position: absolute;
  top: 3px;
  right: 3px;
  font-size: 10px;
  line-height: 1;
  filter: drop-shadow(0 0 3px rgba(251,191,36,0.9));
}

.topo-node__ctrl-label {
  font-size: 9px;
  font-weight: 600;
  color: #92400e;
  text-align: center;
  max-width: 90px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topo-handle {
  background: #34d399 !important;
  border: 2px solid #0f172a !important;
  width: 8px !important;
  height: 8px !important;
}

.topo-node--active .topo-handle { background: #34d399 !important; }
</style>
