<script setup lang="ts">
import { ref } from 'vue'
import { listTags } from '../api/v2/banks'
import type { QuestionBankTag } from '../api/types'

const props = defineProps<{ modelValue: QuestionBankTag[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: QuestionBankTag[]] }>()

const dialogVisible = ref(false)
const allTags = ref<QuestionBankTag[]>([])
const selectedTagIds = ref<number[]>([])
const tagKeyword = ref('')

async function loadTagOptions() {
  allTags.value = (await listTags({ keyword: tagKeyword.value.trim() || undefined, page_size: 200 })).items
}

async function openDialog() {
  tagKeyword.value = ''
  await loadTagOptions()
  selectedTagIds.value = props.modelValue.map(t => t.id)
  dialogVisible.value = true
}

function toggleTag(tag: QuestionBankTag) {
  const idx = selectedTagIds.value.indexOf(tag.id)
  if (idx >= 0) selectedTagIds.value.splice(idx, 1)
  else selectedTagIds.value.push(tag.id)
}

function confirmTags() {
  const merged = [...props.modelValue, ...allTags.value]
  const next = selectedTagIds.value
    .map(id => merged.find(t => t.id === id))
    .filter((tag): tag is QuestionBankTag => Boolean(tag))
  dialogVisible.value = false
  emit('update:modelValue', next)
}
</script>

<template>
  <el-button size="small" @click="openDialog">{{ modelValue.length ? `标签(${modelValue.length})` : '标签' }}</el-button>

  <el-dialog v-model="dialogVisible" title="选择标签" width="420px">
    <div class="mb-3 flex gap-2">
      <el-input v-model="tagKeyword" placeholder="搜索标签" clearable @keyup.enter="loadTagOptions" @clear="loadTagOptions" />
      <el-button @click="loadTagOptions">搜索</el-button>
    </div>
    <div class="flex max-h-80 flex-wrap gap-2 overflow-y-auto">
      <el-tag v-for="tag in allTags" :key="tag.id" :type="selectedTagIds.includes(tag.id) ? 'primary' : 'info'" class="cursor-pointer" @click="toggleTag(tag)">{{ tag.name }}</el-tag>
    </div>
    <p v-if="!allTags.length" class="py-4 text-center text-sm text-slate-400">暂无标签</p>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="confirmTags">确定 ({{ selectedTagIds.length }})</el-button>
    </template>
  </el-dialog>
</template>
