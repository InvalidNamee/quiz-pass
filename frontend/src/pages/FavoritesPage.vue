<script setup lang="ts">
import BankListView from '../components/BankListView.vue'
</script>

<template>
  <BankListView
    title="我的收藏"
    subtitle="已收藏的题库。"
    scope="favorites"
    show-author-filter
    show-visibility-filter
    show-generation-filter
  />
</template>
