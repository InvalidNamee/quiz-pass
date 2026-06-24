<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  BookOpen,
  Bot,
  Clock3,
  Globe2,
  HardDrive,
  History,
  Home,
  Library,
  Sparkles,
  Star,
  Users,
} from '@lucide/vue'
import { useAuthStore } from '../stores/auth'
import UserAvatar from './UserAvatar.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const emit = defineEmits<{ close: [] }>()

const groups = computed(() => [
  {
    title: '学习',
    items: [
      { label: '首页', to: '/dashboard', icon: Home },
      { label: '练习记录', to: '/history', icon: History },
      { label: '本地记录', to: '/local/history', icon: Clock3 },
    ],
  },
  {
    title: '题库',
    items: [
      { label: '我的题库', to: '/banks', icon: Library },
      { label: '本地题库', to: '/local/banks', icon: HardDrive },
      { label: '公开题库', to: '/banks/public', icon: Globe2 },
      { label: '我的收藏', to: '/favorites', icon: Star },
    ],
  },
  {
    title: 'AI',
    items: [
      { label: '生成任务', to: '/banks/generation-jobs', icon: Sparkles },
      { label: 'AI 配置', to: '/settings/ai-providers', icon: Bot },
    ],
  },
  {
    title: '管理',
    items: auth.user?.role === 'admin'
      ? [{ label: '用户管理', to: '/admin/users', icon: Users }]
      : [],
  },
].filter(group => group.items.length))

function logout() {
  auth.logout()
  router.push('/login')
  emit('close')
}

function handleSelect(index: string) {
  router.push(index)
  emit('close')
}
</script>

<template>
  <div class="flex h-full flex-col border-r border-slate-200 bg-white">
    <div class="hidden items-center gap-2 border-b border-slate-200 px-4 py-3 md:flex">
      <div class="flex h-8 w-8 items-center justify-center rounded-md border border-indigo-100 bg-indigo-50 text-indigo-600">
        <BookOpen :size="17" />
      </div>
      <span class="text-base font-bold tracking-wide text-slate-900">Quiz Pass</span>
    </div>

    <el-menu
      :default-active="route.path"
      class="flex-1 overflow-y-auto border-r-0 !bg-transparent px-2 py-3"
      @select="handleSelect"
    >
      <template v-for="group in groups" :key="group.title">
        <div class="px-3 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400 first:pt-0">
          {{ group.title }}
        </div>
        <el-menu-item v-for="item in group.items" :key="item.to" :index="item.to">
          <div class="flex items-center gap-2.5">
            <component :is="item.icon" :size="16" class="shrink-0" />
            <span>{{ item.label }}</span>
          </div>
        </el-menu-item>
      </template>
    </el-menu>

    <div class="border-t border-slate-200 p-3">
      <el-dropdown trigger="click" class="w-full" @command="(cmd: string) => { if (cmd === 'logout') logout(); else router.push(cmd); emit('close') }">
        <el-button text class="!flex !h-auto w-full !justify-start !rounded-md !p-2 text-left text-slate-700 hover:!bg-slate-50">
          <div class="flex min-w-0 items-center gap-2.5">
            <UserAvatar :src="auth.user?.avatar_url" :name="auth.user?.display_name || auth.user?.username" :size="32" />
            <div class="flex min-w-0 flex-col leading-tight">
              <span class="truncate text-sm font-semibold text-slate-800">{{ auth.user?.display_name || auth.user?.username }}</span>
              <span class="mt-0.5 truncate text-[11px] capitalize text-slate-400">{{ auth.user?.role || 'user' }}</span>
            </div>
          </div>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu class="!rounded-md border border-slate-200">
            <el-dropdown-item :command="`/users/${auth.user?.id}`">个人主页</el-dropdown-item>
            <el-dropdown-item command="/profile">账号设置</el-dropdown-item>
            <el-dropdown-item command="logout" divided class="!text-red-500">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>
