<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import AppAvatar from './components/AppAvatar.vue'
import AppToastContainer from './components/AppToastContainer.vue'

const auth = useAuthStore()
const router = useRouter()
const menuOpen = ref(false)
const sidebarOpen = ref(false)
const userMenu = ref<HTMLElement | null>(null)
const authReady = ref(false)

auth.loadMe().then(() => { authReady.value = true }).catch(() => { authReady.value = true })

function logout() {
  menuOpen.value = false
  auth.logout()
  router.push('/login')
}

function onDocumentClick(event: MouseEvent) {
  if (!userMenu.value?.contains(event.target as Node)) menuOpen.value = false
}

onMounted(() => document.addEventListener('click', onDocumentClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocumentClick))
watch(() => router.currentRoute.value.fullPath, () => {
  menuOpen.value = false
  sidebarOpen.value = false
})

const navItems = [
  { to: '/dashboard', label: '首页' },
  { to: '/banks/public', label: '公开题库' },
  { to: '/banks', label: '我的题库' },
  { to: '/favorites', label: '我的收藏' },
  { to: '/banks/generate', label: '新建题库' },
  { to: '/banks/generation-jobs', label: '生成队列' },
  { to: '/history', label: '刷题记录' },
  { to: '/settings/ai-providers', label: 'AI 配置' },
]
</script>

<template>
  <div v-if="auth.token && !authReady" class="flex min-h-screen items-center justify-center bg-slate-50">
    <svg class="h-8 w-8 animate-spin text-brand-500" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  </div>

  <div v-else class="min-h-screen bg-slate-50 text-slate-900 md:flex">
    <!-- Mobile hamburger -->
    <div v-if="auth.token" class="fixed left-0 right-0 top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 md:hidden">
      <button class="grid h-8 w-8 place-items-center rounded-btn text-slate-600 hover:bg-slate-100" @click="sidebarOpen = !sidebarOpen">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path v-if="!sidebarOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
      <span class="font-bold">Quiz Pass</span>
    </div>

    <!-- Mobile overlay -->
    <div v-if="sidebarOpen" class="fixed inset-0 z-20 bg-slate-900/30 md:hidden" @click="sidebarOpen = false" />

    <!-- Sidebar -->
    <aside
      v-if="auth.token"
      :class="[
        'fixed inset-y-0 left-0 z-20 flex w-56 flex-col border-r border-slate-200 bg-white transition-transform md:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        'pt-14 md:pt-0',
      ]"
    >
      <div class="hidden px-5 pb-3 pt-5 text-xl font-bold tracking-tight md:block">Quiz Pass</div>
      <nav class="flex-1 space-y-0.5 overflow-y-auto px-3 pt-3 md:pt-0">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="sidebar-link block rounded-btn px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
        >{{ item.label }}</RouterLink>
        <RouterLink
          v-if="auth.user?.role === 'admin'"
          to="/admin/users"
          class="sidebar-link block rounded-btn px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
        >用户管理</RouterLink>
      </nav>

      <div ref="userMenu" class="relative border-t border-slate-200 px-3 py-3">
        <button
          class="flex w-full items-center gap-3 rounded-btn p-2 text-left hover:bg-slate-100"
          @click="menuOpen = !menuOpen"
        >
          <AppAvatar
            :src="auth.user?.avatar_url"
            :username="auth.user?.display_name || auth.user?.username"
            size="sm"
          />
          <span class="flex-1 truncate text-sm font-medium">{{ auth.user?.display_name || auth.user?.username }}</span>
        </button>

        <div v-if="menuOpen" class="absolute bottom-full left-3 z-10 mb-2 grid w-72 gap-1 rounded-xl border border-slate-200 bg-white p-3 shadow-modal">
          <div class="mb-2 grid grid-cols-[44px_1fr] items-center gap-3 rounded-lg bg-slate-50 p-3">
            <AppAvatar
              :src="auth.user?.avatar_url"
              :username="auth.user?.display_name || auth.user?.username"
              size="lg"
            />
            <span class="min-w-0">
              <strong class="block truncate">{{ auth.user?.display_name || auth.user?.username }}</strong>
              <span class="block truncate text-xs text-slate-500">@{{ auth.user?.username }} · {{ auth.user?.email }}</span>
              <span class="block text-xs text-slate-500">ID {{ auth.user?.id }} · {{ auth.user?.role }}</span>
            </span>
          </div>
          <RouterLink class="rounded-btn px-3 py-2 hover:bg-slate-100" :to="`/users/${auth.user?.id}`" @click="menuOpen = false">个人主页</RouterLink>
          <RouterLink class="rounded-btn px-3 py-2 hover:bg-slate-100" to="/profile" @click="menuOpen = false">账号设置</RouterLink>
          <button class="rounded-btn px-3 py-2 text-left hover:bg-slate-100" @click="logout">退出登录</button>
        </div>
      </div>
    </aside>

    <main :class="auth.token ? 'md:ml-56 w-full px-4 py-7 pt-20 md:px-7 md:pt-7' : 'w-full p-7'">
      <RouterView />
    </main>

    <AppToastContainer />
  </div>
</template>
