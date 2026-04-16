<template>
  <CCard class="mb-4 hvac-schedule-table">
    <CCardBody>
      <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap">
        <h5 class="mb-2 mb-sm-0">HVAC Schedule</h5>
        <div style="display: flex; gap: 0.5rem;">
          <CButton color="primary" size="sm" @click="addRow">Add Period</CButton>
          <CButton
            color="success"
            size="sm"
            :disabled="props.optimizeDisabled || props.optimizeLoading"
            @click="emitOptimize"
          >
            <CSpinner v-if="props.optimizeLoading" component="span" size="sm" class="me-2" />
            {{ props.optimizeButtonLabel }}
          </CButton>
        </div>
      </div>
      <div v-if="props.scheduleSaving" class="schedule-status-text mb-2">
        Saving schedule changes...
      </div>
      <div class="table-responsive">
        <table class="table table-sm align-middle mb-0">
          <thead>
            <tr>
              <th>Start Time</th>
              <th>End Time</th>
              <th>On/Off</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in schedule" :key="row.id">
              <td>
                <ElTimePicker
                  v-model="row.start"
                  class="w-100"
                  format="hh:mm A"
                  value-format="HH:mm"
                  :clearable="false"
                  :teleported="true"
                  placement="right-start"
                  popper-class="schedule-time-picker-popper"
                  @change="handleRowChange(idx)"
                />
              </td>
              <td>
                <ElTimePicker
                  v-model="row.end"
                  class="w-100"
                  format="hh:mm A"
                  value-format="HH:mm"
                  :clearable="false"
                  :teleported="true"
                  placement="right-start"
                  popper-class="schedule-time-picker-popper"
                  @change="handleRowChange(idx)"
                />
              </td>
              <td>
                <CFormSwitch
                  size="lg"
                  :model-value="row.enabled"
                  :color="row.enabled ? 'success' : 'danger'"
                  @update:model-value="(value) => handleEnabledChange(idx, value)"
                />
              </td>
              <td>
                <CButton color="danger" size="sm" @click="removeRow(idx)"><span aria-hidden="true">&times;</span></CButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="error" class="alert alert-danger mt-2">{{ error }}</div>
    </CCardBody>
  </CCard>
</template>

<script setup>

const emit = defineEmits(['optimize', 'schedule-change'])
const props = defineProps({
  optimizeLoading: {
    type: Boolean,
    default: false,
  },
  optimizeDisabled: {
    type: Boolean,
    default: false,
  },
  optimizeButtonLabel: {
    type: String,
    default: 'Optimize',
  },
  scheduleSaving: {
    type: Boolean,
    default: false,
  },
})

function emitOptimize() {
  if (props.optimizeDisabled || props.optimizeLoading) {
    return
  }
  emit('optimize');
}

import { ref, watch } from 'vue'
import { CCard, CCardBody, CButton, CFormSwitch, CSpinner } from '@coreui/vue'
import { ElTimePicker } from 'element-plus'
import 'element-plus/es/components/time-picker/style/css'
import { useControlStore } from '@/stores/control.js'

const controlStore = useControlStore()

  const schedule = ref([])
  const error = ref('')
  const syncingFromStore = ref(false)
  const suppressNextStoreHydration = ref(false)

function isValidTimeLabel(value) {
  return typeof value === 'string' && /^\d{2}:\d{2}$/.test(value)
}

function timeLabelToMinutes(value) {
  const [hours, minutes] = value.split(':').map(Number)
  return hours * 60 + minutes
}

function splitIntoDaySegments(row) {
  const startMinutes = timeLabelToMinutes(row.start)
  const endMinutes = timeLabelToMinutes(row.end)

  if (startMinutes === endMinutes) {
    return []
  }

  if (startMinutes < endMinutes) {
    return [[startMinutes, endMinutes]]
  }

  return [
    [startMinutes, 1440],
    [0, endMinutes],
  ]
}

function rowsOverlap(a, b) {
  const aSegments = splitIntoDaySegments(a)
  const bSegments = splitIntoDaySegments(b)

  for (const [aStart, aEnd] of aSegments) {
    for (const [bStart, bEnd] of bSegments) {
      if (aStart < bEnd && aEnd > bStart) {
        return true
      }
    }
  }

  return false
}

function normalizeScheduleRows(rows) {
  if (!Array.isArray(rows)) {
    return []
  }
  return rows
    .filter(row => isValidTimeLabel(row?.start) && isValidTimeLabel(row?.end))
    .map((row, index) => ({
      id: row.id ?? `schedule-row-${index}`,
      start: row.start,
      end: row.end,
      enabled: row.enabled !== false,
      setpoint: row?.enabled === false ? null : (row?.setpoint ?? null),
    }))
}

