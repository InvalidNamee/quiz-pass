<script setup lang="ts">
import BankListView from '../components/BankListView.vue'
</script>

<template>
  <BankListView
    title="我的收藏"
    subtitle="收纳公开题库和你自己的私有题库。"
    endpoint="/api/v1/question-banks/favorites"
    show-author-filter
    show-visibility-filter
    show-generation-filter
  />
</template>
