<script setup lang="ts">
withDefaults(defineProps<{
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  size?: 'sm' | 'md'
}>(), {
  variant: 'default',
  size: 'sm',
})
</script>

<template>
  <span :class="[
    'inline-flex items-center rounded-full font-medium',
    size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
    {
      default: 'bg-slate-100 text-slate-700',
      success: 'bg-green-50 text-green-700',
      warning: 'bg-yellow-50 text-yellow-700',
      danger: 'bg-red-50 text-red-700',
      info: 'bg-blue-50 text-blue-700',
    }[variant],
  ]">
    <slot />
  </span>
</template>
