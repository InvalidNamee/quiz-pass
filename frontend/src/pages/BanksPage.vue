<script setup lang="ts">
import BankListView from '../components/BankListView.vue'
</script>

<template>
  <BankListView
    title="我的题库"
    subtitle="管理你创建、生成或导入的题库。"
    endpoint="/api/v1/question-banks"
    primary-label="新建题库"
    primary-to="/banks/generate"
    show-visibility-filter
    show-generation-filter
  />
</template>
