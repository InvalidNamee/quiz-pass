<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listTags } from '../../api/v2/banks'
import type { QuestionBankTag } from '../../api/types'
import { useToast } from '../../composables/useToast'
import { useUtilityWindowPage } from '../../features/utility-windows/useUtilityWindowPage'

type Payload = {
  selectedTags?: QuestionBankTag[]
  requestId?: string
}

const toast = useToast()
const { payload, complete, closeWindow } = useUtilityWindowPage<Payload>('tag-filter')
const allTags = ref<QuestionBankTag[]>([])
const selectedTagIds = ref<number[]>([])
const tagKeyword = ref('')
const loading = ref(false)

async function loadTagOptions() {
  loading.value = true
  try {
    allTags.value = (await listTags({ keyword: tagKeyword.value.trim() || undefined, page_size: 200 })).items
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '加载标签失败', 'error')
    allTags.value = []
  } finally {
    loading.value = false
  }
}

function toggleTag(tag: QuestionBankTag) {
  const index = selectedTagIds.value.indexOf(tag.id)
  if (index >= 0) selectedTagIds.value.splice(index, 1)
  else selectedTagIds.value.push(tag.id)
}

function confirmTags() {
  const merged = [...(payload.value.selectedTags || []), ...allTags.value]
  const next = selectedTagIds.value
    .map((id) => merged.find((tag) => tag.id === id))
    .filter((tag): tag is QuestionBankTag => Boolean(tag))
  complete('tags-selected', { tags: next })
}

onMounted(async () => {
  selectedTagIds.value = (payload.value.selectedTags || []).map((tag) => tag.id)
  await loadTagOptions()
})
</script>

<template>
  <section class="min-h-screen bg-white p-4 text-slate-700">
    <div class="space-y-4">
      <div>
        <h1 class="m-0 text-base font-semibold text-slate-900">选择标签</h1>
        <p class="mt-1 text-sm text-slate-500">搜索已有标签并组合筛选题库。</p>
      </div>

      <div class="flex gap-2">
        <el-input v-model="tagKeyword" placeholder="搜索标签" clearable @keyup.enter="loadTagOptions" @clear="loadTagOptions" />
        <el-button @click="loadTagOptions">搜索</el-button>
      </div>

      <div v-loading="loading" class="flex max-h-80 min-h-32 flex-wrap content-start gap-2 overflow-y-auto rounded-md border border-slate-200 p-3">
        <el-tag v-for="tag in allTags" :key="tag.id" :type="selectedTagIds.includes(tag.id) ? 'primary' : 'info'" class="cursor-pointer" @click="toggleTag(tag)">
          {{ tag.name }}
        </el-tag>
        <p v-if="!allTags.length && !loading" class="w-full py-6 text-center text-sm text-slate-400">暂无标签</p>
      </div>

      <div class="flex justify-end gap-2 pt-2">
        <el-button @click="closeWindow">取消</el-button>
        <el-button type="primary" @click="confirmTags">确定 ({{ selectedTagIds.length }})</el-button>
      </div>
    </div>
  </section>
</template>
