<script setup lang="ts">
import { computed } from 'vue'
import type { QuestionType } from '../../api/types'

const props = defineProps<{
  total: number
  currentIndex: number
  statuses: ('correct' | 'wrong' | 'answered' | 'selected' | 'none')[]
  types?: QuestionType[]
}>()

const emit = defineEmits<{ go: [index: number] }>()

const typeLabels: Record<QuestionType, string> = {
  single: '单选',
  multiple: '多选',
  blank: '填空',
  short_answer: '简答',
}

const typeOrder: QuestionType[] = ['single', 'multiple', 'blank', 'short_answer']

const sections = computed(() => {
  if (!props.types?.length) {
    return [{ type: 'single' as QuestionType, label: '题目', items: props.statuses.map((status, index) => ({ status, index, displayNumber: index + 1 })) }]
  }
  let displayNumber = 0
  return typeOrder
    .map((type) => {
      const items = props.statuses
        .map((status, index) => ({ status, index, type: props.types?.[index] }))
        .filter((item) => item.type === type)
        .map((item) => ({ ...item, displayNumber: ++displayNumber }))
      return { type, label: typeLabels[type], items }
    })
    .filter((section) => section.items.length)
})

function getClass(status: string, isCurrent: boolean) {
  return [
    'navigator-cell',
    `is-${status || 'none'}`,
    isCurrent ? 'is-current' : '',
  ].join(' ')
}
</script>

<template>
  <div class="sticky top-5 max-h-[calc(100vh-8rem)] rounded-md border border-slate-200 bg-white p-3">
    <p class="mb-3 text-center text-xs font-bold text-slate-400 tracking-wider">答题卡</p>
    <el-scrollbar max-height="calc(100vh - 12rem)">
      <div class="space-y-3 pr-1.5">
        <section v-for="section in sections" :key="section.type" class="space-y-1.5">
          <p class="px-1 text-[11px] font-bold text-slate-400">{{ section.label }}</p>
          <div class="grid grid-cols-5 gap-1.5">
            <button
              v-for="item in section.items"
              :key="item.index"
              type="button"
              :class="getClass(item.status, item.index === currentIndex)"
              @click="emit('go', item.index)"
            >
              {{ item.displayNumber }}
            </button>
          </div>
        </section>
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
  border-radius: 6px !important;
  border: 1px solid rgba(226, 232, 240, 0.8);
  background: #fff;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color 0.15s ease, background-color 0.15s ease, color 0.15s ease;
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
