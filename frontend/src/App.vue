<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import AppSidebar from './components/AppSidebar.vue'

const auth = useAuthStore()
const router = useRouter()
const sidebarOpen = ref(false)
const authReady = ref(false)

auth.loadMe().then(() => { authReady.value = true }).catch(() => { authReady.value = true })

watch(() => router.currentRoute.value.fullPath, () => { sidebarOpen.value = false })
</script>

<template>
  <div v-if="auth.token && !authReady" class="flex min-h-screen items-center justify-center bg-slate-50">
    <span class="text-slate-400">加载中…</span>
  </div>

  <div v-else class="min-h-screen bg-slate-50">
    <!-- Mobile header -->
    <div v-if="auth.token" class="fixed inset-x-0 top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white px-3 py-2 md:hidden">
      <el-button text class="!p-1 text-slate-600" @click="sidebarOpen = !sidebarOpen">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path v-if="!sidebarOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </el-button>
      <span class="font-semibold text-slate-900">Quiz Pass</span>
    </div>

    <!-- Mobile overlay -->
    <div v-if="sidebarOpen" class="fixed inset-0 z-20 bg-slate-900/20 md:hidden" @click="sidebarOpen = false" />

    <!-- Sidebar -->
    <div :class="['fixed inset-y-0 left-0 z-20 w-56 transition-transform md:translate-x-0', sidebarOpen ? 'translate-x-0' : '-translate-x-full', 'pt-14 md:pt-0']">
      <AppSidebar v-if="auth.token" @close="sidebarOpen = false" />
    </div>

    <main :class="auth.token ? 'md:ml-56 min-h-screen px-4 py-4 pt-16 md:px-5 md:pt-5' : 'p-4'">
      <RouterView />
    </main>
  </div>
</template>
