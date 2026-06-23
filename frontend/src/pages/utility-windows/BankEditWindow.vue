<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { updateBank, getBank } from '../../api/v2/banks'
import { useAuthStore } from '../../stores/auth'
import { useToast } from '../../composables/useToast'
import { normalizeTagNames, tagKey, tagLabel, type TagInputValue } from '../../features/tags/tagUtils'
import { useUtilityWindowPage } from '../../features/utility-windows/useUtilityWindowPage'

type Payload = {
  bankId?: number
  requestId?: string
}

const auth = useAuthStore()
const toast = useToast()
const { payload, complete, closeWindow } = useUtilityWindowPage<Payload>('bank-edit')
const loading = ref(true)
const saving = ref(false)
const bankId = computed(() => Number(payload.value.bankId))
const editForm = ref({ title: '', description: '', visibility: 'private' })
const editTags = ref<TagInputValue[]>([])
const editIsPublic = computed({
  get: () => editForm.value.visibility === 'public',
  set: (value: boolean) => { editForm.value.visibility = value ? 'public' : 'private' },
})

async function load() {
  if (!bankId.value) return
  loading.value = true
  try {
    const bank = await getBank(bankId.value)
    editForm.value = {
      title: bank.title,
      description: bank.description || '',
      visibility: bank.visibility,
    }
    editTags.value = bank.tags || []
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '加载题库失败', 'error')
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!bankId.value) return
  if (!editForm.value.title.trim()) {
    toast.show('请输入题库名称', 'error')
    return
  }
  saving.value = true
  try {
    await updateBank(bankId.value, {
      title: editForm.value.title.trim(),
      description: editForm.value.description.trim(),
      visibility: editForm.value.visibility,
      tag_names: normalizeTagNames(editTags.value),
    })
    toast.show('题库已更新', 'success')
    await complete('bank-updated', { bankId: bankId.value })
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading" class="min-h-screen bg-white p-4 text-slate-700">
    <div class="space-y-4">
      <div>
        <h1 class="m-0 text-base font-semibold text-slate-900">编辑基本信息</h1>
        <p class="mt-1 text-sm text-slate-500">修改题库标题、描述和标签。</p>
      </div>

      <el-form label-position="top">
        <el-form-item label="题库名称">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="题库描述">
          <el-input v-model="editForm.description" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item v-if="auth.user?.role === 'admin'">
          <el-checkbox v-model="editIsPublic">公开此题库</el-checkbox>
        </el-form-item>
        <el-form-item label="题库标签">
          <div class="mb-2.5 flex flex-wrap gap-1.5">
            <el-tag
              v-for="(tag, index) in editTags"
              :key="tagKey(tag, index)"
              closable
              size="small"
              :disable-transitions="true"
              class="!rounded-md"
              @close="editTags.splice(index, 1)"
            >
              {{ tagLabel(tag) }}
            </el-tag>
          </div>
          <el-select v-model="editTags" multiple filterable allow-create default-first-option clearable placeholder="添加或创建标签" style="width: 100%">
            <el-option v-for="(tag, index) in editTags" :key="tagKey(tag, index)" :label="tagLabel(tag)" :value="tag" />
          </el-select>
        </el-form-item>
      </el-form>

      <div class="flex justify-end gap-2 pt-2">
        <el-button @click="closeWindow">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存修改</el-button>
      </div>
    </div>
  </section>
</template>
