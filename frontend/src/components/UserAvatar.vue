<script setup lang="ts">
const props = withDefaults(defineProps<{
  src?: string | null
  name?: string | null
  size?: number
}>(), {
  src: null,
  name: 'U',
  size: 34,
})

function fallback() {
  return (props.name || 'U').slice(0, 1).toUpperCase()
}
</script>

<template>
  <el-avatar
    :size="size"
    :src="src || undefined"
    class="border border-slate-300 bg-slate-100 !text-slate-700"
  >
    {{ fallback() }}
  </el-avatar>
</template>
