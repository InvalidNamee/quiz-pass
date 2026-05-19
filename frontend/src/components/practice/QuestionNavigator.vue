<script setup lang="ts">
defineProps<{
  total: number
  currentIndex: number
  statuses: ('correct' | 'wrong' | 'answered' | 'selected' | 'none')[]
}>()

const emit = defineEmits<{ go: [index: number] }>()

function getClass(status: string, isCurrent: boolean) {
  return [
    'navigator-cell',
    `is-${status || 'none'}`,
    isCurrent ? 'is-current' : '',
  ].join(' ')
}
</script>

<template>
  <div class="sticky top-5 max-h-[calc(100vh-7rem)] border border-slate-200 bg-white p-2">
    <p class="mb-2 text-center text-xs font-medium text-slate-400">答题卡</p>
    <el-scrollbar max-height="calc(100vh - 10rem)">
      <div class="grid grid-cols-5 gap-1.5 pr-1">
        <button
          v-for="(status, index) in statuses"
          :key="index"
          type="button"
          :class="getClass(status, index === currentIndex)"
          @click="emit('go', index)"
        >
          {{ index + 1 }}
        </button>
      </div>
    </el-scrollbar>
  </div>
</template>

<style scoped>
.navigator-cell {
  --practice-ok-border: #86efac;
  --practice-ok-bg: #f0fdf4;
  --practice-ok-text: #166534;
  --practice-bad-border: #fda4af;
  --practice-bad-bg: #fff1f2;
  --practice-bad-text: #be123c;
  height: 34px;
  width: 100%;
  border: 1px solid #d8dee8;
  background: #fff;
  color: #64748b;
  font-size: 13px;
  font-weight: 650;
  transition: border-color .15s ease, background-color .15s ease, color .15s ease;
}
.navigator-cell:hover {
  border-color: #93c5fd;
  color: #1d4ed8;
}
.navigator-cell.is-selected,
.navigator-cell.is-answered {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
}
.navigator-cell.is-correct {
  border-color: var(--practice-ok-border);
  background: var(--practice-ok-bg);
  color: var(--practice-ok-text);
}
.navigator-cell.is-wrong {
  border-color: var(--practice-bad-border);
  background: var(--practice-bad-bg);
  color: var(--practice-bad-text);
}
.navigator-cell.is-current {
  border-color: #2563eb;
  box-shadow: inset 0 0 0 1px #2563eb;
  color: #1e293b;
}
</style>
