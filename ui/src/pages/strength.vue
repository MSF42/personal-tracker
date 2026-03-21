<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import ExercisesPage from './exercises.vue';
import WorkoutLogsPage from './workout-logs.vue';
import WorkoutRoutinesPage from './workout-routines.vue';

const route = useRoute();
const router = useRouter();

const validTabs = ['exercises', 'routines', 'logs'];
const initialTab = validTabs.includes(route.query.tab as string)
    ? (route.query.tab as string)
    : 'exercises';

const activeTab = ref(initialTab);

// Lazy-mount: only render a tab's content after it's been first activated
const mounted = reactive({
    exercises: initialTab === 'exercises',
    routines: initialTab === 'routines',
    logs: initialTab === 'logs',
});

onMounted(() => {
    mounted[initialTab as keyof typeof mounted] = true;
});

function onTabChange(val: string | number) {
    const tab = val as string;
    mounted[tab as keyof typeof mounted] = true;
    router.replace({ query: { ...route.query, tab } });
}
</script>

<template>
    <AppTabs v-model:value="activeTab" @update:value="onTabChange">
        <AppTabList>
            <AppTab value="exercises">Exercises</AppTab>
            <AppTab value="routines">Routines</AppTab>
            <AppTab value="logs">Logs</AppTab>
        </AppTabList>
        <AppTabPanels class="!p-0">
            <AppTabPanel class="!p-0" value="exercises">
                <ExercisesPage v-if="mounted.exercises" />
            </AppTabPanel>
            <AppTabPanel class="!p-0" value="routines">
                <WorkoutRoutinesPage v-if="mounted.routines" />
            </AppTabPanel>
            <AppTabPanel class="!p-0" value="logs">
                <WorkoutLogsPage v-if="mounted.logs" />
            </AppTabPanel>
        </AppTabPanels>
    </AppTabs>
</template>