function addMinutesToTimeLabel(value, deltaMinutes) {
  const total = timeLabelToMinutes(value) + deltaMinutes
  const normalized = ((total % 1440) + 1440) % 1440
  const hours = Math.floor(normalized / 60)
  const minutes = normalized % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

function addRow() {
  // Helper to pad numbers
  const pad = n => n.toString().padStart(2, '0');
  let start, end;
  if (schedule.value.length > 0) {
    start = schedule.value[schedule.value.length - 1].end
    end = addMinutesToTimeLabel(start, 60)
  } else {
    const now = new Date();
    now.setMilliseconds(0);
    now.setSeconds(0);
    let min = now.getMinutes();
    if (min % 5 !== 0) {
      now.setMinutes(min + (5 - (min % 5)));
    } else {
      now.setMinutes(min);
    }
    start = `${pad(now.getHours())}:${pad(now.getMinutes())}`;
    end = addMinutesToTimeLabel(start, 60)
  }
  schedule.value.push({
    id: Date.now() + Math.random(),
    start,
    end,
    enabled: controlStore.preferences.switchValue !== false,
    setpoint: controlStore.preferences.slider1 ?? null,
  });
  syncScheduleToStore(true)
}

function removeRow(idx) {
  schedule.value.splice(idx, 1)
  error.value = ''
  syncScheduleToStore(true)
}

function validateSchedule() {
  error.value = ''
  for (let i = 0; i < schedule.value.length; i++) {
    const current = schedule.value[i]
    if (!isValidTimeLabel(current?.start) || !isValidTimeLabel(current?.end)) {
      error.value = 'Please enter valid start and end times.'
      return false
    }
    if (current.start === current.end) {
      error.value = 'Start time and end time cannot be the same.'
      return false
    }
    for (let j = 0; j < schedule.value.length; j++) {
      if (i === j) continue
      const row = schedule.value[j]
      if (!row.enabled || !current.enabled) continue
      if (rowsOverlap(current, row)) {
        error.value = 'Time ranges cannot overlap.'
        return false
      }
    }
  }
  return true
}

  function syncScheduleToStore(emitChange = false) {
    if (syncingFromStore.value) {
      return
    }
    const nextSchedule = schedule.value.map(r => ({ ...r }))
    suppressNextStoreHydration.value = true
    controlStore.setSchedule(nextSchedule)
    if (emitChange) {
      emit('schedule-change', nextSchedule)
    }
  }

function handleRowChange(idx) {
  if (!validateSchedule()) {
    return
  }
  syncScheduleToStore(true)
}

function handleEnabledChange(idx, value) {
  schedule.value[idx].enabled = Boolean(value)
  if (!validateSchedule()) {
    return
  }
  syncScheduleToStore(true)
}

  watch(
    () => controlStore.schedule,
    (newSchedule) => {
      if (suppressNextStoreHydration.value) {
        suppressNextStoreHydration.value = false
        return
      }
      const normalizedSchedule = normalizeScheduleRows(newSchedule)
      syncingFromStore.value = true
      schedule.value = normalizedSchedule
      syncingFromStore.value = false
    },
  { deep: true, immediate: true }
)
</script>

<style scoped>
.hvac-schedule-table {
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.hvac-schedule-table :deep(.card-body) {
  background:
    radial-gradient(circle at top right, rgba(34, 197, 94, 0.08), transparent 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 1) 100%);
  padding: 1.2rem 1.3rem;
}

.hvac-schedule-table h5 {
  color: #132238;
  font-weight: 700;
  margin: 0;
}

.schedule-status-text {
  color: #5f6b7a;
  font-size: 0.88rem;
  font-weight: 600;
}

.hvac-schedule-table .table {
  min-width: 350px;
}

.hvac-schedule-table .table th {
  color: #132238;
  font-weight: 700;
  border-bottom-color: rgba(19, 34, 56, 0.12);
}

.hvac-schedule-table .table td {
  border-bottom-color: rgba(19, 34, 56, 0.08);
}

.hvac-schedule-table .table-responsive {
  border-radius: 14px;
}
@media (max-width: 600px) {
  .hvac-schedule-table .table {
    font-size: 0.95em;
  }
}

:global([data-coreui-theme='dark']) .hvac-schedule-table {
  border-color: rgba(148, 163, 184, 0.18);
  box-shadow: 0 20px 42px rgba(2, 6, 23, 0.32);
}

:global([data-coreui-theme='dark']) .hvac-schedule-table .card-body {
  background:
    radial-gradient(circle at top right, rgba(34, 197, 94, 0.12), transparent 34%),
    linear-gradient(180deg, rgba(30, 41, 59, 0.98) 0%, rgba(15, 23, 42, 1) 100%);
}

:global([data-coreui-theme='dark']) .hvac-schedule-table h5,
:global([data-coreui-theme='dark']) .hvac-schedule-table .table th,
:global([data-coreui-theme='dark']) .hvac-schedule-table .table td {
  color: #e2e8f0;
}

:global([data-coreui-theme='dark']) .hvac-schedule-table .schedule-status-text {
  color: #94a3b8;
}

:global([data-coreui-theme='dark']) .hvac-schedule-table .table th {
  border-bottom-color: rgba(148, 163, 184, 0.18);
}

:global([data-coreui-theme='dark']) .hvac-schedule-table .table td {
  border-bottom-color: rgba(148, 163, 184, 0.1);
}

:global([data-coreui-theme='dark']) .hvac-schedule-table .table-responsive {
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.44);
}

:global([data-coreui-theme='dark']) .hvac-schedule-table {
  --el-input-bg-color: rgba(15, 23, 42, 0.78) !important;
  --el-input-border-color: rgba(148, 163, 184, 0.18) !important;
  --el-input-hover-border-color: rgba(96, 165, 250, 0.5) !important;
  --el-input-focus-border-color: rgba(96, 165, 250, 0.7) !important;
  --el-input-text-color: #e2e8f0 !important;
  --el-text-color-regular: #e2e8f0 !important;
  --el-fill-color-blank: rgba(15, 23, 42, 0.78) !important;
  --el-bg-color-overlay: rgba(15, 23, 42, 0.98) !important;
  --el-border-color-light: rgba(148, 163, 184, 0.16) !important;
  --el-mask-color: transparent !important;
}
</style>
