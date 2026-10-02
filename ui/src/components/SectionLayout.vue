<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router';

// Shared shell for sections with sub-pages (Running, Strength): a left rail of
// section links beside the page on desktop, collapsing to a horizontal tab row
// above it on narrow screens so the content keeps the full width.
defineProps<{ sections: { label: string; to: string }[] }>();

const route = useRoute();

function linkClass(to: string): string {
    return route.path === to || route.path.startsWith(to + '/')
        ? 'bg-primary-50 text-primary-600 dark:bg-primary-950 dark:text-primary-400'
        : 'text-surface-600 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800';
}
</script>

<template>
    <div class="mx-auto max-w-6xl p-4 md:p-6">
        <div class="flex flex-col gap-4 md:flex-row md:gap-6">
            <nav
                class="flex shrink-0 gap-1 overflow-x-auto md:w-32 md:flex-col"
            >
                <RouterLink
                    v-for="section in sections"
                    :key="section.to"
                    class="rounded-md px-3 py-2 text-sm font-medium whitespace-nowrap transition-colors"
                    :class="linkClass(section.to)"
                    :to="section.to"
                >
                    {{ section.label }}
                </RouterLink>
            </nav>
            <div class="min-w-0 flex-1">
                <slot />
            </div>
        </div>
    </div>
</template>
