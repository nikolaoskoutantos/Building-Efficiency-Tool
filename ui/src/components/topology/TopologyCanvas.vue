<template>
  <div class="topo-canvas-wrap">
    <div v-if="loading && !nodes.length" class="topo-canvas-state">
      <div class="topo-canvas-spinner" />
      <span>Loading topology…</span>
    </div>
    <div v-else-if="!loading && error" class="topo-canvas-state">
      <span style="color:#f87171;">{{ error }}</span>
    </div>
    <div v-else-if="!loading && !nodes.length" class="topo-canvas-state">
      <span>No HVAC units found for this building.</span>
    </div>
    <VueFlow
      v-else
      :nodes="nodes"
      :edges="edges"
      :node-types="nodeTypes"
      :nodes-draggable="true"
      :nodes-connectable="false"
      :elements-selectable="true"
      :fit-view-on-init="true"
      :min-zoom="0.3"
      :max-zoom="2"
      class="topo-flow"
      @node-context-menu="onNodeContextMenu"
      @pane-click="closeCtxMenu"
      @node-click="closeCtxMenu"
    >
      <Background :variant="BackgroundVariant.Dots" :gap="22" :size="1.5" color="rgba(0,0,0,0.1)" />
      <Controls :show-interactive="false" class="topo-controls" />

      <Panel position="bottom-right" class="topo-beta">
        <span class="topo-beta__dot" />
        Beta Version
      </Panel>

      <Panel position="top-right" class="topo-legend">
        <div class="legend-row"><span class="ld ld--on" />HVAC On</div>
        <div class="legend-row"><span class="ld ld--off" />HVAC Off</div>
      </Panel>
    </VueFlow>

    <ContextMenu
      :visible="ctxMenu.visible"
      :x="ctxMenu.x"
      :y="ctxMenu.y"
      :title="ctxMenu.title"
      :items="ctxMenu.items"
      @select="onCtxSelect"
      @close="closeCtxMenu"
    />
  </div>
</template>

<script setup>
import { ref, markRaw, onMounted, onUnmounted, watch } from 'vue'
import { VueFlow, Panel } from '@vue-flow/core'
import { Background, BackgroundVariant } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/controls/dist/style.css'

import HvacNode    from './HvacNode.vue'
import ZoneNode    from './ZoneNode.vue'
import SensorNode  from './SensorNode.vue'
import ContextMenu from './ContextMenu.vue'

import { useDashboardStore } from '@/stores/dashboard.js'
import { useAuthStore }      from '@/stores/auth.js'
import { buildApiUrl }       from '@/config/api.js'

const emit = defineEmits(['edit-device', 'rotate-key', 'set-setpoint'])

const props = defineProps({
  buildingId: { type: Number, default: null },
})

const ZONE_V_GAP   = 170
const SENSOR_V_GAP = 115

const nodeTypes = { hvac: markRaw(HvacNode), zone: markRaw(ZoneNode), sensor: markRaw(SensorNode) }

const dashboardStore = useDashboardStore()
const authStore      = useAuthStore()

const nodes   = ref([])
const edges   = ref([])
const loading = ref(false)
const error   = ref('')

const ctxMenu = ref({ visible: false, x: 0, y: 0, title: '', items: [], nodeData: null, nodeType: '' })

let refreshTimer = null

// ── Context menu ──────────────────────────────────────────────────────────────

function closeCtxMenu() {
  ctxMenu.value.visible = false
}

function menuItemsFor(node) {
  if (node.type === 'hvac') {
    const hasControllableZone = Array.isArray(node.data.zones) && node.data.zones.some(z => z.is_controllable)
    return [
      ...(hasControllableZone ? [{ icon: '⚡', label: 'Set Setpoint', action: 'set-setpoint' }, { divider: true }] : []),
      { icon: '✏️', label: 'Edit Device',  action: 'edit-device'  },
      { icon: '🔑', label: 'Rotate Key',   action: 'rotate-key'   },
      { divider: true },
      { icon: '📋', label: 'Copy Name',    action: 'copy-name'    },
    ]
  }
  if (node.type === 'zone') {
    return [
      ...(node.data.is_controllable
        ? [{ icon: '⚡', label: 'Set Setpoint', action: 'set-setpoint' }, { divider: true }]
        : []),
      { icon: '📋', label: 'Copy Zone Name', action: 'copy-name' },
    ]
  }
  if (node.type === 'sensor') {
    return [
      ...(node.data.is_controllable
        ? [{ icon: '⚡', label: 'Set Setpoint', action: 'set-setpoint' }, { divider: true }]
        : []),
      { icon: '📋', label: 'Copy Sensor Name',   action: 'copy-name'  },
      { icon: '📊', label: 'Copy Current Value', action: 'copy-value' },
      { icon: '🔗', label: 'Copy Sensor ID',     action: 'copy-id'    },
    ]
  }
  return []
}

