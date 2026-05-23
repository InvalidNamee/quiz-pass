<script setup lang="ts">
import type { AIGenerationDraftQuestion, Question } from '../../api/types'
import MathText from '../../components/MathText.vue'
import { optionCountLabel, sourceLabel } from './questionForm'

type Row = Question | AIGenerationDraftQuestion

withDefaults(defineProps<{
  questions: Row[]
  loading?: boolean
  showSource?: boolean
  showValidation?: boolean
  emptyText?: string
}>(), {
  loading: false,
  showSource: false,
  showValidation: false,
  emptyText: '暂无题目',
})

defineSlots<{
  actions(props: { row: Row; index: number }): unknown
}>()

function isFormalQuestion(row: Row): row is Question {
  return 'source' in row
}

function validationStatus(row: Row) {
  return 'validation_status' in row ? row.validation_status : 'valid'
}
</script>

<template>
  <el-table v-loading="loading" :data="questions" size="small" border :empty-text="emptyText">
    <el-table-column type="index" label="#" width="54" />
    <el-table-column label="题型" width="82">
      <template #default="{ row }: { row: Row }">
        <el-tag :type="row.type === 'single' ? 'primary' : 'warning'" size="small">{{ row.type === 'single' ? '单选' : '多选' }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="题干" min-width="340">
      <template #default="{ row }: { row: Row }">
        <div class="min-w-0">
          <MathText :key="`question-stem-${row.id}-${row.stem}`" as="span" class="line-clamp-2 text-slate-900" :text="row.stem || '未填写题干'" />
          <MathText v-if="row.explanation" :key="`question-explanation-${row.id}-${row.explanation}`" as="p" class="mt-1 line-clamp-1 text-sm text-slate-500" :text="row.explanation" />
        </div>
      </template>
    </el-table-column>
    <el-table-column label="选项" width="90">
      <template #default="{ row }: { row: Row }">{{ optionCountLabel(row) }}</template>
    </el-table-column>
    <el-table-column v-if="showSource" label="来源" width="90">
      <template #default="{ row }: { row: Row }">{{ isFormalQuestion(row) ? sourceLabel(row.source) : '' }}</template>
    </el-table-column>
    <el-table-column v-if="showValidation" label="校验" width="120">
      <template #default="{ row }: { row: Row }">
        <el-tag size="small" :type="validationStatus(row) === 'valid' ? 'success' : 'danger'">{{ validationStatus(row) }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="140" align="right" fixed="right">
      <template #default="{ row, $index }: { row: Row; $index: number }">
        <slot name="actions" :row="row" :index="$index" />
      </template>
    </el-table-column>
  </el-table>
</template>
