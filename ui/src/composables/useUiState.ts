import { ref } from 'vue';

// Module-scoped refs so every caller of useUiState() sees the same state —
// mirrors the composable-only state convention used elsewhere in the app.
const focusMode = ref(false);
const paletteOpen = ref(false);
const paletteInitialQuery = ref('');

export function useUiState() {
    function openPalette(initialQuery = '') {
        paletteInitialQuery.value = initialQuery;
        paletteOpen.value = true;
    }

    function closePalette() {
        paletteOpen.value = false;
        paletteInitialQuery.value = '';
    }

    function toggleFocusMode() {
        focusMode.value = !focusMode.value;
    }

    function exitFocusMode() {
        focusMode.value = false;
    }

    return {
        // state (refs, consumers can read reactively)
        focusMode,
        paletteOpen,
        paletteInitialQuery,
        // actions
        openPalette,
        closePalette,
        toggleFocusMode,
        exitFocusMode,
    };
}
