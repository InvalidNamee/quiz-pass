<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { typesetMath } from '../utils/mathjax'

const props = withDefaults(defineProps<{
  text: string | null | undefined
  as?: string
}>(), {
  as: 'span',
})

const root = ref<HTMLElement | null>(null)

async function renderMath() {
  await nextTick()
  if (!root.value) return
  root.value.textContent = props.text || ''
  await typesetMath(root.value)
}

onMounted(renderMath)
watch(() => props.text, renderMath)
onBeforeUnmount(() => {
  if (root.value) window.MathJax?.typesetClear?.([root.value])
})
</script>

<template>
  <component :is="as" ref="root" class="whitespace-pre-wrap" />
</template>
