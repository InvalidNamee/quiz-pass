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
import { useToast } from '../composables/useToast'

const configs = ref<AIProviderConfig[]>([])
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const form = ref({ name: '', api_base_url: '', api_key: '', model: '', is_default: false })
const testingId = ref<number | null>(null)
const deleteTarget = ref<AIProviderConfig | null>(null)
const toast = useToast()

async function load() { configs.value = await listAIConfigs() }

function openAdd() {
  editingId.value = null; form.value = { name: '', api_base_url: '', api_key: '', model: '', is_default: false }; formVisible.value = true
}
function openEdit(item: AIProviderConfig) {
  editingId.value = item.id; form.value = { name: item.name, api_base_url: item.api_base_url, api_key: '', model: item.model, is_default: item.is_default }; formVisible.value = true
}
async function handleSave() {
  try {
    if (editingId.value) { await updateAIConfig(editingId.value, { name: form.value.name, api_base_url: form.value.api_base_url, model: form.value.model, is_default: form.value.is_default }); toast.show('已更新', 'success') }
    else { await createAIConfig({ ...form.value }); toast.show('已添加', 'success') }
    formVisible.value = false; await load()
  } catch (err) { toast.show(err instanceof Error ? err.message : '保存失败', 'error') }
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
  <section class="qp-page">
    <div class="qp-titlebar">
      <h1 class="qp-title">AI 配置</h1>
      <el-button size="small" @click="openAdd">添加配置</el-button>
    </div>

    <el-table :data="configs" size="small" empty-text="暂无配置">
      <el-table-column label="名称" min-width="180">
        <template #default="{ row }">
          <div class="flex items-center gap-1.5">
            <span class="font-medium text-slate-900">{{ row.name || row.model }}</span>
            <el-tag v-if="row.is_default" type="info" size="small">默认</el-tag>
            <el-tag :type="row.is_active ? 'success' : 'warning'" size="small">{{ row.is_active ? '启用' : '未启用' }}</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="模型" prop="model" min-width="160" />
      <el-table-column label="API 地址" prop="api_base_url" min-width="200" show-overflow-tooltip />
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button text size="small" :loading="testingId === row.id" @click="testConfig(row.id)">测试</el-button>
          <el-button text size="small" @click="setDefault(row.id)">默认</el-button>
          <el-button text size="small" @click="openEdit(row)">编辑</el-button>
          <el-button text size="small" type="danger" @click="deleteTarget = row">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="formVisible" :title="editingId ? '编辑配置' : '添加配置'" width="460px">
      <el-form label-position="top" size="default">
        <el-form-item label="配置名称"><el-input v-model="form.name" placeholder="起个名字" /></el-form-item>
        <el-form-item label="接口地址"><el-input v-model="form.api_base_url" placeholder="https://api.openai.com/v1" /></el-form-item>
        <el-form-item label="模型"><el-input v-model="form.model" placeholder="gpt-4o" /></el-form-item>
        <el-form-item v-if="!editingId" label="API Key"><el-input v-model="form.api_key" autocomplete="off" placeholder="sk-..." /><span class="text-xs text-slate-400">保存后不可查看、不可编辑，只能删除重建</span></el-form-item>
        <el-form-item><el-checkbox v-model="form.is_default">设为默认</el-checkbox></el-form-item>
      </el-form>
      <template #footer><el-button @click="formVisible = false">取消</el-button><el-button type="primary" @click="handleSave">{{ editingId ? '保存' : '添加' }}</el-button></template>
    </el-dialog>

    <el-dialog :model-value="!!deleteTarget" :key="deleteTarget?.id" title="删除配置" @update:model-value="(val: boolean) => !val && (deleteTarget = null)">
      <template v-if="deleteTarget">
        <p class="text-slate-600">确定要删除「{{ deleteTarget.name || deleteTarget.model }}」吗？</p>
      </template>
      <template #footer>
        <el-button @click="deleteTarget = null">取消</el-button>
        <el-button type="danger" @click="remove(deleteTarget!.id)">删除</el-button>
      </template>
    </el-dialog>
  </section>
</template>
