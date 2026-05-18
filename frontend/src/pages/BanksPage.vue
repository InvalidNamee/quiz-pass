<script setup lang="ts">
import BankListView from '../components/BankListView.vue'
</script>

<template>
  <BankListView
    title="我的题库"
    subtitle="管理你创建的题库。"
    scope="mine"
    allow-create
    show-visibility-filter
    show-generation-filter
  />
</template>
