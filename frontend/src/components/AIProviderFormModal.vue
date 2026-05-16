<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { AIProviderConfig } from '../api/client'
import AppModal from './AppModal.vue'
import AppButton from './AppButton.vue'

const props = defineProps<{
  modelValue: boolean
  editing: AIProviderConfig | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: [data: { name: string; api_base_url: string; api_key: string; model: string; is_default: boolean }]
}>()

const form = reactive({ name: '', api_base_url: '', api_key: '', model: '', is_default: false })

watch(() => props.modelValue, (open) => {
  if (open) {
    if (props.editing) {
      form.name = props.editing.name
      form.api_base_url = props.editing.api_base_url
      form.api_key = ''
      form.model = props.editing.model
      form.is_default = props.editing.is_default
    } else {
      form.name = ''
      form.api_base_url = ''
      form.api_key = ''
      form.model = ''
      form.is_default = false
    }
  }
})
</script>

<template>
  <AppModal :model-value="modelValue" :title="editing ? '编辑配置' : '添加配置'" max-width="max-w-lg" @update:model-value="emit('update:modelValue', $event)">
    <form class="grid gap-4" autocomplete="off" @submit.prevent="emit('save', { ...form })">
      <label class="grid gap-1">
        <span class="text-xs font-medium text-slate-500">配置名称</span>
        <input v-model="form.name" name="ai-name" class="rounded-input border border-slate-300 px-3 py-2 text-sm" placeholder="起个名字方便区分" autocomplete="off" />
      </label>
      <label class="grid gap-1">
        <span class="text-xs font-medium text-slate-500">接口地址</span>
        <input v-model="form.api_base_url" name="ai-url" class="rounded-input border border-slate-300 px-3 py-2 text-sm" placeholder="https://api.openai.com/v1" autocomplete="off" />
      </label>
      <label class="grid gap-1">
        <span class="text-xs font-medium text-slate-500">模型</span>
        <input v-model="form.model" name="ai-model" class="rounded-input border border-slate-300 px-3 py-2 text-sm" placeholder="如 gpt-4o" autocomplete="off" />
      </label>
      <label v-if="!editing" class="grid gap-1">
        <span class="text-xs font-medium text-slate-500">API Key</span>
        <input v-model="form.api_key" name="ai-key" class="rounded-input border border-slate-300 px-3 py-2 text-sm" type="password" placeholder="sk-..." autocomplete="new-password" />
        <span class="text-xs text-slate-400">保存后不可查看。</span>
      </label>
      <p v-else class="text-xs text-slate-400">API Key 保存后不可修改，如需更换请删除重建。</p>
      <label class="flex items-center gap-2 text-sm">
        <input v-model="form.is_default" type="checkbox" class="rounded" /> 设为默认
      </label>
    </form>
    <template #footer>
      <AppButton variant="ghost" @click="emit('update:modelValue', false)">取消</AppButton>
      <AppButton @click="emit('save', { ...form })">{{ editing ? '保存' : '添加' }}</AppButton>
    </template>
  </AppModal>
</template>
