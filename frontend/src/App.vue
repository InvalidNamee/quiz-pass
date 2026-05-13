<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()
const menuOpen = ref(false)

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 md:flex">
    <aside v-if="auth.token" class="flex w-full flex-col gap-1 border-b border-slate-200 bg-white p-5 md:min-h-screen md:w-56 md:border-b-0 md:border-r">
      <div class="mb-5 text-xl font-bold">Quiz Pass</div>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/dashboard">概览</RouterLink>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/banks">我的题库</RouterLink>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/banks/public">公开题库</RouterLink>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/favorites">我的收藏</RouterLink>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/banks/generate">AI 生成</RouterLink>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/history">历史</RouterLink>
      <RouterLink class="rounded-md px-3 py-2 hover:bg-blue-50" to="/settings/ai-providers">AI 配置</RouterLink>
      <RouterLink v-if="auth.user?.role === 'admin'" class="rounded-md px-3 py-2 hover:bg-blue-50" to="/admin/users">用户管理</RouterLink>
      <div class="flex-1"></div>
      <div class="relative">
        <button class="grid w-full grid-cols-[36px_1fr] items-center gap-3 rounded-md bg-slate-100 p-2 text-left text-slate-900" @click="menuOpen = !menuOpen">
          <img v-if="auth.user?.avatar_url" class="h-9 w-9 rounded-full object-cover" :src="auth.user.avatar_url" alt="" />
          <span v-else class="grid h-9 w-9 place-items-center rounded-full bg-teal-800 font-bold text-white">{{ (auth.user?.display_name || auth.user?.username || 'U').slice(0, 1).toUpperCase() }}</span>
          <span class="grid min-w-0 gap-0.5">
            <strong class="truncate">{{ auth.user?.display_name || auth.user?.username }}</strong>
            <span class="truncate text-xs text-slate-500">{{ auth.user?.email }}</span>
          </span>
        </button>
        <div v-if="menuOpen" class="absolute bottom-14 right-0 z-10 grid w-full gap-1 rounded-lg border border-slate-200 bg-white p-2 shadow-xl">
          <RouterLink class="rounded-md px-3 py-2 hover:bg-slate-100" to="/profile" @click="menuOpen = false">编辑资料</RouterLink>
          <RouterLink class="rounded-md px-3 py-2 hover:bg-slate-100" to="/profile#password" @click="menuOpen = false">修改密码</RouterLink>
          <button class="rounded-md px-3 py-2 text-left hover:bg-slate-100" @click="logout">退出登录</button>
        </div>
      </div>
    </aside>
    <main class="w-full p-7">
      <RouterView />
    </main>
  </div>
</template>
