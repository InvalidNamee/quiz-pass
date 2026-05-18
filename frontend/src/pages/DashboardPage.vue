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
  <section class="grid gap-5">
    <div class="page-card p-4">
      <h1 class="text-lg font-bold">欢迎，{{ auth.user?.display_name || auth.user?.username }}</h1>
    </div>
    <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      <RouterLink v-for="card in cards" :key="card.to" :to="card.to" class="page-card group p-4 transition-colors hover:border-brand-500/40">
        <span class="text-2xl">{{ card.icon }}</span>
        <strong class="mt-2 block group-hover:text-brand-600">{{ card.title }}</strong>
        <span class="mt-1 block text-sm text-slate-500">{{ card.desc }}</span>
      </RouterLink>
    </div>
  </section>
</template>
