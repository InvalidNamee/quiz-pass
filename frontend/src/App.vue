<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()
const menuOpen = ref(false)
const userMenu = ref<HTMLElement | null>(null)

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
})
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 md:flex">
    <aside v-if="auth.token" class="fixed inset-y-0 left-0 z-20 flex w-56 flex-col gap-1 border-r border-slate-200 bg-white p-5">
      <div class="mb-5 text-xl font-bold">Quiz Pass</div>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/dashboard">概览</RouterLink>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/banks">我的题库</RouterLink>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/banks/public">公开题库</RouterLink>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/favorites">我的收藏</RouterLink>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/banks/generate">AI 生成</RouterLink>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/history">历史</RouterLink>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/settings/ai-providers">AI 配置</RouterLink>
      <RouterLink v-if="auth.user?.role === 'admin'" class="rounded-md px-3 py-2 hover:bg-blue-50" to="/admin/users">用户管理</RouterLink>
      <div ref="userMenu" class="relative mt-auto">
        <button class="grid w-full grid-cols-[36px_1fr] items-center gap-3 rounded-md bg-slate-100 p-2 text-left text-slate-900 hover:bg-slate-200" @click="menuOpen = !menuOpen">
          <img v-if="auth.user?.avatar_url" class="h-9 w-9 rounded-full object-cover" :src="auth.user.avatar_url" alt="" />
          <span v-else class="grid h-9 w-9 place-items-center rounded-full bg-teal-800 font-bold text-white">{{ (auth.user?.display_name || auth.user?.username || 'U').slice(0, 1).toUpperCase() }}</span>
          <span class="grid min-w-0 gap-0.5">
            <strong class="truncate">{{ auth.user?.display_name || auth.user?.username }}</strong>
            <span class="truncate text-xs text-slate-500">{{ auth.user?.email }}</span>
          </span>
        </button>
        <div v-if="menuOpen" class="absolute bottom-14 left-0 z-10 grid w-full gap-1 rounded-lg border border-slate-200 bg-white p-2">
          <RouterLink class="rounded-md px-3 py-2 hover:bg-slate-100" to="/profile" @click="menuOpen = false">编辑资料</RouterLink>
          <RouterLink class="rounded-md px-3 py-2 hover:bg-slate-100" to="/profile#password" @click="menuOpen = false">修改密码</RouterLink>
          <button class="rounded-md px-3 py-2 text-left hover:bg-slate-100" @click="logout">退出登录</button>
        </div>
      </div>
    </aside>
    <main :class="auth.token ? 'ml-56 w-full p-7' : 'w-full p-7'">
      <RouterView />
    </main>
  </div>
</template>
