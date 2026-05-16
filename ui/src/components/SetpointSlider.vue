<template>
  <div class="sp-slider">
    <div class="sp-slider__value" :style="{ color: valueColor }">
      {{ Number(modelValue).toFixed(1) }}<span class="sp-slider__unit">°C</span>
    </div>
    <div class="sp-slider__track-wrap">
      <input
        type="range"
        class="sp-slider__input"
        :min="min"
        :max="max"
        :step="step"
        :value="modelValue"
        :style="trackStyle"
        @input="$emit('update:modelValue', Number($event.target.value))"
      />
    </div>
    <div class="sp-slider__labels">
      <span>{{ min }}°C</span>
      <span class="sp-slider__label-center">{{ label }}</span>
      <span>{{ max }}°C</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: 21 },
  min:        { type: Number, default: 16 },
  max:        { type: Number, default: 30 },
  step:       { type: Number, default: 0.5 },
  label:      { type: String, default: 'Setpoint' },
})
defineEmits(['update:modelValue'])

const pct = computed(() => ((props.modelValue - props.min) / (props.max - props.min)) * 100)

const valueColor = computed(() => {
  if (props.modelValue <= 18) return '#2563eb'   // cool — blue
  if (props.modelValue >= 26) return '#dc2626'   // warm  — red
  return '#059669'                                // comfort — green
})

const trackStyle = computed(() => ({
  '--pct': `${pct.value}%`,
  '--thumb-color': valueColor.value,
}))
</script>

<style scoped>
.sp-slider {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  width: 100%;
}

.sp-slider__value {
  font-size: 2rem;
  font-weight: 800;
  line-height: 1;
  transition: color 0.25s;
  letter-spacing: -0.02em;
}

.sp-slider__unit {
  font-size: 1rem;
  font-weight: 600;
  margin-left: 2px;
  opacity: 0.75;
}

.sp-slider__track-wrap {
  width: 100%;
  padding: 4px 0;
}

.sp-slider__input {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: linear-gradient(
    to right,
    v-bind('valueColor') 0%,
    v-bind('valueColor') v-bind('pct + "%"'),
    #e2e8f0 v-bind('pct + "%"'),
    #e2e8f0 100%
  );
  outline: none;
  cursor: pointer;
  transition: background 0.2s;
}

.sp-slider__input::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: v-bind('valueColor');
  border: 3px solid #ffffff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
}

.sp-slider__input::-webkit-slider-thumb:hover {
  transform: scale(1.15);
}

.sp-slider__input::-moz-range-thumb {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: v-bind('valueColor');
  border: 3px solid #ffffff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  cursor: pointer;
}

.sp-slider__labels {
  display: flex;
  justify-content: space-between;
  width: 100%;
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

.sp-slider__label-center {
  color: #64748b;
  font-weight: 600;
}
</style>
