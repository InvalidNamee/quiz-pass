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
  <div class="sticky top-5 max-h-[calc(100vh-8rem)] rounded-2xl border border-slate-100/80 bg-white/95 p-4 shadow-sm backdrop-blur-md">
    <p class="mb-3 text-center text-xs font-bold text-slate-400 tracking-wider">答题卡</p>
    <el-scrollbar max-height="calc(100vh - 12rem)">
      <div class="grid grid-cols-5 gap-1.5 pr-1.5">
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
  --practice-ok-border: rgba(16, 185, 129, 0.4);
  --practice-ok-bg: #ecfdf5;
  --practice-ok-text: #059669;
  --practice-bad-border: rgba(239, 68, 68, 0.3);
  --practice-bad-bg: #fef2f2;
  --practice-bad-text: #dc2626;

  height: 34px;
  width: 100%;
  border-radius: 9999px !important;
  border: 1px solid rgba(226, 232, 240, 0.8);
  background: #fff;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}
.navigator-cell:hover {
  border-color: #a5b4fc;
  color: #4f46e5;
  background: #f5f3ff;
}
.navigator-cell.is-selected,
.navigator-cell.is-answered {
  border-color: #c7d2fe;
  background: #e0e7ff;
  color: #4f46e5;
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
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
  color: #4f46e5;
  font-weight: 800;
}
</style>
