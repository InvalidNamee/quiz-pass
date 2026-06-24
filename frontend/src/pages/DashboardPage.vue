<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import { useToast } from '../composables/useToast'
import { Bot, Globe2, History, Library, Plus, Settings, Sparkles, Star, Target, Zap } from '@lucide/vue'
import GenerateBankDialog from '../components/GenerateBankDialog.vue'
import AIConfigDialog from '../components/AIConfigDialog.vue'
import PracticeSetupDialog from '../components/PracticeSetupDialog.vue'
import { listRecentPracticeBanks } from '../api/v2/banks'
import type { QuestionBankV2 } from '../api/types'
import { practiceLastActivity, practiceProgressColor, practiceProgressPercent, practiceProgressText, practiceProgressType } from '../utils/practiceProgress'
import { isUtilityWindowSupported } from '../features/utility-windows/utilityWindow'
import { openAIConfigWindow, openBankGenerateWindow, openPracticeSetupWindow } from '../features/utility-windows/openUtilityFlows'

const auth = useAuthStore()
const router = useRouter()
const toast = useToast()

const createDialogVisible = ref(false)
const aiConfigVisible = ref(false)
const practiceDialogVisible = ref(false)
const selectedPracticeBank = ref<QuestionBankV2 | null>(null)
const recentBanks = ref<QuestionBankV2[]>([])
const recentLoading = ref(false)

const navs = [
  {
    to: '/banks',
    title: '我的题库',
    desc: '查看、扩展及复习专属题库。',
    icon: Library,
  },
  {
    to: '/banks/public',
    title: '公开题库',
    desc: '浏览和练习社区分享的公开知识。',
    icon: Globe2,
  },
  {
    to: '/favorites',
    title: '我的收藏',
    desc: '回顾及巩固星标收藏的题目。',
    icon: Star,
  },
  {
    to: '/history',
    title: '练习记录',
    desc: '回顾刷题成绩与通关测试历史。',
    icon: History,
  },
  {
    to: '/banks/generation-jobs',
    title: '生成任务',
    desc: '追踪 AI 题库智能生成流水线。',
    icon: Sparkles,
  },
  {
    to: '/settings/ai-providers',
    title: 'AI 配置',
    desc: '管理 API 接口、默认的 LLM 模型。',
    icon: Bot,
  },
]

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : '暂无'
}

function openPractice(bank: QuestionBankV2) {
  if (isUtilityWindowSupported()) {
    openPracticeSetupWindow({ bank }).catch((err) => toast.show(err instanceof Error ? err.message : '打开练习窗口失败', 'error'))
    return
  }
  selectedPracticeBank.value = bank
  practiceDialogVisible.value = true
}

function openCreateBank() {
  if (isUtilityWindowSupported()) {
    openBankGenerateWindow().catch((err) => toast.show(err instanceof Error ? err.message : '打开新建题库窗口失败', 'error'))
    return
  }
  createDialogVisible.value = true
}

function openAddAIConfig() {
  if (isUtilityWindowSupported()) {
    openAIConfigWindow().catch((err) => toast.show(err instanceof Error ? err.message : '打开 AI 配置窗口失败', 'error'))
    return
  }
  aiConfigVisible.value = true
}

function continuePractice(bank: QuestionBankV2) {
  if (!bank.resumable_session) return
  router.push(`/practice/session/${bank.resumable_session.id}?resume=1`)
}

async function loadRecentPractice() {
  recentLoading.value = true
  try {
    recentBanks.value = await listRecentPracticeBanks(6)
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '加载最近练习失败', 'error')
  } finally {
    recentLoading.value = false
  }
}

function handleUtilityCompleted(event: Event) {
  const detail = (event as CustomEvent<{ kind?: string }>).detail
  if (detail?.kind === 'bank-generate') void loadRecentPractice()
}

onMounted(() => {
  window.addEventListener('quiz-pass:utility-window-completed', handleUtilityCompleted)
  void loadRecentPractice()
})
onBeforeUnmount(() => {
  window.removeEventListener('quiz-pass:utility-window-completed', handleUtilityCompleted)
})
</script>

