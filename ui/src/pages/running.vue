<script setup lang="ts">
import { computed } from 'vue';
import { RouterView, useRoute } from 'vue-router';

import SectionLayout from '@/components/SectionLayout.vue';

const route = useRoute();

// The run detail route (/running/:id) renders on its own — full width, its
// own two-column map/chart layout — like Strength's [id] routes. The section
// routes (Progress, Log) get SectionLayout's rail + shared page container so their
// <h1> lines up with every other top-level page.
const isDetail = computed(() => /^\/running\/\d+$/.test(route.path));

const sections = [
    { label: 'Progress', to: '/running/progress' },
    { label: 'Log', to: '/running/log' },
];
</script>

<template>
    <RouterView v-if="isDetail" />
    <SectionLayout v-else :sections="sections">
        <RouterView />
    </SectionLayout>
</template>
