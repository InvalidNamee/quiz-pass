<script setup lang="ts">
import type { QuestionBankV2 } from '../../api/types'
import AppAvatar from '../AppAvatar.vue'
import AppBadge from '../AppBadge.vue'
import AppButton from '../AppButton.vue'

defineProps<{ bank: QuestionBankV2 }>()
const emit = defineEmits<{ toggleFavorite: [] }>()

function statusText(bank: QuestionBankV2) {
  const v = bank.visibility === 'public' ? '公开' : '私有'
  const m: Record<string, string> = { none: '普通', pending: '等待', processing: '生成中', succeeded: '成功', failed: '失败' }
  return `${v} · ${m[bank.generation_status] || bank.generation_status}`
}
function statusVariant(s: string): 'default'|'success'|'warning'|'danger'|'info' {
  const m: Record<string, 'default'|'success'|'warning'|'danger'|'info'> = { none: 'default', pending: 'warning', processing: 'info', succeeded: 'success', failed: 'danger' }
  return m[s] || 'default'
}
</script>

<template>
  <article class="page-card p-3 transition-colors hover:border-brand-500/30">
    <div class="flex flex-wrap items-start justify-between gap-2">
      <RouterLink class="min-w-0 flex-1" :to="`/banks/${bank.id}`">
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="truncate text-base font-semibold hover:text-brand-600">{{ bank.title }}</h2>
          <AppBadge :variant="statusVariant(bank.generation_status)">{{ statusText(bank) }}</AppBadge>
        </div>
        <p class="mt-1 line-clamp-2 text-sm text-slate-500">{{ bank.description || '暂无描述' }}</p>
        <div v-if="bank.tags.length" class="mt-2 flex flex-wrap gap-1">
          <span v-for="tag in bank.tags" :key="tag.id" class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{{ tag.name }}</span>
        </div>
      </RouterLink>
      <AppButton variant="ghost" size="sm" @click="emit('toggleFavorite')">{{ bank.is_favorited ? '已收藏' : '收藏' }}</AppButton>
    </div>
    <div class="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
      <RouterLink class="flex items-center gap-1.5 hover:text-brand-600" :to="`/users/${bank.owner.id}`">
        <AppAvatar :src="bank.owner.avatar_url" :username="bank.owner.display_name || bank.owner.username" size="sm" />
        <span>{{ bank.owner.display_name || bank.owner.username }}</span>
      </RouterLink>
      <span>{{ bank.stats.question_count }} 题 · {{ bank.stats.favorite_count }} 收藏</span>
    </div>
  </article>
</template>
