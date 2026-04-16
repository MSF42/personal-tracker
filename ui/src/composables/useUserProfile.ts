import { ref } from 'vue';

import { useSettingsApi } from '@/composables/api/useSettingsApi';
import { resolveUploadsUrl } from '@/utils/uploads';

// Module-scoped refs so App.vue and settings.vue share the same reactive
// state. When settings.vue updates the profile picture after an upload,
// App.vue's nav bar image updates immediately.
const profilePicture = ref<string | null>(null);
const userName = ref<string | null>(null);

export function useUserProfile() {
    const { getSetting } = useSettingsApi();

    async function loadProfile() {
        const [profileRes, nameRes] = await Promise.all([
            getSetting('profile_picture'),
            getSetting('user_name'),
        ]);
        if (profileRes.success && profileRes.data?.value) {
            profilePicture.value = resolveUploadsUrl(profileRes.data.value);
        }
        if (nameRes.success && nameRes.data?.value) {
            userName.value = nameRes.data.value;
        }
    }

    function setProfilePicture(url: string | null) {
        profilePicture.value = url;
    }

    function setUserName(name: string | null) {
        userName.value = name;
    }

    return {
        profilePicture,
        userName,
        loadProfile,
        setProfilePicture,
        setUserName,
    };
}
