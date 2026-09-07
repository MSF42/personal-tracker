<script setup lang="ts">
withDefaults(
    defineProps<{
        tiles: { label: string; value: string }[];
        /** Running's hero numbers get extra emphasis; other pages use 'lg'. */
        valueSize?: 'lg' | 'xl';
    }>(),
    { valueSize: 'lg' },
);
</script>

<template>
    <div class="grid grid-cols-3 gap-3">
        <div
            v-for="tile in tiles"
            :key="tile.label"
            class="border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800/60 rounded-lg border p-4"
        >
            <div
                class="text-surface-500 text-xs font-medium tracking-wide uppercase"
            >
                {{ tile.label }}
            </div>
            <div
                class="text-primary-600 dark:text-primary-400 mt-1 font-bold tabular-nums"
                :class="valueSize === 'xl' ? 'text-3xl' : 'text-2xl'"
            >
                {{ tile.value }}
            </div>
        </div>
    </div>
</template>
