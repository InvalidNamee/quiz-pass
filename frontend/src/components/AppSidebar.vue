<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppAvatar from './AppAvatar.vue'

const auth = useAuthStore()
const router = useRouter()
const menuOpen = ref(false)

const emit = defineEmits<{ close: [] }>()

function logout() {
  menuOpen.value = false
  auth.logout()
  router.push('/login')
  emit('close')
}

function close() {
  emit('close')
}

const navItems = [
  { to: '/dashboard', label: '首页' },
  { to: '/banks', label: '我的题库' },
  { to: '/banks/public', label: '公开题库' },
  { to: '/banks/generate', label: '新建题库' },
  { to: '/history', label: '刷题记录' },
  { to: '/banks/generation-jobs', label: '生成队列' },
  { to: '/settings/ai-providers', label: 'AI 配置' },
]
</script>

<template>
  <aside class="fixed inset-y-0 left-0 z-20 flex w-56 flex-col border-r border-slate-200 bg-white">
    <div class="hidden px-5 pb-3 pt-5 text-base font-bold tracking-tight md:block">Quiz Pass</div>
    <nav class="flex-1 space-y-0.5 overflow-y-auto px-3 pt-3 md:pt-0">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="sidebar-link block rounded-btn px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
        @click="close"
      >{{ item.label }}</RouterLink>
      <RouterLink
        v-if="auth.user?.role === 'admin'"
        to="/admin/users"
        class="sidebar-link block rounded-btn px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
        @click="close"
      >用户管理</RouterLink>
    </nav>

    <div class="relative border-t border-slate-200 px-3 py-3">
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
        <div class="mb-2 grid grid-cols-[44px_1fr] items-center gap-2 rounded-lg bg-slate-50 p-3">
          <AppAvatar
            :src="auth.user?.avatar_url"
            :username="auth.user?.display_name || auth.user?.username"
            size="lg"
          />
          <span class="min-w-0">
            <strong class="block truncate">{{ auth.user?.display_name || auth.user?.username }}</strong>
            <span class="block truncate text-xs text-slate-500">@{{ auth.user?.username }} · {{ auth.user?.email }}</span>
          </span>
        </div>
        <RouterLink class="rounded-btn px-3 py-2 hover:bg-slate-100" :to="`/users/${auth.user?.id}`" @click="menuOpen = false">个人主页</RouterLink>
        <RouterLink class="rounded-btn px-3 py-2 hover:bg-slate-100" to="/profile" @click="menuOpen = false">账号设置</RouterLink>
        <button class="rounded-btn px-3 py-2 text-left hover:bg-slate-100" @click="logout">退出登录</button>
      </div>
    </div>
  </aside>
</template>
