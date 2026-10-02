<script setup lang="ts">
import { computed } from 'vue';
import { RouterView, useRoute } from 'vue-router';

import SectionLayout from '@/components/SectionLayout.vue';

const route = useRoute();

// Detail routes (/strength/logs/:id, /strength/routines/:id) render on their
// own — full width, their own container and Back button, like the run detail
// page. The section routes get SectionLayout's rail + shared page container so their
// <h1> lines up with every other top-level page.
const isDetail = computed(() =>
    /^\/strength\/(logs|routines)\/.+/.test(route.path),
);

const sections = [
    { label: 'Logs', to: '/strength/logs' },
    { label: 'Exercises', to: '/strength/exercises' },
    { label: 'Routines', to: '/strength/routines' },
];
</script>

<template>
    <RouterView v-if="isDetail" />
    <SectionLayout v-else :sections="sections">
        <RouterView />
    </SectionLayout>
</template>
