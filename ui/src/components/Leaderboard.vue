<template>
  <COffcanvas :visible="visible" :backdrop="false" placement="end" @hide="emit('close')" class="leaderboard-panel">
    <COffcanvasHeader class="leaderboard-panel__header">
      <div>
        <div class="leaderboard-panel__eyebrow">Sustainability</div>
        <COffcanvasTitle>Leaderboard</COffcanvasTitle>
      </div>
      <CButton class="btn-close" @click="emit('close')" aria-label="Close"></CButton>
    </COffcanvasHeader>
    <COffcanvasBody class="leaderboard-panel__body">
      <div class="leaderboard-summary">
        <div>
          <div class="leaderboard-summary__label">Top Score</div>
          <div class="leaderboard-summary__value">{{ leaderboard[0]?.points ?? 0 }}</div>
        </div>
        <div class="leaderboard-summary__badge">Environmental Points</div>
      </div>

      <div class="leaderboard-list">
        <div
          v-for="(entry, idx) in leaderboard"
          :key="idx"
          class="leaderboard-row"
          :class="{ 'leaderboard-row--mine': entry.building === myBuilding }"
        >
          <div class="leaderboard-row__left">
            <div class="leaderboard-row__rank">{{ idx + 1 }}</div>
            <div>
              <div class="leaderboard-row__name">
                {{ entry.building }}
                <span v-if="entry.building === myBuilding" class="leaderboard-row__mine">Your Building</span>
              </div>
              <div class="leaderboard-row__subtitle">Environmental performance</div>
            </div>
          </div>
          <div class="leaderboard-row__points">{{ entry.points }}</div>
        </div>
      </div>
    </COffcanvasBody>
  </COffcanvas>
</template>

<script setup>
import { COffcanvas, COffcanvasHeader, COffcanvasTitle, COffcanvasBody, CButton } from '@coreui/vue'

defineProps({
  visible: Boolean,
  myBuilding: {
    type: String,
    default: '',
  },
})
const emit = defineEmits(['close'])

// Example leaderboard data
const leaderboard = [
  { building: 'Building A', points: 155 },
  { building: 'Building B', points: 120 },
  { building: 'Building C', points: 98 },
  { building: 'Building D', points: 75 },
]
</script>

<style scoped>
.leaderboard-panel :deep(.offcanvas) {
  border-left: 1px solid rgba(172, 199, 255, 0.35);
  background:
    linear-gradient(180deg, rgba(249, 251, 255, 0.98), rgba(240, 246, 255, 0.96));
  box-shadow: -18px 0 40px rgba(90, 117, 156, 0.12);
}

.leaderboard-panel__header {
  border-bottom: 1px solid rgba(172, 199, 255, 0.26);
  padding: 1.35rem 1.35rem 1rem;
}

.leaderboard-panel__eyebrow {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #6b87b3;
  margin-bottom: 0.2rem;
}

.leaderboard-panel__body {
  padding: 1.15rem 1.1rem 1.35rem;
}

.leaderboard-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.05rem;
  margin-bottom: 1rem;
  border: 1px solid rgba(172, 199, 255, 0.28);
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(255, 244, 204, 0.92), rgba(255, 255, 255, 0.95));
  box-shadow: 0 14px 30px rgba(109, 129, 163, 0.08);
}

.leaderboard-summary__label {
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #8a6a10;
}

.leaderboard-summary__value {
  font-size: 1.9rem;
  font-weight: 800;
  color: #22324d;
  line-height: 1.05;
}

.leaderboard-summary__badge {
  display: inline-flex;
  align-items: center;
  padding: 0.45rem 0.8rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  color: #7a5d0f;
  font-size: 0.82rem;
  font-weight: 700;
  white-space: nowrap;
}

.leaderboard-list {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.leaderboard-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.9rem;
  padding: 0.95rem 1rem;
  border: 1px solid rgba(172, 199, 255, 0.24);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 10px 24px rgba(104, 130, 170, 0.07);
}

.leaderboard-row--mine {
  border-color: rgba(39, 122, 226, 0.35);
  background: linear-gradient(135deg, rgba(237, 244, 255, 0.95), rgba(255, 255, 255, 0.9));
}

.leaderboard-row__left {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  min-width: 0;
}

.leaderboard-row__rank {
  width: 2.25rem;
  height: 2.25rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(39, 122, 226, 0.14), rgba(39, 122, 226, 0.24));
  color: #1f4d8f;
  font-weight: 800;
  flex: 0 0 auto;
}

.leaderboard-row__name {
  font-size: 1rem;
  font-weight: 700;
  color: #22324d;
}

.leaderboard-row__mine {
  display: inline-block;
  margin-left: 0.45rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: rgba(39, 122, 226, 0.12);
  color: #277ae2;
  font-size: 0.72rem;
  font-weight: 700;
  vertical-align: middle;
}

.leaderboard-row__subtitle {
  font-size: 0.8rem;
  color: #6a7c98;
  margin-top: 0.1rem;
}

.leaderboard-row__points {
  font-size: 1.25rem;
  font-weight: 800;
  color: #1f6f3d;
  white-space: nowrap;
}
</style>
