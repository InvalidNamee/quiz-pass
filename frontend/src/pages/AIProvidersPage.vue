<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { AIProviderConfig } from '../api/types'
import {
  deleteAIConfig,
  listAIConfigs,
  setDefaultAIConfig,
  testAIConfig,
} from '../api/v2/users'
import { Link, Star, Pencil, Trash2 } from '@lucide/vue'
import { useToast } from '../composables/useToast'
import AIConfigDialog from '../components/AIConfigDialog.vue'

const configs = ref<AIProviderConfig[]>([])
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const form = ref<{ name: string; api_base_url: string; api_key: string; model: string; response_format_type: 'json_object' | 'json_schema'; is_default: boolean }>({
  name: '',
  api_base_url: '',
  api_key: '',
  model: '',
  response_format_type: 'json_object',
  is_default: false,
})
const testingId = ref<number | null>(null)
const deleteTarget = ref<AIProviderConfig | null>(null)
const toast = useToast()

async function load() { configs.value = await listAIConfigs() }

function openAdd() {
  editingId.value = null; form.value = { name: '', api_base_url: '', api_key: '', model: '', response_format_type: 'json_object', is_default: false }; formVisible.value = true
}
function openEdit(item: AIProviderConfig) {
  editingId.value = item.id; form.value = { name: item.name, api_base_url: item.api_base_url, api_key: '', model: item.model, response_format_type: item.response_format_type, is_default: item.is_default }; formVisible.value = true
}

async function setDefault(id: number) {
  try {
    await setDefaultAIConfig(id)
    toast.show('已设为默认', 'success')
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '操作失败', 'error')
  }
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
  try {
    await deleteAIConfig(id)
    deleteTarget.value = null
    toast.show('已删除', 'info')
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '删除失败', 'error')
  }
}

onMounted(load)
</script>

<template>
  <section class="qp-page">
    <div class="qp-titlebar">
      <h1 class="qp-title">AI 配置</h1>
      <el-button size="small" type="primary" @click="openAdd">添加配置</el-button>
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
      <el-table-column label="JSON 模式" min-width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="row.response_format_type === 'json_schema' ? 'success' : 'info'">
            {{ row.response_format_type === 'json_schema' ? 'json_schema (严格)' : 'json_object (宽松)' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="API 地址" prop="api_base_url" min-width="200" show-overflow-tooltip />
      <el-table-column label="操作" width="220" align="right">
        <template #default="{ row }">
          <div class="qp-icon-actions">
            <el-tooltip content="测试连接" placement="top">
              <el-button size="small" class="qp-icon-button is-blue" :loading="testingId === row.id" @click="testConfig(row.id)">
                <Link v-if="testingId !== row.id" :size="16" />
              </el-button>
            </el-tooltip>

            <el-tooltip content="设为默认" placement="top">
              <el-button size="small" class="qp-icon-button is-amber" @click="setDefault(row.id)">
                <Star :size="16" :fill="row.is_default ? '#d97706' : 'none'" />
              </el-button>
            </el-tooltip>

            <el-tooltip content="编辑" placement="top">
              <el-button size="small" class="qp-icon-button" @click="openEdit(row)">
                <Pencil :size="16" />
              </el-button>
            </el-tooltip>

            <el-tooltip content="删除" placement="top">
              <el-button size="small" class="qp-icon-button is-red" @click="deleteTarget = row">
                <Trash2 :size="16" />
              </el-button>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <AIConfigDialog
      v-model="formVisible"
      :config-id="editingId"
      :initial-config="editingId ? form : null"
      @submitted="load"
    />

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
