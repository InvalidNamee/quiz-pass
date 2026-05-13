<script setup lang="ts">
import { useToast } from '../composables/useToast'
import AppToast from './AppToast.vue'

const { toasts } = useToast()
</script>

<template>
  <Teleport to="body">
    <TransitionGroup
      tag="div"
      name="toast"
      class="fixed right-4 top-4 z-[100] grid w-80 gap-2"
    >
      <AppToast v-for="toast in toasts" :key="toast.id" :toast="toast" />
    </TransitionGroup>
  </Teleport>
</template>
