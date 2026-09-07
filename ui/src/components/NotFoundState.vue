<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
    /** Lowercase noun for the missing entity, e.g. "run", "workout log". */
    entity: string;
    backTo: string;
    /** Link text, e.g. "Back to Running". */
    backLabel: string;
}>();

// Only the first letter needs capitalizing for the heading ("Workout log not
// found", not "Workout Log Not Found") — CSS `capitalize` title-cases every
// word, which isn't what multi-word entities like "workout log" want.
const heading = computed(
    () => props.entity.charAt(0).toUpperCase() + props.entity.slice(1),
);
</script>

<template>
    <div class="flex flex-col gap-3">
        <h1 class="text-2xl font-bold">{{ heading }} not found</h1>
        <p class="text-surface-500 text-sm">
            This {{ entity }} may have been deleted.
            <RouterLink
                class="text-primary-600 dark:text-primary-400"
                :to="backTo"
            >
                {{ backLabel }}
            </RouterLink>
        </p>
    </div>
</template>
