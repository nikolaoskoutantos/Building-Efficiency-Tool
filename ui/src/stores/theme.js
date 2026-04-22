import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', () => {
  const stored = typeof window !== 'undefined'
    ? localStorage.getItem('coreui-free-vue-admin-template-theme')
    : null
  const theme = ref(stored || 'light')

  const toggleTheme = (_theme) => {
    theme.value = _theme
  }

  return { theme, toggleTheme }
})
