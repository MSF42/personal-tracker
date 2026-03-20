<script setup lang="ts">
import NoteRow from '@/components/NoteRow.vue';
import { useNoteTree } from '@/composables/useNoteTree';

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
} = useNoteTree();
</script>

<template>
    <div class="flex h-full">
        <!-- Left sidebar -->
        <div
            class="border-surface-200 dark:border-surface-700 flex w-64 shrink-0 flex-col border-r bg-slate-100 dark:bg-slate-800"
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

            <div class="flex-1 overflow-y-auto p-2">
                <div
                    v-for="note in tree"
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
                        @click.stop="deleteRootNote(note)"
                    >
                        <i class="pi pi-trash text-xs"></i>
                    </button>
                </div>

                <div
                    v-if="tree.length === 0"
                    class="text-surface-400 px-2 py-4 text-center text-xs"
                >
                    No notes yet
                </div>
            </div>
        </div>

        <!-- Right panel -->
        <div class="flex min-w-0 flex-1 flex-col">
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
                class="flex flex-1 flex-col overflow-y-auto bg-stone-50 px-7 pt-6 pb-4 dark:bg-stone-900"
            >
                <!-- Normal: editable title -->
                <template v-if="!focusedNodeId">
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
                    <div
                        class="mt-1.5 mb-4 h-0.5 w-9 rounded bg-blue-500"
                    ></div>
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
                        @delete="handleDelete"
                        @input="handleInput"
                        @keydown="handleKeydown"
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
