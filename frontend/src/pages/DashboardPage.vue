<script setup lang="ts">
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const cards = [
  { to: '/banks/generate', icon: '✦', title: 'AI 生成题库', desc: '上传文档，AI 自动生成选择题' },
  { to: '/banks/import', icon: '↑', title: '导入题库', desc: '从 JSON 文件导入已有题库' },
  { to: '/banks', icon: '☰', title: '我的题库', desc: '管理已创建和生成的题库' },
  { to: '/banks/public', icon: '◉', title: '公开题库', desc: '浏览社区分享的题库' },
  { to: '/favorites', icon: '★', title: '我的收藏', desc: '查看已收藏的题库' },
  { to: '/history', icon: '↻', title: '刷题记录', desc: '回顾练习历史和成绩' },
]
</script>

<template>
  <section class="grid gap-6">
    <div class="page-card p-6">
      <h1 class="text-2xl font-bold">欢迎回来，{{ auth.user?.display_name || auth.user?.username }}</h1>
      <p class="mt-1 text-slate-600">选择一个入口开始学习。</p>
    </div>

    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink
        v-for="card in cards"
        :key="card.to"
        :to="card.to"
        class="page-card group p-5 transition-colors hover:border-brand-500/40"
      >
        <span class="text-2xl">{{ card.icon }}</span>
        <strong class="mt-3 block group-hover:text-brand-600">{{ card.title }}</strong>
        <span class="mt-1 block text-sm text-slate-600">{{ card.desc }}</span>
      </RouterLink>
    </div>
  </section>
</template>
