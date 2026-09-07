<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';

import CommandPalette from '@/components/CommandPalette.vue';
import { useSettingsApi } from '@/composables/api/useSettingsApi';
import { useBackup } from '@/composables/useBackup';
import { useUiState } from '@/composables/useUiState';
import { useUnits } from '@/composables/useUnits';
import { useUserProfile } from '@/composables/useUserProfile';

const route = useRoute();
const router = useRouter();
const { getSetting, setSetting } = useSettingsApi();
const ui = useUiState();

const restoreFileInput = ref<HTMLInputElement | null>(null);

const {
    restoreConfirmText,
    showRestoreDialog,
    backingUp,
    restoring,
    downloadBackup,
    onRestoreFileSelected,
    confirmRestore,
} = useBackup();

function triggerRestoreUpload() {
    restoreFileInput.value?.click();
}

const { profilePicture, userName, loadProfile } = useUserProfile();
const {
    weightUnit,
    distanceUnit,
    temperatureUnit,
    setWeightUnit,
    setDistanceUnit,
    setTemperatureUnit,
    loadUnits,
} = useUnits();
const weightOptions = ['kg', 'lbs'];
const distanceOptions = ['km', 'mi'];
const temperatureOptions = [
    { label: '°C', value: 'c' },
    { label: '°F', value: 'f' },
];

const theme = ref('dark');
const themeOptions = ['light', 'dark'];
const popover = ref();

const navItems = [
    { label: 'Home', to: '/', icon: 'pi pi-home' },
    { label: 'Tasks', to: '/tasks', icon: 'pi pi-check-square' },
    { label: 'Habits', to: '/habits', icon: 'pi pi-check-circle' },
    { label: 'Running', to: '/running', icon: 'pi pi-bolt' },
    { label: 'Strength', to: '/strength', icon: 'pi pi-heart' },
    { label: 'Measurements', to: '/measurements', icon: 'pi pi-chart-line' },
];

onMounted(async () => {
    const themeRes = await getSetting('theme');
    if (themeRes.success && themeRes.data?.value) {
        theme.value = themeRes.data.value;
    }
    if (theme.value === 'light') {
        document.documentElement.classList.remove('dark');
    } else {
        document.documentElement.classList.add('dark');
    }
    await Promise.all([loadProfile(), loadUnits()]);
    window.addEventListener('keydown', onGlobalKeydown);
});

onUnmounted(() => {
    window.removeEventListener('keydown', onGlobalKeydown);
});

