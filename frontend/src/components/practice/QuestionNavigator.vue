<script setup lang="ts">
defineProps<{
  total: number
  currentIndex: number
  statuses: ('correct' | 'wrong' | 'answered' | 'selected' | 'none')[]
}>()

const emit = defineEmits<{ go: [index: number] }>()

function getClass(status: string, isCurrent: boolean) {
  const map: Record<string, string> = {
    correct: 'bg-emerald-100 text-emerald-700 border-emerald-300',
    wrong: 'bg-rose-100 text-rose-700 border-rose-300',
    answered: 'bg-slate-100 text-slate-500 border-slate-200',
    selected: 'bg-blue-100 text-blue-700 border-blue-300',
    none: 'bg-white text-slate-500 border-slate-200',
  }
  const curClass = isCurrent ? 'ring-2 ring-brand-500 ring-offset-1 font-bold text-slate-900' : ''
  return `${map[status] || map.none} ${curClass}`
}
</script>

<template>
  <div class="rounded-lg border border-slate-200 bg-white p-3">
    <p class="mb-2 text-center text-xs font-medium text-slate-400">答题卡</p>
    <div class="grid grid-cols-5 gap-1.5">
      <button
        v-for="(status, index) in statuses"
        :key="index"
        :class="['grid h-9 w-full place-items-center rounded-md border text-xs font-medium transition-colors hover:opacity-80', getClass(status, index === currentIndex)]"
        @click="emit('go', index)"
      >
        {{ index + 1 }}
      </button>
    </div>
  </div>
</template>
