import { ref } from 'vue';

import { useSettingsApi } from '@/composables/api/useSettingsApi';

export function useUserProfile() {
    const { getSetting } = useSettingsApi();

    const profilePicture = ref<string | null>(null);
    const userName = ref<string | null>(null);

    async function loadProfile() {
        const [profileRes, nameRes] = await Promise.all([
            getSetting('profile_picture'),
            getSetting('user_name'),
        ]);
        if (profileRes.success && profileRes.data?.value) {
            profilePicture.value = profileRes.data.value;
        }
        if (nameRes.success && nameRes.data?.value) {
            userName.value = nameRes.data.value;
        }
    }

    return { profilePicture, userName, loadProfile };
}
