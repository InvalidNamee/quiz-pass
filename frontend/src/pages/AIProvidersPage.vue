<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type AIProviderConfig } from '../api/client'

const configs = ref<AIProviderConfig[]>([])
const form = ref({ name: '', api_base_url: '', api_key: '', model: '', is_default: true })
const editingId = ref<number | null>(null)
const editForm = ref({ name: '', api_base_url: '', model: '', is_default: false })
const message = ref('')

async function load() {
  configs.value = await api<AIProviderConfig[]>('/api/v1/users/me/ai-provider-configs')
}

async function save() {
  message.value = ''
  await api<AIProviderConfig>('/api/v1/users/me/ai-provider-configs', { method: 'POST', body: JSON.stringify(form.value) })
  form.value = { name: '', api_base_url: '', api_key: '', model: '', is_default: false }
  await load()
}

async function setDefault(id: number) {
  await api(`/api/v1/users/me/ai-provider-configs/${id}/set-default`, { method: 'POST' })
  await load()
}

function startEdit(item: AIProviderConfig) {
  editingId.value = item.id
  editForm.value = { name: item.name, api_base_url: item.api_base_url, model: item.model, is_default: item.is_default }
}

async function updateConfig(id: number) {
  await api<AIProviderConfig>(`/api/v1/users/me/ai-provider-configs/${id}`, { method: 'PATCH', body: JSON.stringify(editForm.value) })
  editingId.value = null
  await load()
}

async function testConfig(id: number) {
  try {
    await api(`/api/v1/users/me/ai-provider-configs/${id}/test`, { method: 'POST' })
    message.value = '连通性测试成功'
  } catch (err) {
    message.value = err instanceof Error ? err.message : '测试失败'
  }
}

async function remove(id: number) {
  await api(`/api/v1/users/me/ai-provider-configs/${id}`, { method: 'DELETE' })
  await load()
}

onMounted(load)
</script>

<template>
  <section>
    <h1 class="text-2xl font-bold">AI 配置</h1>
    <div class="my-4 grid max-w-2xl gap-3" autocomplete="off">
      <input v-model="form.name" class="rounded-md border border-slate-300 bg-white px-3 py-2" name="ai-config-name" placeholder="名称" autocomplete="off" />
      <input v-model="form.api_base_url" class="rounded-md border border-slate-300 bg-white px-3 py-2" name="ai-base-url" placeholder="API Base URL，例如 https://api.openai.com/v1" autocomplete="off" />
      <input v-model="form.api_key" class="rounded-md border border-slate-300 bg-white px-3 py-2" name="ai-access-token" placeholder="API Key（保存后不可修改，只能删除重建）" type="text" autocomplete="off" spellcheck="false" />
      <input v-model="form.model" class="rounded-md border border-slate-300 bg-white px-3 py-2" name="ai-model-name" placeholder="模型名称" autocomplete="off" />
      <label class="flex items-center gap-2"><input v-model="form.is_default" type="checkbox" /> 默认配置</label>
      <button class="w-fit rounded-md bg-blue-600 px-4 py-2 text-white" @click="save">保存配置</button>
      <p v-if="message">{{ message }}</p>
    </div>
    <div class="grid gap-3">
      <article v-for="item in configs" :key="item.id" class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div v-if="editingId !== item.id">
          <strong>{{ item.name }}</strong>
          <span class="block text-sm text-slate-500">{{ item.model }} · {{ item.api_base_url }} · {{ item.is_default ? '默认' : '非默认' }} · Key 已保存</span>
        </div>
        <div v-else class="grid flex-1 gap-2 md:grid-cols-2">
          <input v-model="editForm.name" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="名称" autocomplete="off" />
          <input v-model="editForm.api_base_url" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="API Base URL" autocomplete="off" />
          <input v-model="editForm.model" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="模型名称" autocomplete="off" />
          <label class="flex items-center gap-2"><input v-model="editForm.is_default" type="checkbox" /> 默认配置</label>
          <span class="text-sm text-slate-500">API Key 保存后不可修改</span>
        </div>
        <div class="flex flex-wrap gap-2">
          <button v-if="editingId !== item.id" class="rounded-md bg-slate-200 px-3 py-2 text-slate-900" @click="testConfig(item.id)">测试</button>
          <button v-if="editingId !== item.id" class="rounded-md bg-slate-200 px-3 py-2 text-slate-900" @click="setDefault(item.id)">设默认</button>
          <button v-if="editingId !== item.id" class="rounded-md bg-slate-200 px-3 py-2 text-slate-900" @click="startEdit(item)">编辑</button>
          <button v-if="editingId === item.id" class="rounded-md bg-slate-200 px-3 py-2 text-slate-900" @click="updateConfig(item.id)">保存</button>
          <button v-if="editingId === item.id" class="rounded-md bg-slate-200 px-3 py-2 text-slate-900" @click="editingId = null">取消</button>
          <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900" @click="remove(item.id)">删除</button>
        </div>
      </article>
    </div>
  </section>
</template>
