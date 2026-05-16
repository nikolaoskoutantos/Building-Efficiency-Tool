<template>
  <template v-if="visible">
    <div class="ctx-overlay" @click="$emit('close')" @contextmenu.prevent="$emit('close')" />
    <div class="ctx-menu" :style="{ top: y + 'px', left: x + 'px' }" @click.stop @contextmenu.prevent>
      <div v-if="title" class="ctx-menu__title">{{ title }}</div>
      <template v-for="(item, i) in items" :key="i">
        <div v-if="item.divider" class="ctx-menu__divider" />
        <button
          v-else
          class="ctx-menu__item"
          :class="{ 'ctx-menu__item--danger': item.danger }"
          @click="$emit('select', item.action)"
        >
          <span class="ctx-menu__icon">{{ item.icon }}</span>
          {{ item.label }}
        </button>
      </template>
    </div>
  </template>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  x:       { type: Number,  default: 0 },
  y:       { type: Number,  default: 0 },
  title:   { type: String,  default: '' },
  items:   { type: Array,   default: () => [] },
})
defineEmits(['select', 'close'])
</script>

<style scoped>
.ctx-overlay {
  position: fixed;
  inset: 0;
  z-index: 9998;
}

.ctx-menu {
  position: fixed;
  z-index: 9999;
  min-width: 190px;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 4px;
  box-shadow: 0 10px 36px rgba(0, 0, 0, 0.5), 0 2px 8px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(8px);
}

.ctx-menu__title {
  padding: 6px 10px 5px;
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  margin-bottom: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 190px;
}

.ctx-menu__divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.07);
  margin: 3px 6px;
}

.ctx-menu__item {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 7px 10px;
  background: none;
  border: none;
  border-radius: 7px;
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  transition: background 0.1s;
}

.ctx-menu__item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.ctx-menu__item--danger { color: #f87171; }
.ctx-menu__item--danger:hover { background: rgba(248, 113, 113, 0.12); }

.ctx-menu__icon {
  font-size: 14px;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
}
</style>
