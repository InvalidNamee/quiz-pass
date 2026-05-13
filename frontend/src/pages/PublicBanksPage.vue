<script setup lang="ts">
import BankListView from '../components/BankListView.vue'
</script>

<template>
  <BankListView
    title="公开题库"
    subtitle="浏览大家公开分享的题库，按关键词或作者快速定位。"
    endpoint="/api/v1/question-banks/public"
    show-author-filter
  />
</template>
