import { ref } from 'vue';

import { useSettingsApi } from '@/composables/api/useSettingsApi';
import { useToast } from '@/composables/useToast';

export function useBackup() {
    const { backup, restore } = useSettingsApi();
    const toast = useToast();

    const restoreFile = ref<File | null>(null);
    const restoreConfirmText = ref('');
    const showRestoreDialog = ref(false);
    const backingUp = ref(false);
    const restoring = ref(false);

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
        if (restoreConfirmText.value !== 'RESTORE' || !restoreFile.value)
            return;
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

    return {
        restoreFile,
        restoreConfirmText,
        showRestoreDialog,
        backingUp,
        restoring,
        downloadBackup,
        onRestoreFileSelected,
        confirmRestore,
    };
}
