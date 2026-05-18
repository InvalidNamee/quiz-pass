<script setup lang="ts">
import BankListView from '../components/BankListView.vue'
</script>

<template>
  <BankListView
    title="公开题库"
    subtitle="浏览社区分享的题库。"
    scope="public"
    show-author-filter
  />
</template>
