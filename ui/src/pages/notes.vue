<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import NoteRow from '@/components/NoteRow.vue';
import { useNoteApi } from '@/composables/api/useNoteApi';
import { useSearchApi } from '@/composables/api/useSearchApi';
import { useNoteTree } from '@/composables/useNoteTree';
import { useUiState } from '@/composables/useUiState';
import type { Note, NoteTreeNode } from '@/types/Note';
import type { BacklinkRow, TagCount } from '@/types/Search';

const {
    tree,
    focusId,
    selectedNoteId,
    focusedNodeId,
    selectedNote,
    viewRoot,
    focusedPath,
    flatNodes,
    noteTitle,
    setFocus,
    toggleCollapse,
    addChild,
    addRootNote,
    deleteRootNote,
    handleDelete,
    handleInput,
    handleBlur,
    handleKeydown,
    openNode,
    setNodeDueDate,
    cycleRecurrence,
    completeDueNodeAction,
} = useNoteTree();

const { searchNotes, exportNoteMarkdown } = useNoteApi();
const { getTags, getBacklinks } = useSearchApi();
const ui = useUiState();
const route = useRoute();
const router = useRouter();

// --- Sidebar toggle (mobile) ---
const sidebarOpen = ref(true);

// --- Delete confirmation ---
const showDeleteConfirm = ref(false);
const pendingDeleteNote = ref<NoteTreeNode | null>(null);

function requestDeleteRootNote(note: NoteTreeNode) {
    pendingDeleteNote.value = note;
    showDeleteConfirm.value = true;
}

async function confirmDeleteRootNote() {
    if (pendingDeleteNote.value) {
        await deleteRootNote(pendingDeleteNote.value);
    }
    showDeleteConfirm.value = false;
    pendingDeleteNote.value = null;
}

const searchQuery = ref('');
const searchResults = ref<Note[]>([]);
let searchTimer: ReturnType<typeof setTimeout> | null = null;

watch(searchQuery, (q) => {
    if (searchTimer) clearTimeout(searchTimer);
    if (!q) {
        searchResults.value = [];
        return;
    }
    searchTimer = setTimeout(async () => {
        const res = await searchNotes(q);
        if (res.success && res.data) searchResults.value = res.data;
    }, 300);
});

onUnmounted(() => {
    if (searchTimer) clearTimeout(searchTimer);
});

function selectSearchResult(id: number) {
    selectedNoteId.value = id;
    searchQuery.value = '';
}

function noteFirstLine(note: Note): string {
    return note.content.split('\n')[0] || 'Untitled';
}

// --- Tags + backlinks ---

const tags = ref<TagCount[]>([]);
const mentions = ref<TagCount[]>([]);

async function loadTags() {
    const res = await getTags();
    if (res.success && res.data) {
        tags.value = res.data.tags;
        mentions.value = res.data.mentions;
    }
}

function openTag(name: string) {
    ui.openPalette(name);
}

const backlinks = ref<BacklinkRow[]>([]);

async function loadBacklinksFor(note: NoteTreeNode | null) {
    if (!note) {
        backlinks.value = [];
        return;
    }
    const title = noteTitle(note);
    if (!title || title === 'Untitled') {
        backlinks.value = [];
        return;
    }
    const res = await getBacklinks(title, note.id);
    if (res.success && res.data) {
        backlinks.value = res.data.links;
    } else {
        backlinks.value = [];
    }
}

watch(selectedNote, (note) => {
    loadBacklinksFor(note);
});

// --- Archive toggle: filter the sidebar tree client-side ---

const visibleTree = computed<NoteTreeNode[]>(() => {
    if (ui.showArchive.value) return tree.value;
    return tree.value.filter((n) => !n.archived);
});

// --- Query-param deep link (from palette search results) ---

async function handleRouteNoteParam() {
    const raw = route.query.note;
    if (!raw) return;
    const id = Number(Array.isArray(raw) ? raw[0] : raw);
    if (Number.isNaN(id)) return;
    await openNode(id);
    // Clear the query param so refreshes don't re-trigger the jump.
    const next = { ...route.query };
    delete next.note;
    router.replace({ query: next });
}

watch(() => route.query.note, handleRouteNoteParam);

onMounted(async () => {
    await loadTags();
    // Slight delay so useNoteTree's own onMounted load finishes first.
    setTimeout(handleRouteNoteParam, 50);
    window.addEventListener('outboard:inbox-captured', onInboxCaptured);
});

