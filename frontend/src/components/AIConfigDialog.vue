<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { createAIConfig, updateAIConfig } from '../api/v2/users'
import { useToast } from '../composables/useToast'

const props = defineProps<{
  modelValue: boolean
  configId?: number | null
  initialConfig?: {
    name: string
    api_base_url: string
    model: string
    response_format_type: 'json_object' | 'json_schema'
    is_default: boolean
  } | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submitted: []
}>()

const toast = useToast()
const submitting = ref(false)

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const isEdit = computed(() => Boolean(props.configId))

const form = ref({
  name: '',
  api_base_url: '',
  api_key: '',
  model: '',
  response_format_type: 'json_object' as 'json_object' | 'json_schema',
  is_default: false,
})

function reset() {
  if (isEdit.value && props.initialConfig) {
    form.value = {
      name: props.initialConfig.name,
      api_base_url: props.initialConfig.api_base_url,
      api_key: '',
      model: props.initialConfig.model,
      response_format_type: props.initialConfig.response_format_type,
      is_default: props.initialConfig.is_default,
    }
  } else {
    form.value = {
      name: '',
      api_base_url: '',
      api_key: '',
      model: '',
      response_format_type: 'json_object',
      is_default: false,
    }
  }
}

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
    if (isEdit.value && props.configId) {
      await updateAIConfig(props.configId, {
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
    visible.value = false
    emit('submitted')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    submitting.value = false
  }
}

watch(() => props.modelValue, (open) => {
  if (open) reset()
})
</script>

<template>
  <el-dialog v-model="visible" :title="isEdit ? '编辑配置' : '添加配置'" width="460px" class="!rounded-2xl shadow-xl">
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
    <template #footer>
      <el-button @click="visible = false" class="!rounded-xl !h-9">取消</el-button>
      <el-button type="primary" :loading="submitting" class="!rounded-xl shadow-sm !h-9" @click="handleSave">
        {{ isEdit ? '保存' : '添加' }}
      </el-button>
    </template>
  </el-dialog>
</template>
