<script setup lang="ts">
import { computed, ref } from 'vue'
import { createAIConfig, updateAIConfig } from '../../api/v2/users'
import { useToast } from '../../composables/useToast'
import { useUtilityWindowPage } from '../../features/utility-windows/useUtilityWindowPage'

type ConfigSnapshot = {
  name: string
  api_base_url: string
  model: string
  response_format_type: 'json_object' | 'json_schema'
  is_default: boolean
}
type Payload = {
  configId?: number | null
  initialConfig?: ConfigSnapshot | null
  requestId?: string
}

const toast = useToast()
const { payload, complete, closeWindow } = useUtilityWindowPage<Payload>('ai-config')
const submitting = ref(false)
const isEdit = computed(() => Boolean(payload.value.configId))
const initialConfig = computed(() => payload.value.initialConfig || null)
const form = ref({
  name: initialConfig.value?.name || '',
  api_base_url: initialConfig.value?.api_base_url || '',
  api_key: '',
  model: initialConfig.value?.model || '',
  response_format_type: initialConfig.value?.response_format_type || 'json_object' as 'json_object' | 'json_schema',
  is_default: initialConfig.value?.is_default || false,
})

async function handleSave() {
  if (!form.value.model.trim()) {
    toast.show('请输入模型名称', 'error')
    return
  }
  if (!form.value.api_base_url.trim()) {
    toast.show('请输入接口地址', 'error')
    return
  }
  if (!isEdit.value && !form.value.api_key.trim()) {
    toast.show('请输入 API Key', 'error')
    return
  }
  submitting.value = true
  try {
    if (isEdit.value && payload.value.configId) {
      await updateAIConfig(payload.value.configId, {
        name: form.value.name.trim(),
        api_base_url: form.value.api_base_url.trim(),
        model: form.value.model.trim(),
        response_format_type: form.value.response_format_type,
        is_default: form.value.is_default,
      })
      toast.show('已更新', 'success')
    } else {
      await createAIConfig({
        ...form.value,
        name: form.value.name.trim(),
        api_base_url: form.value.api_base_url.trim(),
        api_key: form.value.api_key.trim(),
        model: form.value.model.trim(),
      })
      toast.show('已添加', 'success')
    }
    await complete('ai-config-saved')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '保存失败', 'error')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="min-h-screen bg-white p-4 text-slate-700">
    <div class="space-y-4">
      <div>
        <h1 class="m-0 text-base font-semibold text-slate-900">{{ isEdit ? '编辑配置' : '添加配置' }}</h1>
        <p class="mt-1 text-sm text-slate-500">配置 OpenAI 兼容模型，用于 AI 生成题库。</p>
      </div>

      <el-form label-position="top" size="default">
        <el-form-item label="配置名称">
          <el-input v-model="form.name" placeholder="输入配置名称（可选）" autocomplete="off" />
        </el-form-item>
        <el-form-item label="接口地址">
          <el-input v-model="form.api_base_url" placeholder="https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item label="模型">
          <el-input v-model="form.model" placeholder="gpt-4o" />
        </el-form-item>
        <el-form-item label="JSON 模式">
          <el-radio-group v-model="form.response_format_type">
            <el-radio-button value="json_object">json_object (宽松)</el-radio-button>
            <el-radio-button value="json_schema">json_schema (严格)</el-radio-button>
          </el-radio-group>
          <div class="mt-1 text-xs text-slate-400">模型不支持 json_schema 时请选择 json_object。</div>
        </el-form-item>
        <el-form-item v-if="!isEdit" label="API Key">
          <el-input
            v-model="form.api_key"
            autocomplete="off"
            name="qp-ai-provider-key"
            placeholder="请输入 API Key"
            type="text"
            spellcheck="false"
            data-lpignore="true"
            data-1p-ignore="true"
            data-form-type="other"
          />
          <span class="text-xs text-slate-400">保存后不可查看、不可编辑，只能删除重建</span>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.is_default">设为默认</el-checkbox>
        </el-form-item>
      </el-form>

      <div class="flex justify-end gap-2 pt-2">
        <el-button @click="closeWindow">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSave">{{ isEdit ? '保存' : '添加' }}</el-button>
      </div>
    </div>
  </section>
</template>