<template>
  <section class="qp-page">
    <div class="qp-section">
      <div class="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 class="qp-page-title">
            欢迎回来，{{ auth.user?.display_name || auth.user?.username }}
          </h1>
          <p class="qp-page-subtitle">
            AI 智能题库助手已就绪，今天您想练习哪个方向的题目？
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2.5">
          <el-button
            type="primary"
            @click="openCreateBank"
          >
            <Plus :size="16" class="mr-1" />新建题库
          </el-button>
          <el-button
            @click="openAddAIConfig"
          >
            <Settings :size="16" class="mr-1" />添加 AI 配置
          </el-button>
        </div>
      </div>
    </div>


    <div>
      <h2 class="mb-2 text-xs font-semibold tracking-wide text-slate-500">快捷工作导航</h2>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <RouterLink
          v-for="card in navs"
          :key="card.to"
          :to="card.to"
          class="group flex items-center gap-3 rounded-md border border-slate-200 bg-white p-3 transition-colors hover:border-indigo-200 hover:bg-indigo-50/30"
        >
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-indigo-100 bg-indigo-50 text-indigo-600">
            <component :is="card.icon" :size="17" />
          </div>

          <div class="flex-1 min-w-0">
            <h3 class="text-[14px] font-semibold leading-tight text-slate-800 group-hover:text-indigo-600">
              {{ card.title }}
            </h3>
            <p class="mt-1 truncate pr-1 text-[12px] text-slate-500">
              {{ card.desc }}
            </p>
          </div>
        </RouterLink>
      </div>
    </div>

    <div>
      <div class="mb-3 flex items-center justify-between gap-3">
        <h2 class="text-xs font-semibold tracking-wide text-slate-500">最近练习</h2>
        <RouterLink to="/history" class="text-xs font-semibold text-indigo-600 hover:text-indigo-500">查看全部</RouterLink>
      </div>
      <div v-loading="recentLoading" class="min-h-[120px]">
        <div v-if="recentBanks.length" class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          <div
            v-for="bank in recentBanks"
            :key="bank.id"
            class="group cursor-pointer rounded-md border border-slate-200 bg-white p-3 transition-colors hover:border-indigo-200 hover:bg-indigo-50/30"
            @click="router.push(`/banks/${bank.id}`)"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="truncate text-[14px] font-semibold text-slate-800 group-hover:text-indigo-600">{{ bank.title }}</div>
                <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                  <span>{{ bank.stats.question_count }} 题</span>
                  <span><Star :size="10" class="mr-0.5 inline text-amber-500" />{{ bank.stats.favorite_count }} 收藏</span>
                  <span>{{ formatTime(practiceLastActivity(bank.latest_practice_session)) }}</span>
                </div>
              </div>
              <el-tag v-if="bank.is_shared_copy" size="small" class="!rounded-md" type="info">副本</el-tag>
            </div>

            <div v-if="bank.latest_practice_session" class="mt-3 grid gap-1.5 rounded-md bg-slate-50 px-2.5 py-2">
              <div class="flex items-center justify-between gap-2 text-xs">
                <span class="font-semibold text-slate-500">{{ practiceProgressType(bank.latest_practice_session) }}</span>
                <span class="text-slate-400">{{ practiceProgressText(bank.latest_practice_session) }}</span>
              </div>
              <el-progress
                :percentage="practiceProgressPercent(bank.latest_practice_session)"
                :color="practiceProgressColor(bank.latest_practice_session)"
                :stroke-width="7"
                :show-text="false"
              />
            </div>

            <div class="mt-3 flex flex-wrap items-center gap-1.5 border-t border-slate-50 pt-3">
              <el-button v-if="bank.resumable_session" size="small" type="primary" @click.stop="continuePractice(bank)">
                <Zap :size="12" class="mr-1" />继续练习
              </el-button>
              <el-button v-else-if="bank.permissions.can_practice" size="small" @click.stop="openPractice(bank)">
                <Target :size="12" class="mr-1" />开始练习
              </el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="还没有练习记录" class="rounded-md border border-slate-200 bg-white">
          <RouterLink to="/banks"><el-button size="small" type="primary">去我的题库</el-button></RouterLink>
          <RouterLink to="/banks/public" class="ml-2"><el-button size="small">浏览公开题库</el-button></RouterLink>
        </el-empty>
      </div>
    </div>

    <!-- Reused existing GenerateBankDialog -->
    <GenerateBankDialog v-model="createDialogVisible" @submitted="loadRecentPractice" />

    <!-- Reused existing AIConfigDialog -->
    <AIConfigDialog v-model="aiConfigVisible" />

    <PracticeSetupDialog
      v-model="practiceDialogVisible"
      :bank-id="selectedPracticeBank?.id ?? null"
      :initial-bank="selectedPracticeBank"
    />
  </section>
</template>
