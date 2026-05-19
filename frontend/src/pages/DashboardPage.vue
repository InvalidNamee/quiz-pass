<script setup lang="ts">
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()

const cards = [
  { to: '/banks/generate', icon: '✦', title: '新建题库', desc: 'AI 生成、解析或 JSON 导入' },
  { to: '/banks', icon: '☰', title: '我的题库', desc: '管理已创建的题库' },
  { to: '/banks/public', icon: '◉', title: '公开题库', desc: '浏览社区分享的题库' },
  { to: '/history', icon: '↻', title: '刷题记录', desc: '回顾练习历史和成绩' },
]
</script>

<template>
  <section class="qp-page">
    <div class="qp-titlebar">
      <h1 class="qp-title">欢迎，{{ auth.user?.display_name || auth.user?.username }}</h1>
    </div>
    <div class="divide-y divide-slate-200 border border-slate-200 bg-white">
      <RouterLink v-for="card in cards" :key="card.to" :to="card.to" class="group flex items-center gap-3 px-3 py-2.5 hover:bg-blue-50">
        <span class="w-6 text-center text-base text-slate-500">{{ card.icon }}</span>
        <strong class="w-28 text-sm font-semibold text-slate-900 group-hover:text-blue-700">{{ card.title }}</strong>
        <span class="min-w-0 flex-1 text-sm text-slate-500">{{ card.desc }}</span>
      </RouterLink>
    </div>
  </section>
</template>
