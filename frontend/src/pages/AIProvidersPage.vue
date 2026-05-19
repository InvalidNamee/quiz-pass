<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { AIProviderConfig } from '../api/types'
import {
  createAIConfig,
  deleteAIConfig,
  listAIConfigs,
  setDefaultAIConfig,
  testAIConfig,
  updateAIConfig,
} from '../api/v2/users'
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
  configs.value = await listAIConfigs()
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
      await updateAIConfig(editingConfig.value.id, { name: data.name, api_base_url: data.api_base_url, model: data.model, is_default: data.is_default })
      toast.show('配置已更新', 'success')
    } else {
      await createAIConfig(data)
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
  await setDefaultAIConfig(id)
  await load()
}

async function testConfig(id: number) {
  testingId.value = id
  try {
    await testAIConfig(id)
    toast.show('连接成功', 'success')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '连接失败', 'error')
  } finally {
    testingId.value = null
  }
}

async function remove(id: number) {
  await deleteAIConfig(id)
  deleteTarget.value = null
  toast.show('已删除', 'info')
  await load()
}

onMounted(load)
</script>

<template>
  <section class="grid gap-5">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-lg font-bold">AI 配置</h1>
      <AppButton size="sm" @click="openAdd">添加配置</AppButton>
    </div>

    <p v-if="!configs.length" class="py-8 text-center text-sm text-slate-400">暂无配置</p>
    <div v-else class="divide-y divide-slate-100 border-y border-slate-200">
      <div v-for="item in configs" :key="item.id" class="flex flex-wrap items-center justify-between gap-3 py-2.5">
        <div class="min-w-0 text-sm">
          <div class="flex items-center gap-1.5">
            <span class="font-medium text-slate-900">{{ item.name || item.model }}</span>
            <AppBadge v-if="item.is_default" variant="info">默认</AppBadge>
            <AppBadge :variant="item.is_active ? 'success' : 'warning'">{{ item.is_active ? '启用' : '未启用' }}</AppBadge>
          </div>
          <p class="text-xs text-slate-500">{{ item.model }} · {{ item.api_base_url }}</p>
        </div>
        <div class="flex gap-1">
          <AppButton variant="ghost" size="sm" :loading="testingId === item.id" @click="testConfig(item.id)">测试</AppButton>
          <AppButton variant="ghost" size="sm" @click="setDefault(item.id)">默认</AppButton>
          <AppButton variant="ghost" size="sm" @click="openEdit(item)">编辑</AppButton>
          <AppButton variant="danger" size="sm" @click="deleteTarget = item">删除</AppButton>
        </div>
      </div>
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
