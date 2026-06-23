<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GenerateBankDialog from '../components/GenerateBankDialog.vue'
import { isUtilityWindowSupported } from '../features/utility-windows/utilityWindow'
import { openBankGenerateWindow } from '../features/utility-windows/openUtilityFlows'

const route = useRoute()
const router = useRouter()
const visible = ref(true)
const extendBankId = computed(() => route.params.bankId ? Number(route.params.bankId) : null)

function close() {
  if (extendBankId.value) router.replace(`/banks/${extendBankId.value}`)
  else router.replace('/banks')
}

onMounted(async () => {
  if (!isUtilityWindowSupported()) return
  await openBankGenerateWindow({ extendBankId: extendBankId.value }).catch(() => undefined)
  close()
})
</script>

<template>
  <section class="qp-page">
    <div class="qp-titlebar">
      <div>
        <h1 class="qp-title">新建题库</h1>
        <p class="qp-subtitle">此流程已改为弹窗；关闭后返回题库列表。</p>
      </div>
    </div>
    <GenerateBankDialog v-model="visible" :extend-bank-id="extendBankId" @update:model-value="(value: boolean) => { if (!value) close() }" />
  </section>
</template>
