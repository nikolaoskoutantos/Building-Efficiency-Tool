import { defineComponent, h, onMounted, ref, resolveComponent } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { CBadge, CSidebarNav, CNavItem, CNavGroup, CNavTitle } from '@coreui/vue'
import nav from '@/_nav.js'

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

    onMounted(() => {
      firstRender.value = false
    })

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
      return h(
        CNavGroup,
        {
          as: 'div',
          compact: true,
          ...(firstRender.value && {
            visible: item.items.some((child) => isActiveItem(route, child)),
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
          default: () => item.items.map((child) => renderItem(child)),
        },
      )
    }

    const renderItem = (item) => {
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
