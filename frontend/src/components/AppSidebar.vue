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
  <div class="flex h-full flex-col border-r border-slate-200 bg-white">
    <div class="hidden border-b border-slate-200 px-4 py-3 text-base font-semibold text-slate-900 md:block">Quiz Pass</div>
    <el-menu
      :default-active="route.path"
      class="flex-1 border-r-0 bg-white px-2 py-2"
      @select="handleSelect"
    >
      <el-menu-item index="/dashboard">首页</el-menu-item>
      <el-menu-item index="/banks">我的题库</el-menu-item>
      <el-menu-item index="/banks/public">公开题库</el-menu-item>
      <el-menu-item index="/favorites">我的收藏</el-menu-item>
      <el-menu-item index="/history">刷题记录</el-menu-item>
      <el-menu-item index="/banks/generation-jobs">生成队列</el-menu-item>
      <el-menu-item index="/settings/ai-providers">AI 配置</el-menu-item>
      <el-menu-item v-if="auth.user?.role === 'admin'" index="/admin/users">用户管理</el-menu-item>
    </el-menu>
    <div class="border-t border-slate-200 px-3 py-2">
      <el-dropdown trigger="click" @command="(cmd: string) => { if (cmd === 'logout') logout(); else router.push(cmd); emit('close') }">
        <el-button text class="!flex !h-auto w-full !justify-start !px-1.5 !py-1 text-left text-slate-700 hover:bg-slate-50">
          <UserAvatar :src="auth.user?.avatar_url" :name="auth.user?.display_name || auth.user?.username" :size="36" />
          <span class="flex-1 truncate text-sm">{{ auth.user?.display_name || auth.user?.username }}</span>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item :command="`/users/${auth.user?.id}`">个人主页</el-dropdown-item>
            <el-dropdown-item command="/profile">账号设置</el-dropdown-item>
            <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>
