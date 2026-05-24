<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import UserAvatar from './UserAvatar.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const emit = defineEmits<{ close: [] }>()

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
  <div class="flex h-full flex-col border-r border-slate-100 bg-white/90 backdrop-blur-xl">
    <!-- Brand header -->
    <div class="hidden items-center gap-2 border-b border-slate-100 px-5 py-4 md:flex">
      <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-600 text-white shadow-sm shadow-indigo-500/20">
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      </div>
      <span class="bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-base font-extrabold tracking-wide text-transparent">Quiz Pass</span>
    </div>

    <!-- Navigation Menu -->
    <el-menu
      :default-active="route.path"
      class="flex-1 border-r-0 !bg-transparent px-3 py-3"
      @select="handleSelect"
    >
      <el-menu-item index="/dashboard">
        <div class="flex items-center gap-2.5">
          <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4zM14 16a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 01-2-2v-4z" />
          </svg>
          <span>首页</span>
        </div>
      </el-menu-item>

      <el-menu-item index="/banks">
        <div class="flex items-center gap-2.5">
          <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <span>我的题库</span>
        </div>
      </el-menu-item>

      <el-menu-item index="/banks/public">
        <div class="flex items-center gap-2.5">
          <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
          </svg>
          <span>公开题库</span>
        </div>
      </el-menu-item>

      <el-menu-item index="/favorites">
        <div class="flex items-center gap-2.5">
          <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.907c.969 0 1.371 1.24.588 1.81l-3.97 2.88a1 1 0 00-.364 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.971-2.88a1 1 0 00-1.178 0l-3.97 2.88c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.364-1.118l-3.97-2.88c-.783-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
          </svg>
          <span>我的收藏</span>
        </div>
      </el-menu-item>

      <el-menu-item index="/history">
        <div class="flex items-center gap-2.5">
          <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>练习记录</span>
        </div>
      </el-menu-item>

      <el-menu-item index="/banks/generation-jobs">
        <div class="flex items-center gap-2.5">
          <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <span>生成任务</span>
        </div>
      </el-menu-item>

      <el-menu-item index="/settings/ai-providers">
        <div class="flex items-center gap-2.5">
          <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span>AI 配置</span>
        </div>
      </el-menu-item>

      <el-menu-item v-if="auth.user?.role === 'admin'" index="/admin/users">
        <div class="flex items-center gap-2.5">
          <svg class="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
          <span>用户管理</span>
        </div>
      </el-menu-item>
    </el-menu>

    <!-- User Section -->
    <div class="border-t border-slate-100 p-4">
      <el-dropdown trigger="click" class="w-full" @command="(cmd: string) => { if (cmd === 'logout') logout(); else router.push(cmd); emit('close') }">
        <el-button text class="!flex !h-auto w-full !justify-start !rounded-xl !p-2 text-left text-slate-700 hover:!bg-slate-50 transition-all">
          <div class="flex items-center gap-2.5 min-w-0">
            <UserAvatar :src="auth.user?.avatar_url" :name="auth.user?.display_name || auth.user?.username" :size="32" class="ring-2 ring-indigo-500/10 shadow-sm" />
            <div class="flex flex-col min-w-0 leading-tight">
              <span class="truncate text-sm font-semibold text-slate-800">{{ auth.user?.display_name || auth.user?.username }}</span>
              <span class="truncate text-[10px] text-slate-400 mt-0.5 capitalize">{{ auth.user?.role || 'user' }}</span>
            </div>
          </div>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu class="!rounded-xl shadow-xl border border-slate-100">
            <el-dropdown-item :command="`/users/${auth.user?.id}`">个人主页</el-dropdown-item>
            <el-dropdown-item command="/profile">账号设置</el-dropdown-item>
            <el-dropdown-item command="logout" divided class="!text-red-500">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>
