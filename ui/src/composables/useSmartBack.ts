import { useRouter } from 'vue-router';

/**
 * A "back" navigation that returns to wherever the user actually came from —
 * e.g. a tabbed shell like /strength?tab=logs rather than always landing on
 * a fixed list route — falling back to `fallback` when there is no in-app
 * history to return to (a fresh deep link or a reloaded page).
 *
 * Vue Router's history state carries the previous entry's path in
 * `history.state.back`; when that's absent there is nothing to go back to.
 */
export function useSmartBack(fallback: string) {
    const router = useRouter();

    function back() {
        if (window.history.state?.back) {
            router.back();
        } else {
            void router.push(fallback);
        }
    }

    return { back };
}
