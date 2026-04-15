import { ref } from 'vue';

// Module-scoped refs so every caller of useUiState() sees the same state —
// mirrors the composable-only state convention elsewhere in the app (e.g.
// useNoteTree() holds its tree in composable scope rather than via Pinia).
const focusMode = ref(false);
const paletteOpen = ref(false);
const paletteInitialQuery = ref('');
const showArchive = ref(false);
const inboxNoteId = ref<number | null>(null);

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

    function toggleArchive() {
        showArchive.value = !showArchive.value;
    }

    function setInboxNoteId(id: number | null) {
        inboxNoteId.value = id;
    }

    return {
        // state (refs, consumers can read reactively)
        focusMode,
        paletteOpen,
        paletteInitialQuery,
        showArchive,
        inboxNoteId,
        // actions
        openPalette,
        closePalette,
        toggleFocusMode,
        exitFocusMode,
        toggleArchive,
        setInboxNoteId,
    };
}
