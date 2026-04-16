import { defineComponent, h, onMounted, ref, resolveComponent } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'

import { CBadge, CSidebarNav, CNavItem, CNavGroup, CNavTitle } from '@coreui/vue'
import nav from '@/_nav.js'
import { useAuthStore } from '@/stores/auth'
import { normalizeRole } from '@/utils/apiErrors'

import simplebar from 'simplebar-vue'
import 'simplebar-vue/dist/simplebar.min.css'

const normalizePath = (path) =>
  decodeURI(path)
    .replace(/#.*$/, '')
    .replace(/(index)?\.(html)$/, '')

const isActiveLink = (route, link) => {
  if (link === undefined) {
    return false
  }

  if (route.hash === link) {
    return true
  }

  const currentPath = normalizePath(route.path)
  const targetPath = normalizePath(link)

  return currentPath === targetPath
}

const isActiveItem = (route, item) => {
  if (isActiveLink(route, item.to)) {
    return true
  }

  if (item.items) {
    return item.items.some((child) => isActiveItem(route, child))
  }

  return false
}

const AppSidebarNav = defineComponent({
  name: 'AppSidebarNav',
  components: {
    CNavItem,
    CNavGroup,
    CNavTitle,
  },
  setup() {
    const route = useRoute()
    const firstRender = ref(true)
    const authStore = useAuthStore()
    const { userProfile } = storeToRefs(authStore)

    onMounted(() => {
      firstRender.value = false
    })

    const canAccessItem = (item) => {
      if (!Array.isArray(item.roles) || item.roles.length === 0) {
        return true
      }

      const currentRole = normalizeRole(userProfile.value?.role)
      return item.roles.includes(currentRole)
    }

    const renderIcon = (icon) => {
      return icon
        ? h(resolveComponent('CIcon'), {
            customClassName: 'nav-icon',
            name: icon,
          })
        : h('span', { class: 'nav-icon' }, h('span', { class: 'nav-icon-bullet' }))
    }

    const renderBadge = (badge) => {
      return badge
        ? h(
            CBadge,
            {
              class: 'ms-auto',
              color: badge.color,
              size: 'sm',
            },
            {
              default: () => badge.text,
            },
          )
        : null
    }

    const renderExternalLink = (item) => {
      return h(
        resolveComponent(item.component),
        {
          href: item.href,
          target: '_blank',
          rel: 'noopener noreferrer',
        },
        {
          default: () => [
            renderIcon(item.icon),
            item.name,
            item.external && h(resolveComponent('CIcon'), {
              class: 'ms-2',
              name: 'cil-external-link',
              size: 'sm'
            }),
            renderBadge(item.badge),
          ],
        },
      )
    }

    const renderRouterLink = (item) => {
      return h(
        RouterLink,
        {
          to: item.to,
          custom: true,
        },
        {
          default: (props) =>
            h(
              resolveComponent(item.component),
              {
                active: props.isActive,
                as: 'div',
                href: props.href,
                onClick: () => props.navigate(),
              },
              {
                default: () => [
                  renderIcon(item.icon),
                  item.name,
                  renderBadge(item.badge),
                ],
              },
            ),
        },
      )
    }

    const renderNavGroup = (item) => {
      const visibleChildren = item.items.filter((child) => canAccessItem(child))
      if (visibleChildren.length === 0) {
        return null
      }

      return h(
        CNavGroup,
        {
          as: 'div',
          compact: true,
          ...(firstRender.value && {
            visible: visibleChildren.some((child) => isActiveItem(route, child)),
          }),
        },
        {
          togglerContent: () => [
            h(resolveComponent('CIcon'), {
              customClassName: 'nav-icon',
              name: item.icon,
            }),
            item.name,
          ],
          default: () => visibleChildren.map((child) => renderItem(child)),
        },
      )
    }

    const renderItem = (item) => {
      if (!canAccessItem(item)) {
        return null
      }

      if (item.items) {
        return renderNavGroup(item)
      }

      if (item.href) {
        return renderExternalLink(item)
      }

      if (item.to) {
        return renderRouterLink(item)
      }

      return h(
        resolveComponent(item.component),
        {
          as: 'div',
        },
        {
          default: () => item.name,
        },
      )
    }

    return () =>
      h(
        CSidebarNav,
        {
          as: simplebar,
        },
        {
          default: () => nav.map((item) => renderItem(item)),
        },
      )
  },
})

export { AppSidebarNav }
