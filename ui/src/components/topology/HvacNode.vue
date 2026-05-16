<template>
  <div class="topo-node topo-node--hvac" :class="{ 'topo-node--online': isOnline }">
    <Handle type="source" :position="Position.Right" class="topo-handle" />
    <div class="topo-node__ring" />
    <div class="topo-node__body">
      <span class="topo-node__icon">{{ unitIcon }}</span>
      <div class="topo-node__status-dot" :class="isOnline ? 'topo-node__status-dot--online' : 'topo-node__status-dot--offline'" />
    </div>
    <div class="topo-node__label">{{ data.name }}</div>
    <div class="topo-node__sub">{{ data.unit_type }}</div>
  </div>
</template>

<script setup>
import { Handle, Position } from '@vue-flow/core'
import { computed } from 'vue'

const props = defineProps({ data: { type: Object, required: true } })

const isOnline = computed(() => props.data.connection_status === 'online')

const unitIcon = computed(() => {
  const t = (props.data.unit_type || '').toLowerCase()
  if (t.includes('heat_pump') || t.includes('pump')) return '♨'
  if (t.includes('chiller')) return '❄'
  if (t.includes('boiler')) return '🔥'
  if (t.includes('fan')) return '🌀'
  if (t.includes('ahu')) return '💨'
  return '❄'
})
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

.topo-node__ring {
  position: absolute;
  inset: -6px;
  border-radius: 50%;
  border: 2px solid rgba(56, 189, 248, 0.25);
  animation: ring-pulse 3s ease-in-out infinite;
  pointer-events: none;
}

.topo-node--online .topo-node__ring {
  border-color: rgba(56, 189, 248, 0.55);
  animation: ring-pulse 2s ease-in-out infinite;
}

@keyframes ring-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.08); opacity: 0.6; }
}

.topo-node__body {
  position: relative;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(240,249,255,0.98) 100%);
  border: 2px solid rgba(56, 189, 248, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.35), 0 0 0 1px rgba(255,255,255,0.08);
}

.topo-node--online .topo-node__body {
  border-color: #38bdf8;
  box-shadow: 0 4px 20px rgba(0,0,0,0.35), 0 0 20px rgba(56,189,248,0.25);
}

.topo-node__icon {
  font-size: 28px;
  line-height: 1;
  filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.6));
}

.topo-node__status-dot {
  position: absolute;
  bottom: 4px;
  right: 4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #0f172a;
}
.topo-node__status-dot--online { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
.topo-node__status-dot--offline { background: #6b7280; }

.topo-node__label {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
  text-align: center;
  max-width: 100px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topo-node__sub {
  font-size: 10px;
  color: #0369a1;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
}

.topo-handle {
  background: #38bdf8 !important;
  border: 2px solid #0f172a !important;
  width: 10px !important;
  height: 10px !important;
}
</style>
