import { useApi } from './useApi';

interface SettingResponse {
    key: string;
    value: string | null;
}

export function useSettingsApi() {
    const api = useApi();

    const getSetting = async (key: string) =>
        api.getData<SettingResponse>(`settings/${key}`);

    const setSetting = async (key: string, value: string) =>
        api.put<{ value: string }, SettingResponse>(`settings/${key}`, {
            value,
        });

    const deleteSetting = async (key: string) => api.remove(`settings/${key}`);

    const resetAllData = async () =>
        api.post<Record<string, never>, { message: string }>(
            'settings/reset',
            {},
        );

    const backup = async (): Promise<void> => {
        const response = await fetch(
            `${window.location.origin}/api/v1/settings/backup`,
            { method: 'POST' },
        );
        if (!response.ok) throw new Error('Backup failed');
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download =
            response.headers
                .get('content-disposition')
                ?.match(/filename="(.+)"/)?.[1] ?? 'backup.zip';
        a.click();
        URL.revokeObjectURL(url);
    };

    const restore = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        const response = await fetch(
            `${window.location.origin}/api/v1/settings/restore`,
            { method: 'POST', body: formData },
        );
        const data = await response.json();
        if (!response.ok) {
            return {
                success: false as const,
                error: data.error ?? 'Restore failed',
            };
        }
        return { success: true as const, data };
    };

    return {
        getSetting,
        setSetting,
        deleteSetting,
        resetAllData,
        backup,
        restore,
    };
}
