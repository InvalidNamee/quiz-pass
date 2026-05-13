<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type AIProviderConfig } from '../api/client'
import AppBadge from '../components/AppBadge.vue'
import AppButton from '../components/AppButton.vue'
import AppModal from '../components/AppModal.vue'
import { useToast } from '../composables/useToast'

const configs = ref<AIProviderConfig[]>([])
const form = ref({ name: '', api_base_url: '', api_key: '', model: '', is_default: true })
const editingId = ref<number | null>(null)
const editForm = ref({ name: '', api_base_url: '', model: '', is_default: false })
const testingId = ref<number | null>(null)
const deleteTarget = ref<AIProviderConfig | null>(null)
const toast = useToast()

async function load() {
  configs.value = await api<AIProviderConfig[]>('/api/v1/users/me/ai-provider-configs')
}

async function save() {
  try {
    await api<AIProviderConfig>('/api/v1/users/me/ai-provider-configs', { method: 'POST', body: JSON.stringify(form.value) })
    form.value = { name: '', api_base_url: '', api_key: '', model: '', is_default: false }
    toast.show('配置已保存', 'success')
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '保存失败', 'error')
  }
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
  try {
    await api<AIProviderConfig>(`/api/v1/users/me/ai-provider-configs/${id}`, { method: 'PATCH', body: JSON.stringify(editForm.value) })
    editingId.value = null
    toast.show('配置已更新', 'success')
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '更新失败', 'error')
  }
}

async function testConfig(id: number) {
  testingId.value = id
  try {
    await api(`/api/v1/users/me/ai-provider-configs/${id}/test`, { method: 'POST' })
    toast.show('连接成功', 'success')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '连接失败', 'error')
  } finally {
    testingId.value = null
  }
}

async function remove(id: number) {
  await api(`/api/v1/users/me/ai-provider-configs/${id}`, { method: 'DELETE' })
  deleteTarget.value = null
  toast.show('已删除', 'info')
  await load()
}

onMounted(load)
</script>

<template>
  <section class="grid gap-5">
    <div class="page-card p-6">
      <h1 class="text-2xl font-bold">AI 配置</h1>
      <p class="mt-2 text-slate-600">添加 OpenAI 兼容接口，用于 AI 生成题库。</p>
    </div>

    <form class="page-card grid gap-4 p-6" autocomplete="off" @submit.prevent>
      <h2 class="text-lg font-semibold">添加新配置</h2>
      <div class="grid gap-3 sm:grid-cols-2">
        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">配置名称</span>
          <input v-model="form.name" name="ai-provider-name" class="rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="起个别名，方便区分（可选）" autocomplete="off" />
        </label>
        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">模型</span>
          <input v-model="form.model" name="ai-provider-model" class="rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="如 gpt-4o、deepseek-v4-flash" autocomplete="off" />
        </label>
        <label class="grid gap-1 sm:col-span-2">
          <span class="text-sm font-medium text-slate-700">接口地址</span>
          <input v-model="form.api_base_url" name="ai-provider-url" class="rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="https://api.openai.com/v1" autocomplete="off" />
        </label>
        <label class="grid gap-1 sm:col-span-2">
          <span class="text-sm font-medium text-slate-700">API Key</span>
          <input v-model="form.api_key" name="ai-provider-key" class="rounded-input border border-slate-300 bg-white px-3 py-2" type="password" placeholder="sk-..." autocomplete="new-password" />
          <span class="text-xs text-slate-400">保存后不可查看，只能删除重建。</span>
        </label>
      </div>
      <label class="flex items-center gap-2 text-sm text-slate-700">
        <input v-model="form.is_default" type="checkbox" class="rounded" /> 设为默认
      </label>
      <AppButton @click="save">添加</AppButton>
    </form>

    <div class="grid gap-3">
      <p v-if="!configs.length" class="page-card p-6 text-center text-sm text-slate-400">暂无配置，请先添加一个接口</p>
      <article v-for="item in configs" :key="item.id" class="page-card p-5">
        <div v-if="editingId !== item.id" class="flex flex-wrap items-center justify-between gap-4">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <strong>{{ item.name || item.model }}</strong>
              <AppBadge v-if="item.is_default" variant="info">默认</AppBadge>
              <AppBadge :variant="item.is_active ? 'success' : 'warning'">{{ item.is_active ? '启用' : '未启用' }}</AppBadge>
            </div>
            <p class="text-sm text-slate-500">{{ item.model }} · {{ item.api_base_url }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <AppButton variant="ghost" size="sm" :loading="testingId === item.id" @click="testConfig(item.id)">测试连接</AppButton>
            <AppButton variant="ghost" size="sm" @click="setDefault(item.id)">设为默认</AppButton>
            <AppButton variant="ghost" size="sm" @click="startEdit(item)">编辑</AppButton>
            <AppButton variant="danger" size="sm" @click="deleteTarget = item">删除</AppButton>
          </div>
        </div>
        <div v-else class="grid gap-3 sm:grid-cols-2">
          <input v-model="editForm.name" name="ai-edit-name" class="rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="配置名称" autocomplete="off" />
          <input v-model="editForm.model" name="ai-edit-model" class="rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="模型名称" autocomplete="off" />
          <input v-model="editForm.api_base_url" name="ai-edit-url" class="rounded-input border border-slate-300 bg-white px-3 py-2 sm:col-span-2" placeholder="接口地址" autocomplete="off" />
          <label class="flex items-center gap-2 text-sm sm:col-span-2">
            <input v-model="editForm.is_default" type="checkbox" class="rounded" /> 设为默认
          </label>
          <div class="flex gap-2 sm:col-span-2">
            <AppButton size="sm" @click="updateConfig(item.id)">保存</AppButton>
            <AppButton variant="ghost" size="sm" @click="editingId = null">取消</AppButton>
          </div>
        </div>
      </article>
    </div>

    <AppModal :model-value="!!deleteTarget" :key="deleteTarget?.id" title="删除配置" @update:model-value="val => !val && (deleteTarget = null)">
      <template v-if="deleteTarget">
        <p class="text-slate-600">确定要删除「{{ deleteTarget.name || deleteTarget.model }}」吗？</p>
      </template>
      <template #footer>
        <AppButton variant="ghost" @click="deleteTarget = null">取消</AppButton>
        <AppButton variant="danger" @click="remove(deleteTarget!.id)">删除</AppButton>
      </template>
    </AppModal>
  </section>
</template>
