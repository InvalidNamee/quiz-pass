<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PracticeSetupDialog from '../components/PracticeSetupDialog.vue'
import { getBank } from '../api/v2/banks'
import { isUtilityWindowSupported } from '../features/utility-windows/utilityWindow'
import { openPracticeSetupWindow } from '../features/utility-windows/openUtilityFlows'

const route = useRoute()
const router = useRouter()
const visible = ref(true)
const bankId = computed(() => Number(route.params.bankId))

function close() {
  router.replace(`/banks/${bankId.value}`)
}

onMounted(async () => {
  if (!isUtilityWindowSupported()) return
  const bank = await getBank(bankId.value).catch(() => null)
  if (bank) await openPracticeSetupWindow({ bank }).catch(() => undefined)
  close()
})
</script>

<template>
  <section class="qp-page">
    <div class="qp-titlebar">
      <div>
        <h1 class="qp-title">开始练习</h1>
        <p class="qp-subtitle">此流程已改为弹窗；关闭后返回题库详情。</p>
      </div>
    </div>
    <PracticeSetupDialog v-model="visible" :bank-id="bankId" @update:model-value="(value: boolean) => { if (!value) close() }" />
  </section>
</template>
