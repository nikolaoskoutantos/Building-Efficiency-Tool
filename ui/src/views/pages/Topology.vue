<template>
  <div class="topology-page">
    <div class="topology-header">
      <div class="topology-header__left">
        <span class="topology-header__title">System Topology</span>
        <span v-if="buildingName" class="topology-header__building">{{ buildingName }}</span>
      </div>
    </div>
    <TopologyCanvas class="topology-canvas-full" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import TopologyCanvas from '@/components/topology/TopologyCanvas.vue'
import { useDashboardStore } from '@/stores/dashboard.js'

const dashboardStore = useDashboardStore()
const buildingName = computed(() => dashboardStore.defaultBuilding?.name || '')
</script>

<style scoped>
.topology-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  background: #0b1120;
  border-radius: 16px;
  overflow: hidden;
}

.topology-header {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  background: rgba(15, 23, 42, 0.95);
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  flex-shrink: 0;
  gap: 12px;
}

.topology-header__title {
  font-size: 15px;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: 0.02em;
}

.topology-header__building {
  font-size: 12px;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 20px;
  padding: 2px 10px;
  font-weight: 600;
}

.topology-canvas-full {
  flex: 1;
  min-height: 0;
}

:deep(.topo-canvas-wrap) {
  height: 100% !important;
  border-radius: 0 !important;
}
</style>
