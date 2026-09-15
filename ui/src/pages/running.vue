<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';

const route = useRoute();

// The run detail route (/running/:id) renders on its own — full width, its
// own two-column map/chart layout — like Strength's [id] routes. The section
// routes (Progress, Log) get the left rail + shared page container so their
// <h1> lines up with every other top-level page.
const isDetail = computed(() => /^\/running\/\d+$/.test(route.path));

const sections = [
    { label: 'Progress', to: '/running/progress' },
    { label: 'Log', to: '/running/log' },
];

function railClass(to: string): string {
    return route.path === to || route.path.startsWith(to + '/')
        ? 'bg-primary-50 text-primary-600 dark:bg-primary-950 dark:text-primary-400'
        : 'text-surface-600 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800';
}
</script>

<template>
    <RouterView v-if="isDetail" />
    <div v-else class="mx-auto max-w-6xl p-6">
        <div class="flex gap-6">
            <nav class="flex w-32 shrink-0 flex-col gap-1">
                <RouterLink
                    v-for="section in sections"
                    :key="section.to"
                    class="rounded-md px-3 py-2 text-sm font-medium transition-colors"
                    :class="railClass(section.to)"
                    :to="section.to"
                >
                    {{ section.label }}
                </RouterLink>
            </nav>
            <div class="min-w-0 flex-1">
                <RouterView />
            </div>
        </div>
    </div>
</template>
