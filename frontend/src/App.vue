<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import AppSidebar from './components/AppSidebar.vue'
import AppToastContainer from './components/AppToastContainer.vue'

const auth = useAuthStore()
const router = useRouter()
const sidebarOpen = ref(false)
const authReady = ref(false)

auth.loadMe().then(() => { authReady.value = true }).catch(() => { authReady.value = true })

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') sidebarOpen.value = false
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
watch(() => router.currentRoute.value.fullPath, () => { sidebarOpen.value = false })
</script>

<template>
  <div v-if="auth.token && !authReady" class="flex min-h-screen items-center justify-center bg-slate-50">
    <svg class="h-8 w-8 animate-spin text-brand-500" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  </div>

  <div v-else class="min-h-screen bg-slate-50 text-slate-900">
    <!-- Mobile header -->
    <div v-if="auth.token" class="fixed left-0 right-0 top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 md:hidden">
      <button class="grid h-8 w-8 place-items-center rounded-btn text-slate-600 hover:bg-slate-100" @click="sidebarOpen = !sidebarOpen">
        <svg v-if="!sidebarOpen" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
        <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
      <span class="font-bold">Quiz Pass</span>
    </div>

    <!-- Mobile overlay -->
    <div v-if="sidebarOpen" class="fixed inset-0 z-20 bg-slate-900/30 md:hidden" @click="sidebarOpen = false" />

    <!-- Sidebar (hidden on mobile unless toggled) -->
    <div :class="['fixed inset-y-0 left-0 z-20 transition-transform md:translate-x-0', sidebarOpen ? 'translate-x-0' : '-translate-x-full', 'pt-14 md:pt-0']">
      <AppSidebar v-if="auth.token" @close="sidebarOpen = false" />
    </div>

    <main :class="auth.token ? 'md:ml-56 px-4 py-7 pt-20 md:px-7 md:pt-7' : 'p-7'">
      <RouterView />
    </main>

    <AppToastContainer />
  </div>
</template>
