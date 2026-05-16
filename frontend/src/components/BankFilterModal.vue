<script setup lang="ts">
import { ref, watch } from 'vue'
import type { QuestionBankTag } from '../api/client'
import AppModal from './AppModal.vue'
import AppButton from './AppButton.vue'
import AuthorSelect from './AuthorSelect.vue'
import BankTagInput from './BankTagInput.vue'

const props = defineProps<{
  modelValue: boolean
  keyword: string
  ownerId: number | null
  selectedTags: QuestionBankTag[]
  visibility: string
  generationStatus: string
  showAuthorFilter?: boolean
  showVisibilityFilter?: boolean
  showGenerationFilter?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  apply: [filters: {
    keyword: string
    ownerId: number | null
    selectedTags: QuestionBankTag[]
    visibility: string
    generationStatus: string
  }]
}>()

const localKeyword = ref('')
const localOwnerId = ref<number | null>(null)
const localTags = ref<QuestionBankTag[]>([])
const localVisibility = ref('')
const localGenerationStatus = ref('')

watch(() => props.modelValue, (open) => {
  if (open) {
    localKeyword.value = props.keyword
    localOwnerId.value = props.ownerId
    localTags.value = [...props.selectedTags]
    localVisibility.value = props.visibility
    localGenerationStatus.value = props.generationStatus
  }
})

function doApply() {
  emit('apply', {
    keyword: localKeyword.value,
    ownerId: localOwnerId.value,
    selectedTags: localTags.value,
    visibility: localVisibility.value,
    generationStatus: localGenerationStatus.value,
  })
  emit('update:modelValue', false)
}

function clear() {
  localKeyword.value = ''
  localOwnerId.value = null
  localTags.value = []
  localVisibility.value = ''
  localGenerationStatus.value = ''
}
</script>

<template>
  <AppModal :model-value="modelValue" title="筛选题库" max-width="max-w-lg" @update:model-value="emit('update:modelValue', $event)">
    <div class="grid gap-4">
      <label class="grid gap-1">
        <span class="text-xs font-medium text-slate-500">关键词</span>
        <input v-model="localKeyword" class="rounded-input border border-slate-300 px-3 py-2 text-sm" placeholder="搜索标题或描述" @keyup.enter="doApply" />
      </label>
      <div v-if="showAuthorFilter">
        <AuthorSelect v-model="localOwnerId" />
      </div>
      <BankTagInput v-model="localTags" label="标签" placeholder="按标签筛选" />
      <div v-if="showVisibilityFilter" class="grid gap-1">
        <span class="text-xs font-medium text-slate-500">可见性</span>
        <div class="flex gap-4">
          <label class="flex items-center gap-1.5 text-sm">
            <input v-model="localVisibility" type="radio" value="" class="accent-brand-600" /> 全部
          </label>
          <label class="flex items-center gap-1.5 text-sm">
            <input v-model="localVisibility" type="radio" value="private" class="accent-brand-600" /> 私有
          </label>
          <label class="flex items-center gap-1.5 text-sm">
            <input v-model="localVisibility" type="radio" value="public" class="accent-brand-600" /> 公开
          </label>
        </div>
      </div>
      <div v-if="showGenerationFilter" class="grid gap-1">
        <span class="text-xs font-medium text-slate-500">生成状态</span>
        <select v-model="localGenerationStatus" class="rounded-input border border-slate-300 px-3 py-2 text-sm">
          <option value="">全部</option>
          <option value="none">普通题库</option>
          <option value="pending">等待生成</option>
          <option value="processing">生成中</option>
          <option value="succeeded">生成成功</option>
          <option value="failed">生成失败</option>
        </select>
      </div>
    </div>
    <template #footer>
      <AppButton variant="ghost" @click="clear">清空</AppButton>
      <AppButton variant="secondary" @click="emit('update:modelValue', false)">取消</AppButton>
      <AppButton @click="doApply">筛选</AppButton>
    </template>
  </AppModal>
</template>
