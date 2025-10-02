<template>
  <COffcanvas :visible="visible" placement="end" @hide="emit('close')">
    <COffcanvasHeader>
      <COffcanvasTitle>Leaderboard</COffcanvasTitle>
      <CButton class="btn-close" @click="emit('close')" aria-label="Close"></CButton>
    </COffcanvasHeader>
    <COffcanvasBody>
      <CListGroup>
        <table class="table table-striped">
          <thead>
            <tr>
              <th>Building</th>
              <th>Environmental Points</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(entry, idx) in leaderboard" :key="idx">
              <td>{{ entry.building }}</td>
              <td>{{ entry.points }}</td>
            </tr>
          </tbody>
        </table>
      </CListGroup>
    </COffcanvasBody>
  </COffcanvas>
</template>

<script setup>
import { COffcanvas, COffcanvasHeader, COffcanvasTitle, COffcanvasBody, CListGroup, CButton } from '@coreui/vue'
const props = defineProps({ visible: Boolean })
const emit = defineEmits(['close'])

// Example leaderboard data
const leaderboard = [
  { building: 'Building A', points: 155 },
  { building: 'Building B', points: 120 },
  { building: 'Building C', points: 98 },
  { building: 'Building D', points: 75 },
]
</script>
