<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  src?: string | null
  alt?: string
  username?: string | null
  size?: 'sm' | 'md' | 'lg'
}>(), {
  size: 'md',
})

const sizeClass = computed(() => ({
  sm: 'h-7 w-7 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-12 w-12 text-base',
}[props.size]))

const initial = computed(() => (props.username || 'U').slice(0, 1).toUpperCase())
</script>

<template>
  <img v-if="src" :src="src" :alt="alt || ''" :class="[sizeClass, 'rounded-full object-cover']" />
  <span v-else :class="[sizeClass, 'grid place-items-center rounded-full bg-slate-800 font-bold text-white']">
    {{ initial }}
  </span>
</template>
