<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';

import { useSettingsApi } from '@/composables/api/useSettingsApi';
import { useToast } from '@/composables/useToast';

const route = useRoute();
const router = useRouter();
const { getSetting, setSetting, backup, restore } = useSettingsApi();
const toast = useToast();

const profilePicture = ref<string | null>(null);
const userName = ref<string | null>(null);
const theme = ref('dark');
const themeOptions = ['light', 'dark'];
const backingUp = ref(false);
const restoreFileInput = ref<HTMLInputElement | null>(null);
const restoreFile = ref<File | null>(null);
const restoreConfirmText = ref('');
const showRestoreDialog = ref(false);
const restoring = ref(false);
const popover = ref();

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
    { label: 'Notes', to: '/notes', icon: 'pi pi-file-edit' },
    {
        label: 'Measurements',
        to: '/measurements',
        icon: 'pi pi-chart-line',
    },
];

onMounted(async () => {
    const [profileRes, themeRes, nameRes] = await Promise.all([
        getSetting('profile_picture'),
        getSetting('theme'),
        getSetting('user_name'),
    ]);
    if (profileRes.success && profileRes.data?.value) {
        profilePicture.value = profileRes.data.value;
    }
    if (nameRes.success && nameRes.data?.value) {
        userName.value = nameRes.data.value;
    }
    if (themeRes.success && themeRes.data?.value) {
        theme.value = themeRes.data.value;
    }
    if (theme.value === 'light') {
        document.documentElement.classList.remove('dark');
    } else {
        document.documentElement.classList.add('dark');
    }
});

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

async function downloadBackup() {
    backingUp.value = true;
    try {
        await backup();
        toast.showSuccess('Backup downloaded');
    } catch {
        toast.showError('Failed to download backup');
    } finally {
        backingUp.value = false;
    }
}

function triggerRestoreUpload() {
    restoreFileInput.value?.click();
}

function onRestoreFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    restoreFile.value = file;
    restoreConfirmText.value = '';
    showRestoreDialog.value = true;
    input.value = '';
}

async function confirmRestore() {
    if (restoreConfirmText.value !== 'RESTORE' || !restoreFile.value) return;
    restoring.value = true;
    const res = await restore(restoreFile.value);
    restoring.value = false;
    if (res.success) {
        showRestoreDialog.value = false;
        toast.showSuccess('Backup restored successfully');
        window.location.reload();
    } else {
        toast.showError(res.error);
    }
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
                        route.path === item.to
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
                class="text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-surface-100 ml-auto flex shrink-0 cursor-pointer items-center gap-2 transition-colors"
                @click="toggleMenu"
            >
                <template v-if="profilePicture || userName">
                    <img
                        v-if="profilePicture"
                        alt="Profile"
                        class="h-8 w-8 rounded-full object-cover"
                        :src="profilePicture"
                    />
                    <span v-if="userName" class="text-sm font-medium">
                        {{ userName }}
                    </span>
                </template>
                <i v-else class="pi pi-cog text-lg"></i>
            </button>
            <AppPopover ref="popover">
                <div class="flex w-64 flex-col gap-4 p-2">
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

    <div style="padding-bottom: env(safe-area-inset-bottom, 0px)">
        <RouterView />
    </div>
</template>
