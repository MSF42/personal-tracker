<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';

import { useSettingsApi } from '@/composables/api/useSettingsApi';

const route = useRoute();
const { getSetting } = useSettingsApi();

const profilePicture = ref<string | null>(null);

const navItems = [
    { label: 'Home', to: '/', icon: 'pi pi-home' },
    { label: 'Tasks', to: '/tasks', icon: 'pi pi-check-square' },
    { label: 'Running', to: '/running', icon: 'pi pi-bolt' },
    { label: 'Exercises', to: '/exercises', icon: 'pi pi-heart' },
    {
        label: 'Routines',
        to: '/workout-routines',
        icon: 'pi pi-list',
    },
    { label: 'Logs', to: '/workout-logs', icon: 'pi pi-history' },
    { label: 'Settings', to: '/settings', icon: 'pi pi-cog' },
];

onMounted(async () => {
    const res = await getSetting('profile_picture');
    if (res.success && res.data?.value) {
        profilePicture.value = res.data.value;
    }
});
</script>

<template>
    <AppToast />
    <nav
        class="border-surface-200 bg-surface-0 dark:border-surface-700 dark:bg-surface-900 border-b px-6 py-3"
    >
        <div class="mx-auto flex max-w-6xl items-center gap-6">
            <RouterLink class="shrink-0" to="/settings">
                <img
                    v-if="profilePicture"
                    alt="Profile"
                    class="h-8 w-8 rounded-full object-cover"
                    :src="profilePicture"
                />
                <span v-else class="text-primary-500 text-lg font-bold"
                    >PT</span
                >
            </RouterLink>
            <div class="flex gap-1">
                <RouterLink
                    v-for="item in navItems"
                    :key="item.to"
                    class="flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors"
                    :class="
                        route.path === item.to
                            ? 'bg-primary-50 text-primary-600 dark:bg-primary-950 dark:text-primary-400'
                            : 'text-surface-600 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800'
                    "
                    :to="item.to"
                >
                    <i class="text-xs" :class="item.icon"></i>
                    {{ item.label }}
                </RouterLink>
            </div>
        </div>
    </nav>
    <RouterView />
</template>