function onNodeContextMenu({ node, event }) {
  event.preventDefault()
  const PAD_X = 200
  const PAD_Y = 160
  const x = Math.min(event.clientX, window.innerWidth  - PAD_X)
  const y = Math.min(event.clientY, window.innerHeight - PAD_Y)

  ctxMenu.value = {
    visible:  true,
    x, y,
    title:    node.data.name || node.data.sensor_type || '',
    items:    menuItemsFor(node),
    nodeData: node.data,
  }
}

function dispatchSetpoint(nodeData) {
  if (Array.isArray(nodeData.zones)) {
    for (const zone of nodeData.zones) {
      const target = zone.sensors?.find(s => s.is_controllable)
      if (target) { emit('set-setpoint', { ...target, zone_name: zone.name, thermostat_name: zone.thermostat_name }); return }
    }
  } else if (Array.isArray(nodeData.sensors)) {
    const target = nodeData.sensors.find(s => s.is_controllable)
    if (target) emit('set-setpoint', { ...target, zone_name: nodeData.name, thermostat_name: nodeData.thermostat_name })
  } else {
    emit('set-setpoint', nodeData)
  }
}

function onCtxSelect(action) {
  const { nodeData } = ctxMenu.value
  closeCtxMenu()
  const ACTIONS = {
    'copy-name':    () => navigator.clipboard.writeText(nodeData.name || nodeData.sensor_type || ''),
    'copy-value':   () => navigator.clipboard.writeText(String(nodeData.value ?? '--')),
    'copy-id':      () => navigator.clipboard.writeText(String(nodeData.id ?? '')),
    'edit-device':  () => emit('edit-device', nodeData.id),
    'rotate-key':   () => emit('rotate-key', nodeData.id),
    'set-setpoint': () => dispatchSetpoint(nodeData),
  }
  ACTIONS[action]?.()
}

// Escape key closes the menu
function onKeydown(e) {
  if (e.key === 'Escape') closeCtxMenu()
}

// ── Topology loading ──────────────────────────────────────────────────────────

function buildGraph(topology) {
  const newNodes = [], newEdges = []
  let cursor = 60

  for (const unit of topology.units) {
    const unitStart = cursor
    for (const zone of unit.zones) {
      const zoneY        = cursor
      const sensorCount  = zone.sensors.length
      const sensorBlockH = Math.max(sensorCount * SENSOR_V_GAP, ZONE_V_GAP)

      newNodes.push({ id: `zone-${zone.id}`, type: 'zone', position: { x: 340, y: zoneY + sensorBlockH / 2 - 32 }, data: { ...zone, hvac_unit_id: unit.id } })
      newEdges.push({
        id: `e-u${unit.id}-z${zone.id}`, source: `unit-${unit.id}`, target: `zone-${zone.id}`,
        animated: zone.hvac_is_on,
        style: zone.hvac_is_on
          ? { stroke: '#10b981', strokeWidth: 2.5 }
          : { stroke: '#cbd5e1', strokeWidth: 1.5, strokeDasharray: '6 4' },
      })
      zone.sensors.forEach((sensor, si) => {
        newNodes.push({ id: `sensor-${sensor.id}`, type: 'sensor', position: { x: 600, y: zoneY + si * SENSOR_V_GAP + 8 }, data: { ...sensor, zone_setpoint: zone.setpoint ?? null } })
        newEdges.push({
          id: `e-z${zone.id}-s${sensor.id}`, source: `zone-${zone.id}`, target: `sensor-${sensor.id}`,
          animated: sensor.value != null,
          style: { stroke: '#a5b4fc', strokeWidth: 1.5 },
        })
      })
      cursor += sensorBlockH
    }
    newNodes.push({ id: `unit-${unit.id}`, type: 'hvac', position: { x: 80, y: (unitStart + cursor) / 2 - 36 }, data: unit })
    cursor += 40
  }
  nodes.value = newNodes
  edges.value = newEdges
}

