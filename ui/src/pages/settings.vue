<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { useSettingsApi } from '@/composables/api/useSettingsApi';
import { useToast } from '@/composables/useToast';

const { getSetting, setSetting, deleteSetting, resetAllData } =
    useSettingsApi();
const toast = useToast();

const profilePicture = ref<string | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const confirmText = ref('');
const showResetDialog = ref(false);
const resetting = ref(false);

onMounted(async () => {
    const res = await getSetting('profile_picture');
    if (res.success && res.data?.value) {
        profilePicture.value = res.data.value;
    }
});

function triggerUpload() {
    fileInput.value?.click();
}

function onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async () => {
        const dataUrl = reader.result as string;
        const res = await setSetting('profile_picture', dataUrl);
        if (res.success) {
            profilePicture.value = dataUrl;
            toast.showSuccess('Profile picture updated');
        }
    };
    reader.readAsDataURL(file);
    input.value = '';
}

async function removePicture() {
    const res = await deleteSetting('profile_picture');
    if (res.success) {
        profilePicture.value = null;
        toast.showSuccess('Profile picture removed');
    }
}

function openResetDialog() {
    confirmText.value = '';
    showResetDialog.value = true;
}

async function confirmReset() {
    if (confirmText.value !== 'DELETE') return;
    resetting.value = true;
    const res = await resetAllData();
    resetting.value = false;
    if (res.success) {
        showResetDialog.value = false;
        toast.showSuccess('All data has been deleted');
        window.location.reload();
    }
}
</script>

<template>
    <main class="mx-auto max-w-3xl px-6 py-8">
        <h1
            class="text-surface-900 dark:text-surface-0 mb-8 text-2xl font-bold"
        >
            Settings
        </h1>

        <!-- Profile Picture -->
        <section
            class="border-surface-200 dark:border-surface-700 mb-8 rounded-lg border p-6"
        >
            <h2
                class="text-surface-800 dark:text-surface-100 mb-4 text-lg font-semibold"
            >
                Profile Picture
            </h2>
            <div class="flex items-center gap-6">
                <div
                    class="bg-surface-100 dark:bg-surface-800 flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-full"
                >
                    <img
                        v-if="profilePicture"
                        alt="Profile"
                        class="h-full w-full object-cover"
                        :src="profilePicture"
                    />
                    <i v-else class="pi pi-user text-surface-400 text-3xl"></i>
                </div>
                <div class="flex flex-col gap-2">
                    <input
                        ref="fileInput"
                        accept="image/*"
                        class="hidden"
                        type="file"
                        @change="onFileSelected"
                    />
                    <AppButton
                        icon="pi pi-upload"
                        label="Upload"
                        size="small"
                        @click="triggerUpload"
                    />
                    <AppButton
                        v-if="profilePicture"
                        icon="pi pi-trash"
                        label="Remove"
                        severity="secondary"
                        size="small"
                        @click="removePicture"
                    />
                </div>
            </div>
        </section>

        <!-- Danger Zone -->
        <section
            class="rounded-lg border border-red-300 p-6 dark:border-red-800"
        >
            <h2
                class="mb-2 text-lg font-semibold text-red-600 dark:text-red-400"
            >
                Danger Zone
            </h2>
            <p class="text-surface-600 dark:text-surface-400 mb-4 text-sm">
                Permanently delete all data including tasks, running activities,
                exercises, routines, workout logs, and settings.
            </p>
            <AppButton
                icon="pi pi-trash"
                label="Delete All Data"
                severity="danger"
                @click="openResetDialog"
            />
        </section>

        <!-- Confirmation Dialog -->
        <AppDialog
            v-model:visible="showResetDialog"
            header="Delete All Data"
            :modal="true"
            :style="{ width: '28rem' }"
        >
            <p class="text-surface-600 dark:text-surface-400 mb-4 text-sm">
                This action cannot be undone. Type
                <strong>DELETE</strong> to confirm.
            </p>
            <AppInputText
                v-model="confirmText"
                class="mb-4 w-full"
                placeholder="Type DELETE to confirm"
                @keydown.enter="confirmReset"
            />
            <div class="flex justify-end gap-2">
                <AppButton
                    label="Cancel"
                    severity="secondary"
                    @click="showResetDialog = false"
                />
                <AppButton
                    :disabled="confirmText !== 'DELETE'"
                    label="Delete Everything"
                    :loading="resetting"
                    severity="danger"
                    @click="confirmReset"
                />
            </div>
        </AppDialog>
    </main>
</template>
