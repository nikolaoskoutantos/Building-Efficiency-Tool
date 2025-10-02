<template>
  <CCard class="mb-4 hvac-schedule-table">
    <CCardBody>
      <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap">
        <h5 class="mb-2 mb-sm-0">HVAC Schedule</h5>
        <div style="display: flex; gap: 0.5rem;">
          <CButton color="primary" size="sm" @click="addRow">Add Period</CButton>
          <CButton color="success" size="sm" @click="emitOptimize">Optimize</CButton>
        </div>
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
                <el-time-picker
                  v-model="row.start"
                  :picker-options="{ step: '00:30' }"
                  format="HH:mm"
                  value-format="HH:mm"
                  placeholder="Start"
                  class="el-time-picker-sm"
                  :clearable="false"
                  style="width: 100%"
                  :disabled="idx === 0"
                />
              </td>
              <td>
                <el-time-picker
                  v-model="row.end"
                  :picker-options="{ step: '00:30' }"
                  format="HH:mm"
                  value-format="HH:mm"
                  placeholder="End"
                  @change="validateRow(idx)"
                  class="el-time-picker-sm"
                  :clearable="false"
                  style="width: 100%"
                />
              </td>
              <td>
                <CFormSwitch size="lg" v-model="row.enabled" :color="row.enabled ? 'success' : 'danger'" />
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

import { defineEmits } from 'vue'
const emit = defineEmits(['optimize'])

function emitOptimize() {
  emit('optimize');
}

// Element Plus time picker
import { ElTimePicker } from 'element-plus'
import 'element-plus/dist/index.css'
import { ref, watch } from 'vue'
import { CCard, CCardBody, CButton, CFormSwitch } from '@coreui/vue'
import { useControlStore } from '@/stores/control.js'

const controlStore = useControlStore()

const schedule = ref([])
const error = ref('')


function addRow() {
  // Helper to pad numbers
  const pad = n => n.toString().padStart(2, '0');
  let start, end;
  const now = new Date();
  now.setMilliseconds(0);
  now.setSeconds(0);
  let min = now.getMinutes();
  // Always round up to the next 5-min interval
  if (min % 5 !== 0) {
    now.setMinutes(min + (5 - (min % 5)));
  } else {
    now.setMinutes(min);
  }
  let startDate;
  if (schedule.value.length > 0) {
    // Start from the end of the last period, but if it's in the past, use next 5-min after now
    const lastEnd = schedule.value[schedule.value.length - 1].end;
    const [h, m] = lastEnd.split(':').map(Number);
    const lastEndDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, 0, 0);
    if (lastEndDate > now) {
      // If lastEndDate is not on a 5-min mark, round up
      let lm = lastEndDate.getMinutes();
      if (lm % 5 !== 0) {
        lastEndDate.setMinutes(lm + (5 - (lm % 5)));
      }
      startDate = lastEndDate;
    } else {
      // Use next 5-min after now
      startDate = new Date(now);
    }
  } else {
    startDate = new Date(now);
  }
  start = `${pad(startDate.getHours())}:${pad(startDate.getMinutes())}`;
  // End time is 1 hour later
  const endDate = new Date(startDate.getTime() + 60 * 60000);
  end = `${pad(endDate.getHours())}:${pad(endDate.getMinutes())}`;
  schedule.value.push({
    id: Date.now() + Math.random(),
    start,
    end,
    enabled: true
  });
}

function removeRow(idx) {
  schedule.value.splice(idx, 1)
  error.value = ''
}

function validateRow(idx) {
  error.value = ''
  const current = schedule.value[idx]
  if (current.start >= current.end) {
    error.value = 'Start time must be before end time.'
    return
  }
  // Check for overlap with other enabled rows
  for (let i = 0; i < schedule.value.length; i++) {
    if (i === idx) continue
    const row = schedule.value[i]
    if (!row.enabled || !current.enabled) continue
    if (
      (current.start < row.end && current.end > row.start)
    ) {
      error.value = 'Time ranges cannot overlap.'
      return
    }
  }
}

watch(schedule, (val) => {
  // Save to store
  controlStore.setSchedule(val.map(r => ({ ...r })))
}, { deep: true })

// On mount, force the first period to start from now (rounded up to next 5-min)
const pad = n => n.toString().padStart(2, '0');
const now = new Date();
now.setMilliseconds(0);
now.setSeconds(0);
let min = now.getMinutes();
if (min % 5 !== 0) {
  now.setMinutes(min + (5 - (min % 5)));
} else {
  now.setMinutes(min);
}
const start = `${pad(now.getHours())}:${pad(now.getMinutes())}`;
const endDate = new Date(now.getTime() + 60 * 60000);
const end = `${pad(endDate.getHours())}:${pad(endDate.getMinutes())}`;
schedule.value = [{
  id: Date.now() + Math.random(),
  start,
  end,
  enabled: true
}];
</script>

<style scoped>
.hvac-schedule-table .table {
  min-width: 350px;
}
@media (max-width: 600px) {
  .hvac-schedule-table .table {
    font-size: 0.95em;
  }
}

[data-coreui-theme=dark] {
  --el-input-bg-color: #222 !important;
  --el-input-text-color: #fff !important;
}
</style>