async function load() {
  const bid = props.buildingId ?? dashboardStore.activeBuilding?.id
  if (!bid) return
  loading.value = true
  error.value   = ''
  try {
    const token = authStore.getJwtToken?.()
    const res = await fetch(buildApiUrl(`/dashboard/topology/${bid}`), {
      headers:     token ? { Authorization: `Bearer ${token}` } : {},
      credentials: 'include',
    })
    if (!res.ok) {
      const d = await res.json().catch(() => ({}))
      throw new Error(d?.detail || `HTTP ${res.status}`)
    }
    buildGraph(await res.json())
  } catch (e) {
    error.value = `Failed to load topology: ${e.message}`
  } finally {
    loading.value = false
  }
}

watch(
  () => props.buildingId ?? dashboardStore.activeBuilding?.id,
  (id) => { if (id) load() },
  { immediate: true },
)

onMounted(async () => {
  if (!dashboardStore.buildings.length) await dashboardStore.loadDashboardData(false)
  refreshTimer = setInterval(load, 10_000)
  document.addEventListener('keydown', onKeydown)
})
onUnmounted(() => {
  clearInterval(refreshTimer)
  document.removeEventListener('keydown', onKeydown)
})

defineExpose({ load })
</script>

<style scoped>
.topo-canvas-wrap {
  width: 100%;
  height: 720px;
  background: #ffffff;
  border-radius: 16px;
  overflow: hidden;
  position: relative;
}

.topo-flow { width: 100%; height: 100%; background: #ffffff !important; }

.topo-canvas-state {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 12px; color: #94a3b8; font-size: 13px;
  z-index: 1;
}
.topo-canvas-spinner {
  width: 28px; height: 28px; border-radius: 50%;
  border: 3px solid rgba(37,99,235,0.12);
  border-top-color: #3b82f6;
  animation: spin 0.9s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.topo-legend {
  background: rgba(255,255,255,0.92) !important;
  border: 1px solid rgba(0,0,0,0.08) !important;
  border-radius: 10px !important;
  padding: 8px 12px !important;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08) !important;
  display: flex; flex-direction: column; gap: 5px;
}
.legend-row { display: flex; align-items: center; gap: 7px; font-size: 11px; color: #475569; font-weight: 500; }
.ld { display: inline-block; width: 20px; height: 2px; border-radius: 2px; }
.ld--on { background: #10b981; box-shadow: 0 0 4px rgba(16,185,129,0.4); }
.ld--off { border-top: 1.5px dashed #cbd5e1; background: transparent; }

:deep(.vue-flow__handle) { opacity: 0.5 !important; }
:deep(.vue-flow__controls) {
  background: rgba(255,255,255,0.92) !important;
  border: 1px solid rgba(0,0,0,0.08) !important;
  border-radius: 10px !important;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08) !important;
  overflow: hidden;
}
:deep(.vue-flow__controls-button) { background: transparent !important; border: none !important; color: #374151 !important; }
:deep(.vue-flow__controls-button:hover) { background: #f3f4f6 !important; color: #111827 !important; }

.topo-beta {
  display: flex !important;
  align-items: center;
  gap: 6px;
  background: rgba(15, 23, 42, 0.78) !important;
  backdrop-filter: blur(6px);
  border: 1px solid rgba(148, 163, 184, 0.18) !important;
  border-radius: 999px !important;
  padding: 4px 12px 4px 8px !important;
  font-size: 10px;
  font-weight: 700;
  color: rgba(226, 232, 240, 0.82);
  letter-spacing: 0.07em;
  text-transform: uppercase;
  pointer-events: none;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.18) !important;
}

.topo-beta__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #38bdf8;
  box-shadow: 0 0 5px #38bdf8;
  flex-shrink: 0;
  animation: beta-pulse 2.4s ease-in-out infinite;
}

@keyframes beta-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.45; transform: scale(0.8); }
}
</style>
