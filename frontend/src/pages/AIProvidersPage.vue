<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type AIProviderConfig } from '../api/client'
import AppBadge from '../components/AppBadge.vue'
import AppButton from '../components/AppButton.vue'
import AppModal from '../components/AppModal.vue'
import AIProviderFormModal from '../components/AIProviderFormModal.vue'
import { useToast } from '../composables/useToast'

const configs = ref<AIProviderConfig[]>([])
const formModal = ref(false)
const editingConfig = ref<AIProviderConfig | null>(null)
const testingId = ref<number | null>(null)
const deleteTarget = ref<AIProviderConfig | null>(null)
const toast = useToast()

async function load() {
  configs.value = await api<AIProviderConfig[]>('/api/v1/users/me/ai-provider-configs')
}

function openAdd() {
  editingConfig.value = null
  formModal.value = true
}

function openEdit(item: AIProviderConfig) {
  editingConfig.value = item
  formModal.value = true
}

async function handleSave(data: { name: string; api_base_url: string; api_key: string; model: string; is_default: boolean }) {
  try {
    if (editingConfig.value) {
      await api<AIProviderConfig>(`/api/v1/users/me/ai-provider-configs/${editingConfig.value.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name: data.name, api_base_url: data.api_base_url, model: data.model, is_default: data.is_default }),
      })
      toast.show('配置已更新', 'success')
    } else {
      await api<AIProviderConfig>('/api/v1/users/me/ai-provider-configs', { method: 'POST', body: JSON.stringify(data) })
      toast.show('配置已添加', 'success')
    }
    formModal.value = false
    editingConfig.value = null
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '保存失败', 'error')
  }
}

async function setDefault(id: number) {
  await api(`/api/v1/users/me/ai-provider-configs/${id}/set-default`, { method: 'POST' })
  await load()
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
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold">AI 配置</h1>
          <p class="mt-2 text-slate-600">添加 OpenAI 兼容接口，用于 AI 生成题库。</p>
        </div>
        <AppButton @click="openAdd">添加配置</AppButton>
      </div>
    </div>

    <div class="grid gap-3">
      <p v-if="!configs.length" class="page-card p-6 text-center text-sm text-slate-400">暂无配置，请先添加一个接口</p>
      <article v-for="item in configs" :key="item.id" class="page-card p-5">
        <div class="flex flex-wrap items-center justify-between gap-4">
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
            <AppButton variant="ghost" size="sm" @click="openEdit(item)">编辑</AppButton>
            <AppButton variant="danger" size="sm" @click="deleteTarget = item">删除</AppButton>
          </div>
        </div>
      </article>
    </div>

    <AIProviderFormModal
      v-model="formModal"
      :editing="editingConfig"
      @save="handleSave"
    />

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
