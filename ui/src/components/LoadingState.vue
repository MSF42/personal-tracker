<script setup lang="ts">
withDefaults(defineProps<{ label?: string }>(), { label: 'Loading…' });
</script>

<template>
    <div
        class="text-surface-400 flex items-center justify-center gap-2 py-12 text-sm"
    >
        <i class="pi pi-spin pi-spinner"></i>
        {{ label }}
    </div>
</template>
