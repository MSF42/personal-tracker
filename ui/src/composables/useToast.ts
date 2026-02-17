import { useToast as usePrimeToast } from 'primevue/usetoast';

import type { ApiError } from '@/types/ApiResponse';

export function useToast() {
    const toast = usePrimeToast();

    const showSuccess = (summary: string, detail?: string) => {
        toast.add({
            severity: 'success',
            summary,
            detail,
            life: 3000,
        });
    };

    const showError = (summary: string, detail?: string) => {
        toast.add({
            severity: 'error',
            summary,
            detail,
            life: 5000,
        });
    };

    const showApiError = (error: ApiError) => {
        toast.add({
            severity: 'error',
            summary: 'Error',
            detail: error.message,
            life: 5000,
        });
    };

    const showWarning = (summary: string, detail?: string) => {
        toast.add({
            severity: 'warn',
            summary,
            detail,
            life: 4000,
        });
    };

    const showInfo = (summary: string, detail?: string) => {
        toast.add({
            severity: 'info',
            summary,
            detail,
            life: 3000,
        });
    };

    return { showSuccess, showError, showApiError, showWarning, showInfo };
}
