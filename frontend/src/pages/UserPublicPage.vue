<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { QuestionBankV2, UserPublic } from '../api/types'
import { listBanks, favoriteBank, unfavoriteBank } from '../api/v2/banks'
import { Rocket, Star, Zap } from '@lucide/vue'
import { getUserPublic } from '../api/v2/users'
import UserAvatar from '../components/UserAvatar.vue'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const user = ref<UserPublic | null>(null)
const banks = ref<QuestionBankV2[]>([])
const loading = ref(true)

function formatDate(value: string) {
  return new Date(value).toLocaleDateString()
}

async function toggleFavorite(bank: QuestionBankV2) {
  const next = !bank.is_favorited
  bank.is_favorited = next
  try {
    if (next) await favoriteBank(bank.id)
    else await unfavoriteBank(bank.id)
  } catch {
    bank.is_favorited = !next
    toast.show('操作失败', 'error')
  }
}

onMounted(async () => {
  try {
    const userId = Number(route.params.userId)
    user.value = await getUserPublic(userId)
    banks.value = (await listBanks('public', { owner_id: userId, page_size: 100 })).items
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section v-loading="loading" class="qp-page" element-loading-text="加载中...">
    <template v-if="user">
      <div class="qp-section">
        <div class="flex flex-wrap items-center gap-4">
          <UserAvatar :src="user.avatar_url" :name="user.display_name || user.username" :size="64" />
          <div class="min-w-0">
            <h1 class="text-lg font-semibold">{{ user.display_name || user.username }}</h1>
            <p class="text-slate-500">@{{ user.username }} · #{{ user.id }}</p>
          </div>
        </div>
        <p class="mt-3 text-sm text-slate-700">{{ user.bio || '这个用户还没有填写简介。' }}</p>
        <el-descriptions :column="3" border class="mt-3" size="small">
          <el-descriptions-item label="公开题库">{{ user.public_bank_count }}</el-descriptions-item>
          <el-descriptions-item label="注册时间">{{ formatDate(user.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="用户 ID">#{{ user.id }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="qp-section">
        <div class="flex items-center justify-between gap-4 mb-3">
          <h2 class="qp-section-title m-0">公开题库</h2>
          <span class="text-sm text-slate-500">{{ banks.length }} 个可见</span>
        </div>

        <el-table :data="banks" size="small" empty-text="暂无公开题库" @row-click="(row: QuestionBankV2) => router.push(`/banks/${row.id}`)" class="cursor-pointer">
          <el-table-column label="题库" min-width="240">
            <template #default="{ row }: { row: QuestionBankV2 }">
              <div class="flex flex-col gap-0.5">
                <div class="flex items-center gap-1.5">
                  <button
                    class="text-lg leading-none transition-colors"
                    :class="row.is_favorited ? 'text-amber-500 hover:text-amber-400' : 'text-slate-300 hover:text-slate-400'"
                    @click.stop="toggleFavorite(row)"
                  ><Star :size="18" :fill="row.is_favorited ? '#f59e0b' : 'none'" /></button>
                  <span class="font-medium text-slate-900">{{ row.title }}</span>
                  <el-tag v-if="row.is_shared_copy" size="small" type="info">共享副本</el-tag>
                </div>
                <span class="text-xs text-slate-400 truncate max-w-xs">{{ row.description || '暂无描述' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="标签" min-width="160">
            <template #default="{ row }: { row: QuestionBankV2 }">
              <div class="flex flex-wrap gap-1">
                <el-tag v-for="tag in row.tags.slice(0, 3)" :key="tag.id" size="small" type="info">{{ tag.name }}</el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="题目数" width="70" align="center">
            <template #default="{ row }: { row: QuestionBankV2 }">{{ row.stats.question_count }}</template>
          </el-table-column>
          <el-table-column label="收藏数" width="80" align="center">
            <template #default="{ row }: { row: QuestionBankV2 }">{{ row.stats.favorite_count }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" align="left" header-align="left">
            <template #default="{ row }: { row: QuestionBankV2 }">
              <div class="qp-icon-actions">
                <el-tooltip v-if="row.resumable_session" content="继续练习" placement="top">
                  <el-button size="small" class="qp-icon-button is-blue" @click.stop="router.push(`/practice/session/${row.resumable_session.id}?resume=1`)">
                    <Zap :size="16" />
                  </el-button>
                </el-tooltip>
                <el-tooltip v-if="row.permissions.can_practice" content="开始练习" placement="top">
                  <el-button size="small" class="qp-icon-button" @click.stop="router.push(`/banks/${row.id}?practice=1`)">
                    <Rocket :size="16" />
                  </el-button>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>
  </section>
</template>