function onGlobalKeydown(e: KeyboardEvent) {
    const isMod = e.metaKey || e.ctrlKey;
    const target = e.target as HTMLElement | null;
    const inField =
        !!target &&
        (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA');

    // Cmd/Ctrl+K opens the palette. Intercept even when focused inside a
    // textarea so the outliner shortcut is always reachable.
    if (isMod && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        ui.openPalette();
        return;
    }
    // Cmd/Ctrl+. toggles focus mode from anywhere.
    if (isMod && e.key === '.') {
        e.preventDefault();
        ui.toggleFocusMode();
        return;
    }
    // Escape exits focus mode only when not editing text (so the outliner's
    // own escape handling keeps working).
    if (e.key === 'Escape' && ui.focusMode.value && !inField) {
        ui.exitFocusMode();
    }
}

function toggleMenu(event: Event) {
    popover.value.toggle(event);
}

async function onThemeChange(value: string) {
    theme.value = value;
    if (value === 'light') {
        document.documentElement.classList.remove('dark');
    } else {
        document.documentElement.classList.add('dark');
    }
    await setSetting('theme', value);
}

function goToSettings() {
    popover.value.hide();
    router.push('/settings');
}
</script>

<template>
    <AppToast
        position="top-center"
        style="margin-top: env(safe-area-inset-top, 0px)"
    />
    <nav
        v-show="!ui.focusMode.value"
        class="border-surface-200 bg-surface-0 dark:border-surface-700 dark:bg-surface-900 sticky top-0 z-50 border-b px-4 pb-3"
        style="padding-top: calc(env(safe-area-inset-top, 0px) + 0.75rem)"
    >
        <div class="mx-auto flex max-w-6xl items-center gap-2">
            <div class="flex flex-1 gap-1 overflow-x-auto">
                <RouterLink
                    v-for="item in navItems"
                    :key="item.to"
                    class="flex shrink-0 items-center gap-1.5 rounded-md px-2 py-2 text-sm font-medium transition-colors sm:px-3"
                    :class="
                        route.path === item.to ||
                        (item.to !== '/' &&
                            route.path.startsWith(item.to + '/'))
                            ? 'bg-primary-50 text-primary-600 dark:bg-primary-950 dark:text-primary-400'
                            : 'text-surface-600 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800'
                    "
                    :title="item.label"
                    :to="item.to"
                >
                    <i class="text-base" :class="item.icon"></i>
                    <span class="hidden sm:inline">{{ item.label }}</span>
                </RouterLink>
            </div>
            <button
                aria-label="Open command palette"
                class="text-surface-400 hover:text-primary-500 mx-1 hidden cursor-pointer text-[10px] tracking-widest uppercase md:inline"
                title="Command palette (⌘K)"
                @click="ui.openPalette()"
            >
                ⌘K
            </button>
            <button
                aria-label="Open settings menu"
                class="text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-surface-100 ml-auto flex shrink-0 cursor-pointer items-center gap-2 transition-colors"
                @click="toggleMenu"
            >
                <template v-if="profilePicture || userName">
                    <img
                        v-if="profilePicture"
                        alt="Profile"
                        class="h-7 w-7 rounded-full object-cover"
                        :src="profilePicture"
                    />
                    <div
                        v-else-if="userName"
                        class="bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                    >
                        {{ userName.charAt(0).toUpperCase() }}
                    </div>
                    <span v-if="userName" class="text-sm font-medium">{{
                        userName
                    }}</span>
                </template>
                <i v-else class="pi pi-cog text-lg"></i>
            </button>
            <AppPopover ref="popover">
                <div class="flex w-[22rem] max-w-[92vw] flex-col gap-4 p-2">
                    <!-- Appearance -->
                    <div>
                        <h3
                            class="text-surface-500 dark:text-surface-400 mb-2 text-xs font-semibold tracking-wide uppercase"
                        >
                            Appearance
                        </h3>
                        <AppSelectButton
                            :model-value="theme"
                            :options="themeOptions"
                            @update:model-value="onThemeChange"
                        />
                    </div>

                    <!-- Units -->
                    <div>
                        <h3
                            class="text-surface-500 dark:text-surface-400 mb-2 text-xs font-semibold tracking-wide uppercase"
                        >
                            Units
                        </h3>
                        <div class="flex flex-wrap items-center gap-2">
                            <AppSelectButton
                                :allow-empty="false"
                                aria-label="Weight unit"
                                :model-value="weightUnit"
                                :options="weightOptions"
                                size="small"
                                @update:model-value="setWeightUnit"
                            />
                            <AppSelectButton
                                :allow-empty="false"
                                aria-label="Distance unit"
                                :model-value="distanceUnit"
                                :options="distanceOptions"
                                size="small"
                                @update:model-value="setDistanceUnit"
                            />
                            <AppSelectButton
                                :allow-empty="false"
                                aria-label="Temperature unit"
                                :model-value="temperatureUnit"
                                option-label="label"
                                option-value="value"
                                :options="temperatureOptions"
                                size="small"
                                @update:model-value="setTemperatureUnit"
                            />
                        </div>
                    </div>

                    <!-- Data Management -->
                    <div>
                        <h3
                            class="text-surface-500 dark:text-surface-400 mb-2 text-xs font-semibold tracking-wide uppercase"
                        >
                            Data Management
                        </h3>
                        <div class="flex flex-col gap-1.5">
                            <AppButton
                                icon="pi pi-download"
                                label="Download Backup"
                                :loading="backingUp"
                                severity="secondary"
                                size="small"
                                @click="downloadBackup"
                            />
                            <input
                                ref="restoreFileInput"
                                accept=".zip"
                                class="hidden"
                                type="file"
                                @change="onRestoreFileSelected"
                            />
                            <AppButton
                                icon="pi pi-upload"
                                label="Restore from Backup"
                                severity="secondary"
                                size="small"
                                @click="triggerRestoreUpload"
                            />
                        </div>
                    </div>

                    <!-- Divider -->
                    <div
                        class="border-surface-200 dark:border-surface-700 border-t"
                    ></div>

                    <!-- Settings Link -->
                    <button
                        class="text-surface-600 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800 flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors"
                        @click="goToSettings"
                    >
                        <i class="pi pi-cog text-xs"></i>
                        Settings
                    </button>
                </div>
            </AppPopover>
        </div>
    </nav>

    <!-- Restore Confirmation Dialog -->
    <AppDialog
        v-model:visible="showRestoreDialog"
        header="Restore from Backup"
        :modal="true"
        :style="{ width: '28rem' }"
    >
        <p class="text-surface-600 dark:text-surface-400 mb-4 text-sm">
            This will replace all current data with the backup. This action
            cannot be undone. Type <strong>RESTORE</strong> to confirm.
        </p>
        <AppInputText
            v-model="restoreConfirmText"
            class="mb-4 w-full"
            placeholder="Type RESTORE to confirm"
            @keydown.enter="confirmRestore"
        />
        <div class="flex justify-end gap-2">
            <AppButton
                label="Cancel"
                severity="secondary"
                @click="showRestoreDialog = false"
            />
            <AppButton
                :disabled="restoreConfirmText !== 'RESTORE'"
                label="Restore"
                :loading="restoring"
                severity="warn"
                @click="confirmRestore"
            />
        </div>
    </AppDialog>

    <div
        class="min-h-0 flex-1"
        style="padding-bottom: env(safe-area-inset-bottom, 0px)"
    >
        <RouterView />
    </div>

    <!-- Mounted once globally; visibility is driven by useUiState. -->
    <CommandPalette />

    <!-- Focus-mode exit hint, since the nav is hidden in that state. -->
    <button
        v-if="ui.focusMode.value"
        class="text-surface-400 hover:text-primary-500 fixed top-3 right-3 z-40 text-[10px] tracking-widest uppercase"
        title="Exit focus mode (Esc)"
        @click="ui.exitFocusMode()"
    >
        exit focus
    </button>
</template>