onUnmounted(() => {
    window.removeEventListener('outboard:inbox-captured', onInboxCaptured);
});

async function onInboxCaptured() {
    // If we're viewing the Inbox note, refresh the tree so the captured
    // child appears; otherwise just refresh tags.
    if (
        ui.inboxNoteId.value != null &&
        selectedNoteId.value === ui.inboxNoteId.value
    ) {
        const reloadedRes = await useNoteApi().getNotes();
        if (reloadedRes.success && reloadedRes.data) {
            tree.value = reloadedRes.data;
        }
    }
    await loadTags();
}

// --- Export + note-row event handlers ---

async function exportCurrentNote() {
    if (!selectedNote.value) return;
    const md = await exportNoteMarkdown(selectedNote.value.id);
    if (md == null) return;
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${noteTitle(selectedNote.value)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

async function onSaveDue(node: NoteTreeNode, due: string | null) {
    await setNodeDueDate(node, due);
}

async function onCycleRecurrence(node: NoteTreeNode) {
    await cycleRecurrence(node);
}

async function onComplete(node: NoteTreeNode) {
    await completeDueNodeAction(node);
    // A completed recurring node will have a new due date; a completed
    // non-recurring node will have none. Either way, re-run tags in case
    // content changed; no-op here but cheap.
    loadTags();
}
</script>

<template>
    <div class="flex h-full">
        <!-- Left sidebar -->
        <div
            v-show="!ui.focusMode.value"
            class="border-surface-200 dark:border-surface-700 flex shrink-0 flex-col border-r bg-slate-100 md:w-64 dark:bg-slate-800"
            :class="sidebarOpen ? 'w-64' : 'hidden md:flex'"
        >
            <div
                class="border-surface-200 dark:border-surface-700 border-b p-3"
            >
                <div
                    class="mb-2 text-[10px] font-bold tracking-widest text-slate-500 uppercase dark:text-slate-400"
                >
                    Notes
                </div>
                <button
                    class="w-full rounded-md bg-blue-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700"
                    @click="addRootNote"
                >
                    <i class="pi pi-plus mr-1.5 text-xs"></i>New Note
                </button>
            </div>

            <div
                class="border-surface-200 dark:border-surface-700 border-b px-3 pb-2"
            >
                <div class="relative">
                    <i
                        class="pi pi-search text-surface-400 pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-xs"
                    ></i>
                    <input
                        v-model="searchQuery"
                        class="border-surface-200 dark:border-surface-600 dark:bg-surface-800 dark:text-surface-100 w-full rounded-md border bg-white py-1.5 pr-7 pl-7 text-sm outline-none focus:ring-1 focus:ring-blue-500"
                        placeholder="Search notes..."
                        type="text"
                    />
                    <button
                        v-if="searchQuery"
                        class="text-surface-400 hover:text-surface-600 absolute top-1/2 right-2 -translate-y-1/2"
                        @click="searchQuery = ''"
                    >
                        <i class="pi pi-times text-xs"></i>
                    </button>
                </div>
            </div>

            <div class="flex-1 overflow-y-auto p-2">
                <!-- Search results -->
                <template v-if="searchQuery">
                    <div
                        v-for="result in searchResults"
                        :key="result.id"
                        class="cursor-pointer truncate rounded px-3 py-1.5 text-sm"
                        :class="
                            result.id === selectedNoteId
                                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                                : 'text-surface-700 dark:text-surface-300 hover:bg-surface-0 dark:hover:bg-slate-700'
                        "
                        @click="selectSearchResult(result.id)"
                    >
                        {{ noteFirstLine(result) }}
                    </div>
                    <div
                        v-if="searchResults.length === 0"
                        class="text-surface-400 px-2 py-4 text-center text-xs"
                    >
                        No results
                    </div>
                </template>

                <!-- Normal tree list -->
                <template v-else>
                    <div class="mb-1 flex items-center justify-end px-2">
                        <button
                            class="text-[9px] font-semibold tracking-widest uppercase"
                            :class="
                                ui.showArchive.value
                                    ? 'text-primary-500'
                                    : 'text-surface-400 hover:text-surface-600'
                            "
                            :title="
                                ui.showArchive.value
                                    ? 'Hide archived'
                                    : 'Show archived'
                            "
                            @click="ui.toggleArchive()"
                        >
                            {{
                                ui.showArchive.value ? 'hide arch' : 'show arch'
                            }}
                        </button>
                    </div>
                    <div
                        v-for="note in visibleTree"
                        :key="note.id"
                        class="group relative flex cursor-pointer items-center gap-1 rounded px-3 py-1.5 text-sm"
                        :class="
                            note.id === selectedNoteId
                                ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                                : 'text-surface-700 dark:text-surface-300 hover:bg-surface-0 hover:shadow-sm dark:hover:bg-slate-700'
                        "
                        @click="selectedNoteId = note.id"
                    >
                        <span class="min-w-0 flex-1 truncate">{{
                            noteTitle(note)
                        }}</span>
                        <button
                            class="shrink-0 rounded p-0.5 opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-500"
                            :class="
                                note.id === selectedNoteId
                                    ? 'text-primary-400'
                                    : 'text-surface-400'
                            "
                            title="Delete note"
                            @click.stop="requestDeleteRootNote(note)"
                        >
                            <i class="pi pi-trash text-xs"></i>
                        </button>
                    </div>

                    <div
                        v-if="visibleTree.length === 0"
                        class="text-surface-400 px-2 py-4 text-center text-xs"
                    >
                        No notes yet
                    </div>

                    <!-- Tag + mention index -->
                    <div v-if="tags.length" class="mt-4">
                        <div
                            class="text-surface-500 mb-1 px-3 text-[9px] font-semibold tracking-widest uppercase"
                        >
                            Tags
                        </div>
                        <div class="flex flex-wrap gap-1 px-3">
                            <button
                                v-for="t in tags.slice(0, 30)"
                                :key="'tag-' + t.name"
                                class="border-surface-200 dark:border-surface-700 text-surface-600 dark:text-surface-300 hover:border-primary-400 hover:text-primary-500 rounded border bg-white/40 px-1.5 py-0.5 text-[10px] dark:bg-slate-900/40"
                                @click="openTag('#' + t.name)"
                            >
                                #{{ t.name }}
                                <span class="text-surface-400">{{
                                    t.count
                                }}</span>
                            </button>
                        </div>
                    </div>
                    <div v-if="mentions.length" class="mt-2">
                        <div
                            class="text-surface-500 mb-1 px-3 text-[9px] font-semibold tracking-widest uppercase"
                        >
                            Mentions
                        </div>
                        <div class="flex flex-wrap gap-1 px-3 pb-2">
                            <button
                                v-for="m in mentions.slice(0, 30)"
                                :key="'m-' + m.name"
                                class="border-surface-200 dark:border-surface-700 text-surface-600 dark:text-surface-300 hover:border-primary-400 hover:text-primary-500 rounded border bg-white/40 px-1.5 py-0.5 text-[10px] dark:bg-slate-900/40"
                                @click="openTag('@' + m.name)"
                            >
                                @{{ m.name }}
                                <span class="text-surface-400">{{
                                    m.count
                                }}</span>
                            </button>
                        </div>
                    </div>
                </template>
            </div>
        </div>

        <!-- Delete Confirmation Dialog -->
        <AppDialog
            v-model:visible="showDeleteConfirm"
            header="Delete Note"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <p>
                Are you sure you want to delete this note and all its children?
            </p>
            <div class="mt-4 flex justify-end gap-2">
                <AppButton
                    label="Cancel"
                    text
                    @click="showDeleteConfirm = false"
                />
                <AppButton
                    label="Delete"
                    severity="danger"
                    @click="confirmDeleteRootNote"
                />
            </div>
        </AppDialog>

        <!-- Right panel -->
        <div class="flex min-w-0 flex-1 flex-col">
            <!-- Mobile sidebar toggle -->
            <div
                class="border-surface-200 dark:border-surface-700 flex items-center border-b px-3 py-2 md:hidden"
            >
                <AppButton
                    :icon="sidebarOpen ? 'pi pi-times' : 'pi pi-bars'"
                    rounded
                    severity="secondary"
                    size="small"
                    text
                    @click="sidebarOpen = !sidebarOpen"
                />
                <span class="text-surface-500 ml-2 text-sm">Notes</span>
            </div>

            <div
                v-if="!selectedNote"
                class="flex flex-1 items-center justify-center"
            >
                <div class="text-center">
                    <p class="text-surface-400 mb-4 text-lg">
                        No note selected
                    </p>
                    <AppButton
                        icon="pi pi-plus"
                        label="Add Note"
                        @click="addRootNote"
                    />
                </div>
            </div>

            <div
                v-else
                class="bg-surface-50 dark:bg-surface-900 flex flex-1 flex-col overflow-y-auto px-7 pt-6 pb-4"
            >
                <!-- Normal: editable title -->
                <template v-if="!focusedNodeId">
                    <div class="flex items-start gap-2">
                        <textarea
                            class="text-surface-900 dark:text-surface-100 mb-2 w-full resize-none border-none bg-transparent text-2xl leading-snug font-bold tracking-tight outline-none"
                            data-title-area
                            placeholder="Untitled"
                            rows="1"
                            :value="selectedNote.content"
                            @blur="handleBlur(selectedNote)"
                            @input="handleInput($event, selectedNote)"
                            @vue:mounted="
                                ($event: any) => {
                                    const el = $event.el as HTMLTextAreaElement;
                                    el.style.height = 'auto';
                                    el.style.height = el.scrollHeight + 'px';
                                }
                            "
                        />
                        <button
                            class="text-surface-400 hover:text-primary-500 shrink-0 pt-3 text-[10px] tracking-widest uppercase"
                            title="Export as markdown"
                            @click="exportCurrentNote"
                        >
                            ↓ export
                        </button>
                    </div>
                    <div
                        class="mt-1.5 mb-4 h-0.5 w-9 rounded bg-blue-500"
                    ></div>

                    <!-- Backlinks pane (only for top-level notes with links) -->
                    <div
                        v-if="backlinks.length"
                        class="border-surface-200 dark:border-surface-700 mb-4 rounded-md border p-3"
                    >
                        <div
                            class="text-surface-500 mb-1 text-[9px] font-semibold tracking-widest uppercase"
                        >
                            Linked from ({{ backlinks.length }})
                        </div>
                        <div class="space-y-0.5">
                            <button
                                v-for="b in backlinks"
                                :key="'bl-' + b.id"
                                class="text-surface-600 hover:text-primary-500 block w-full truncate text-left text-xs"
                                @click="openNode(b.id)"
                            >
                                {{ b.content.split('\n')[0] || '(empty)' }}
                            </button>
                        </div>
                    </div>
                </template>

                <!-- Zoomed: breadcrumb navigation -->
                <div
                    v-else
                    class="mb-4 flex flex-wrap items-center gap-1 text-sm"
                >
                    <button
                        class="text-primary-600 dark:text-primary-400 max-w-[10rem] truncate font-medium hover:underline"
                        @click="focusedNodeId = null"
                    >
                        {{ noteTitle(selectedNote) }}
                    </button>
                    <template v-for="(crumb, i) in focusedPath" :key="crumb.id">
                        <i
                            class="pi pi-chevron-right text-surface-400 text-xs"
                        ></i>
                        <button
                            v-if="i < focusedPath.length - 1"
                            class="text-primary-600 dark:text-primary-400 max-w-[10rem] truncate hover:underline"
                            @click="focusedNodeId = crumb.id"
                        >
                            {{ noteTitle(crumb) }}
                        </button>
                        <span
                            v-else
                            class="text-surface-900 dark:text-surface-100 max-w-[10rem] truncate font-semibold"
                            >{{ noteTitle(crumb) }}</span
                        >
                    </template>
                </div>

                <!-- Outline content -->
                <div v-if="flatNodes.length > 0" class="space-y-0">
                    <NoteRow
                        v-for="{ node, depth } in flatNodes"
                        :key="node.id"
                        :depth="depth"
                        :focused-node-id="focusedNodeId"
                        :is-focused="focusId === node.id"
                        :node="node"
                        @add-child="addChild"
                        @blur="
                            (n) => {
                                handleBlur(n);
                                if (focusId === n.id) focusId = null;
                            }
                        "
                        @complete="onComplete"
                        @cycle-recurrence="onCycleRecurrence"
                        @delete="handleDelete"
                        @input="handleInput"
                        @keydown="handleKeydown"
                        @save-due="onSaveDue"
                        @set-focus="(n) => setFocus(n.id)"
                        @toggle-collapse="toggleCollapse"
                        @zoom="(id) => (focusedNodeId = id)"
                    />
                </div>

                <!-- Empty state: no children yet -->
                <div v-else class="mt-2">
                    <button
                        class="text-surface-400 hover:text-primary-500 flex items-center gap-1 text-sm"
                        @click="viewRoot && addChild(viewRoot)"
                    >
                        <i class="pi pi-plus text-xs"></i>
                        <span>Add item</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>
