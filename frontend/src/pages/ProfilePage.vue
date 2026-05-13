<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const displayName = ref('')
const bio = ref('')
const avatarSource = ref('default')
const oldPassword = ref('')
const newPassword = ref('')
const profileMessage = ref('')
const passwordMessage = ref('')

onMounted(() => {
  displayName.value = auth.user?.display_name ?? ''
  bio.value = auth.user?.bio ?? ''
  avatarSource.value = auth.user?.avatar_source ?? 'default'
})

async function save() {
  await api('/api/v1/users/me', {
    method: 'PATCH',
    body: JSON.stringify({ display_name: displayName.value, bio: bio.value, avatar_source: avatarSource.value }),
  })
  await auth.loadMe()
  profileMessage.value = '资料已保存'
}

async function changePassword() {
  passwordMessage.value = ''
  await api('/api/v1/users/me/change-password', {
    method: 'POST',
    body: JSON.stringify({ old_password: oldPassword.value, new_password: newPassword.value }),
  })
  oldPassword.value = ''
  newPassword.value = ''
  passwordMessage.value = '密码已更新'
}
</script>

<template>
  <section>
    <h1 class="text-2xl font-bold">个人资料</h1>
    <div class="my-4 grid max-w-2xl gap-3">
      <input v-model="displayName" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="显示名称" />
      <textarea v-model="bio" class="min-h-28 rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="简介" />
      <select v-model="avatarSource" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="default">默认头像</option>
        <option value="qq_email">使用 QQ 邮箱头像</option>
        <option value="manual">手动头像 URL</option>
      </select>
      <button class="w-fit rounded-md bg-blue-600 px-4 py-2 text-white" @click="save">保存</button>
      <p v-if="profileMessage" class="font-bold text-green-700">{{ profileMessage }}</p>
    </div>

    <h2 id="password" class="text-xl font-semibold">修改密码</h2>
    <div class="my-4 grid max-w-2xl gap-3">
      <input v-model="oldPassword" class="rounded-md border border-slate-300 bg-white px-3 py-2" type="password" autocomplete="current-password" placeholder="当前密码" />
      <input v-model="newPassword" class="rounded-md border border-slate-300 bg-white px-3 py-2" type="password" autocomplete="new-password" placeholder="新密码（至少 8 位）" />
      <button class="w-fit rounded-md bg-blue-600 px-4 py-2 text-white" @click="changePassword">更新密码</button>
      <p v-if="passwordMessage" class="font-bold text-green-700">{{ passwordMessage }}</p>
    </div>
  </section>
</template>
