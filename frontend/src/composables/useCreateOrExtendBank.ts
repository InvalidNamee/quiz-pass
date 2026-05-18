import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { AIProviderConfig, QuestionBank, QuestionBankTag } from '../api/types'

type CreateMode = 'ai_knowledge' | 'ai_parse' | 'json_import'

export function useCreateOrExtendBank() {
  const route = useRoute()
  const router = useRouter()

  const extendBankId = computed(() => route.params.bankId ? Number(route.params.bankId) : null)
  const isExtend = computed(() => Boolean(extendBankId.value))

  const createMode = ref<CreateMode>('ai_knowledge')
  const title = ref('')
  const description = ref('')
  const isPublic = ref(false)
  const aiProviderConfigId = ref('')
  const questionCountMode = ref('fixed')
  const questionCount = ref(10)
  const generateDescription = ref(false)
  const extraInstruction = ref('')
  const selectedTags = ref<QuestionBankTag[]>([])
  const file = ref<File | null>(null)
  const configs = ref<AIProviderConfig[]>([])
  const extendBank = ref<QuestionBank | null>(null)
  const submitting = ref(false)

  function reset() {
    title.value = ''
    extraInstruction.value = ''
    selectedTags.value = []
    file.value = null
  }

  return {
    extendBankId, isExtend, createMode, title, description, isPublic,
    aiProviderConfigId, questionCountMode, questionCount, generateDescription,
    extraInstruction, selectedTags, file, configs, extendBank, submitting,
    reset, router,
  }
}
