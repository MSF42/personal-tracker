import { ref } from 'vue';

export function useLoading() {
    const loading = ref(false);

    const withLoading = async (fn: () => Promise<void>) => {
        loading.value = true;
        try {
            await fn();
        } finally {
            loading.value = false;
        }
    };

    return { loading, withLoading };
}
