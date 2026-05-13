<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  page: number
  totalPages: number
  total: number
}>(), {
  page: 1,
  totalPages: 1,
  total: 0,
})

const emit = defineEmits<{
  'update:page': [page: number]
}>()

const pages = computed(() => {
  const result: (number | '...')[] = []
  const p = props.page
  const t = props.totalPages
  if (t <= 7) {
    for (let i = 1; i <= t; i++) result.push(i)
    return result
  }
  result.push(1)
  if (p > 3) result.push('...')
  for (let i = Math.max(2, p - 1); i <= Math.min(t - 1, p + 1); i++) {
    result.push(i)
  }
  if (p < t - 2) result.push('...')
  result.push(t)
  return result
})

function go(page: number) {
  if (page >= 1 && page <= props.totalPages) emit('update:page', page)
}
</script>

<template>
  <div v-if="totalPages > 1" class="flex flex-wrap items-center justify-end gap-2 text-sm text-slate-600">
    <span class="mr-2 text-slate-500">共 {{ total }} 条</span>
    <button
      class="rounded-btn px-3 py-1.5 hover:bg-slate-100 disabled:opacity-40"
      :disabled="page <= 1"
      @click="go(page - 1)"
    >上一页</button>
    <button
      v-for="p in pages"
      :key="p"
      :class="[
        'grid h-8 w-8 place-items-center rounded-btn',
        p === page ? 'bg-slate-900 text-white' : 'hover:bg-slate-100',
        p === '...' ? 'cursor-default' : '',
      ]"
      :disabled="p === '...'"
      @click="typeof p === 'number' && go(p)"
    >{{ p }}</button>
    <button
      class="rounded-btn px-3 py-1.5 hover:bg-slate-100 disabled:opacity-40"
      :disabled="page >= totalPages"
      @click="go(page + 1)"
    >下一页</button>
  </div>
</template>
