<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import { useToast } from '../composables/useToast'
import { Plus, Settings, Star, Target, Zap } from '@lucide/vue'
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
    iconClass: 'from-indigo-500 to-indigo-600',
    iconSvg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />'
  },
  {
    to: '/banks/public',
    title: '公开题库',
    desc: '浏览和练习社区分享的公开知识。',
    iconClass: 'from-purple-500 to-purple-600',
    iconSvg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />'
  },
  {
    to: '/favorites',
    title: '我的收藏',
    desc: '回顾及巩固星标收藏的题目。',
    iconClass: 'from-amber-500 to-amber-600',
    iconSvg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.907c.969 0 1.371 1.24.588 1.81l-3.97 2.88a1 1 0 00-.364 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.971-2.88a1 1 0 00-1.178 0l-3.97 2.88c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.364-1.118l-3.97-2.88c-.783-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />'
  },
  {
    to: '/history',
    title: '练习记录',
    desc: '回顾刷题成绩与通关测试历史。',
    iconClass: 'from-cyan-500 to-cyan-600',
    iconSvg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />'
  },
  {
    to: '/banks/generation-jobs',
    title: '生成任务',
    desc: '追踪 AI 题库智能生成流水线。',
    iconClass: 'from-emerald-500 to-emerald-600',
    iconSvg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />'
  },
  {
    to: '/settings/ai-providers',
    title: 'AI 配置',
    desc: '管理 API 接口、默认的 LLM 模型。',
    iconClass: 'from-rose-500 to-rose-600',
    iconSvg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />'
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
  <section class="qp-page space-y-6">
    <!-- Welcome banner with premium gradient and visual action buttons -->
    <div class="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 p-6 text-white shadow-xl shadow-indigo-500/10">
      <!-- Decorative geometric shapes -->
      <div class="absolute -right-16 -bottom-16 h-48 w-48 rounded-full bg-white/10 blur-xl" />
      <div class="absolute -top-16 -right-16 h-36 w-36 rounded-full bg-white/10 blur-lg" />

      <div class="relative z-10 flex flex-col justify-between gap-5 md:flex-row md:items-center">
        <div>
          <h1 class="text-2xl font-extrabold tracking-tight sm:text-3xl">
            欢迎回来，{{ auth.user?.display_name || auth.user?.username }}
          </h1>
          <p class="mt-1.5 text-sm text-indigo-50 font-medium">
            AI 智能题库助手已就绪，今天您想练习哪个方向的题目？
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2.5">
          <el-button
            type="default"
            class="!rounded-xl !h-10 !px-4.5 !bg-white/15 !border-white/20 !text-white hover:!bg-white/25 active:scale-95 transition-all shadow-inner font-bold"
            @click="openCreateBank"
          >
            <Plus :size="16" class="mr-1" />新建题库
          </el-button>
          <el-button
            type="default"
            class="!rounded-xl !h-10 !px-4.5 !bg-white/15 !border-white/20 !text-white hover:!bg-white/25 active:scale-95 transition-all shadow-inner font-bold"
            @click="openAddAIConfig"
          >
            <Settings :size="16" class="mr-1" />添加 AI 配置
          </el-button>
        </div>
      </div>
    </div>


    <!-- Compact 6 grid micro navigations -->
    <div>
      <h2 class="text-xs font-bold text-slate-400 tracking-wider uppercase mb-3">快捷工作导航</h2>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <RouterLink
          v-for="card in navs"
          :key="card.to"
          :to="card.to"
          class="group relative overflow-hidden rounded-2xl border border-slate-100 bg-white p-4 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md hover:border-indigo-500/15 flex items-center gap-3.5"
        >
          <!-- Flow gradient hover decoration -->
          <div class="absolute -right-8 -bottom-8 h-20 w-20 rounded-full bg-indigo-50/40 group-hover:scale-150 transition-all duration-500 opacity-50 blur-sm" />

          <div
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr text-white shadow-md shadow-slate-100 group-hover:scale-105 transition-all duration-300"
            :class="card.iconClass"
          >
            <svg class="h-4.5 w-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" v-html="card.iconSvg" />
          </div>

          <div class="flex-1 min-w-0">
            <h3 class="font-extrabold text-slate-800 text-[14px] leading-tight group-hover:text-indigo-600 transition-colors">
              {{ card.title }}
            </h3>
            <p class="text-[10px] text-slate-400 mt-1 truncate pr-1">
              {{ card.desc }}
            </p>
          </div>
        </RouterLink>
      </div>
    </div>

    <div>
      <div class="mb-3 flex items-center justify-between gap-3">
        <h2 class="text-xs font-bold text-slate-400 tracking-wider uppercase">最近练习</h2>
        <RouterLink to="/history" class="text-xs font-semibold text-indigo-600 hover:text-indigo-500">查看全部</RouterLink>
      </div>
      <div v-loading="recentLoading" class="min-h-[120px]">
        <div v-if="recentBanks.length" class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          <div
            v-for="bank in recentBanks"
            :key="bank.id"
            class="group cursor-pointer rounded-2xl border border-slate-100 bg-white p-4 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-indigo-500/15 hover:shadow-md"
            @click="router.push(`/banks/${bank.id}`)"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="truncate text-[14px] font-extrabold text-slate-800 group-hover:text-indigo-600">{{ bank.title }}</div>
                <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                  <span>{{ bank.stats.question_count }} 题</span>
                  <span><Star :size="10" class="mr-0.5 inline text-amber-500" />{{ bank.stats.favorite_count }} 收藏</span>
                  <span>{{ formatTime(practiceLastActivity(bank.latest_practice_session)) }}</span>
                </div>
              </div>
              <el-tag v-if="bank.is_shared_copy" size="small" class="!rounded-md" type="info">副本</el-tag>
            </div>

            <div v-if="bank.latest_practice_session" class="mt-3 grid gap-1.5 rounded-xl bg-slate-50/70 px-2.5 py-2">
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
              <el-button v-if="bank.resumable_session" size="small" type="primary" class="!h-8 !rounded-xl !bg-indigo-600 !border-indigo-600 !px-2.5 shadow-sm shadow-indigo-600/10" @click.stop="continuePractice(bank)">
                <Zap :size="12" class="mr-1" />继续练习
              </el-button>
              <el-button v-else-if="bank.permissions.can_practice" size="small" class="!h-8 !rounded-xl !px-2.5" @click.stop="openPractice(bank)">
                <Target :size="12" class="mr-1" />开始练习
              </el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="还没有练习记录" class="rounded-2xl border border-slate-100 bg-white shadow-sm">
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
