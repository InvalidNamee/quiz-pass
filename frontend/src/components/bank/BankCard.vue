<script setup lang="ts">
import { statusVariant } from '../../api/http'
import type { QuestionBankV2 } from '../../api/types'
import AppAvatar from '../AppAvatar.vue'
import AppBadge from '../AppBadge.vue'

defineProps<{ bank: QuestionBankV2 }>()
const emit = defineEmits<{ toggleFavorite: [] }>()
</script>

<template>
  <div class="flex items-start gap-3 py-2.5 hover:bg-slate-50">
    <RouterLink class="min-w-0 flex-1" :to="`/banks/${bank.id}`">
      <div class="flex flex-wrap items-center gap-1.5">
        <span class="text-sm font-medium text-slate-900 hover:text-brand-600 truncate">{{ bank.title }}</span>
        <span class="text-xs text-slate-400">{{ bank.visibility === 'public' ? '公开' : '私有' }}</span>
        <AppBadge :variant="statusVariant(bank.generation_status)">{{ bank.generation_status === 'none' ? '' : bank.generation_status }}</AppBadge>
      </div>
      <p class="mt-0.5 text-xs text-slate-500 line-clamp-1">{{ bank.description || '暂无描述' }}</p>
      <div class="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-400">
        <RouterLink class="flex items-center gap-1 hover:text-brand-600" :to="`/users/${bank.owner.id}`" @click.stop>
          <AppAvatar :src="bank.owner.avatar_url" :username="bank.owner.display_name || bank.owner.username" size="sm" />
          <span>{{ bank.owner.display_name || bank.owner.username }}</span>
        </RouterLink>
        <span>{{ bank.stats.question_count }} 题</span>
        <span v-if="bank.tags.length" class="flex gap-1">
          <span v-for="tag in bank.tags.slice(0, 3)" :key="tag.id" class="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">{{ tag.name }}</span>
          <span v-if="bank.tags.length > 3" class="text-slate-400">+{{ bank.tags.length - 3 }}</span>
        </span>
      </div>
    </RouterLink>
    <button class="shrink-0 text-xs text-slate-400 hover:text-brand-600 py-0.5" @click="emit('toggleFavorite')">
      {{ bank.is_favorited ? '★' : '☆' }}
    </button>
  </div>
</template>
