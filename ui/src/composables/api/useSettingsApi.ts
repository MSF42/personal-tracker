import { useApi } from '@/composables/api/useApi';

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

    return { getSetting, setSetting };
}
