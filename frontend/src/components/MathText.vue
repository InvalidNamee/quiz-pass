<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { renderMathText } from '../utils/mathjax'

const props = withDefaults(defineProps<{
  text: string | null | undefined
  as?: string
}>(), {
  as: 'span',
})

const root = ref<HTMLElement | null>(null)
let renderVersion = 0

function waitForFrame() {
  return new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
}

async function renderMath() {
  const version = ++renderVersion
  await nextTick()
  if (!root.value || version !== renderVersion) return
  window.MathJax?.typesetClear?.([root.value])
  root.value.textContent = props.text || ''
  await waitForFrame()
  if (!root.value || version !== renderVersion) return
  await renderMathText(root.value, props.text || '')
}

onMounted(renderMath)
watch(() => [props.text, props.as], renderMath, { flush: 'post' })
onBeforeUnmount(() => {
  if (root.value) window.MathJax?.typesetClear?.([root.value])
})
</script>

<template>
  <component :is="as" ref="root" class="whitespace-pre-wrap" />
</template>
