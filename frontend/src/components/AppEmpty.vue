<script setup lang="ts">
defineProps<{
  title?: string
  description?: string
  actionLabel?: string
  actionTo?: string
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
    <svg class="h-10 w-10 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
    </svg>
    <p v-if="title" class="font-semibold text-slate-600">{{ title }}</p>
    <p v-if="description" class="text-sm text-slate-500">{{ description }}</p>
    <RouterLink v-if="actionLabel && actionTo" :to="actionTo" class="mt-2 rounded-btn bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
      {{ actionLabel }}
    </RouterLink>
  </div>
</template>
