<script setup lang="ts">
import { nextTick, ref } from 'vue';

import { useNoteApi } from '@/composables/api/useNoteApi';
import { useNoteTree } from '@/composables/useNoteTree';
import type { NoteTreeNode } from '@/types/Note';
import { renderMarkdown } from '@/utils/markdown';

const {
    tree,
    focusId,
    selectedNoteId,
    focusedNodeId,
    nodeRefs,
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

const { uploadNoteImage, updateNote } = useNoteApi();

const hoveredId = ref<number | null>(null);
const uploadingImages = ref<Set<number>>(new Set());

async function uploadAndInsertImage(
    file: File,
    node: NoteTreeNode,
    textarea: HTMLTextAreaElement | null,
) {
    uploadingImages.value.add(node.id);
    uploadingImages.value = new Set(uploadingImages.value);
    try {
        const res = await uploadNoteImage(file);
        if (!res.success || !res.data) return;

        const markdownImg = `![](${res.data.url})`;
        const cursorPos = textarea?.selectionStart ?? node.content.length;
        node.content =
            node.content.slice(0, cursorPos) +
            markdownImg +
            node.content.slice(cursorPos);
        await updateNote(node.id, { content: node.content });
    } finally {
        uploadingImages.value.delete(node.id);
        uploadingImages.value = new Set(uploadingImages.value);
    }
}

function handlePaste(e: ClipboardEvent, node: NoteTreeNode) {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (const item of items) {
        if (item.type.startsWith('image/')) {
            e.preventDefault();
            const file = item.getAsFile();
            if (!file) return;
            const textarea = document.querySelector(
                `[data-note-id="${node.id}"] textarea`,
            ) as HTMLTextAreaElement | null;
            uploadAndInsertImage(file, node, textarea);
            return;
        }
    }
}

function openFilePicker(node: NoteTreeNode) {
    setFocus(node.id);
    nextTick(() => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = () => {
            const file = input.files?.[0];
            if (!file) return;
            const textarea = document.querySelector(
                `[data-note-id="${node.id}"] textarea`,
            ) as HTMLTextAreaElement | null;
            uploadAndInsertImage(file, node, textarea);
        };
        input.click();
    });
}

const hoveredSidebarId = ref<number | null>(null);
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
                    @mouseenter="hoveredSidebarId = note.id"
                    @mouseleave="hoveredSidebarId = null"
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
                    <div
                        v-for="{ node, depth } in flatNodes"
                        :key="node.id"
                        class="group relative flex items-start gap-1 rounded py-0.5 hover:bg-stone-100 dark:hover:bg-stone-800"
                        :data-note-id="node.id"
                        :style="{ paddingLeft: depth * 1.5 + 'rem' }"
                        @mouseenter="hoveredId = node.id"
                        @mouseleave="hoveredId = null"
                    >
                        <!-- Indent guides -->
                        <div
                            v-for="i in depth"
                            :key="'guide-' + i"
                            class="pointer-events-none absolute inset-y-0 w-px bg-stone-200 dark:bg-stone-700"
                            :style="{ left: (i - 1) * 1.5 + 0.625 + 'rem' }"
                        ></div>
                        <!-- Bullet — zoom trigger -->
                        <button
                            class="mt-1.5 flex h-5 w-5 shrink-0 cursor-pointer items-center justify-center rounded"
                            :class="
                                focusedNodeId === node.id
                                    ? 'text-primary-500'
                                    : 'text-surface-400 hover:text-surface-600 dark:hover:text-surface-300'
                            "
                            tabindex="-1"
                            :title="'Zoom into ' + noteTitle(node)"
                            @click="focusedNodeId = node.id"
                        >
                            <span
                                class="inline-block h-1.5 w-1.5 rounded-full"
                                :class="
                                    focusedNodeId === node.id
                                        ? 'bg-primary-500'
                                        : 'bg-surface-400 dark:bg-surface-500'
                                "
                            ></span>
                        </button>

                        <!-- Collapse caret — halfway between parent guide and this bullet -->
                        <button
                            v-if="node.children.length"
                            class="text-surface-400 hover:text-surface-600 dark:hover:text-surface-300 absolute top-2 flex h-3 w-3 cursor-pointer items-center justify-center opacity-0 transition-opacity group-hover:opacity-100"
                            :style="{
                                left: Math.max(0, depth * 1.5 - 0.5) + 'rem',
                            }"
                            tabindex="-1"
                            @click="toggleCollapse(node)"
                        >
                            <i
                                class="pi text-[8px]"
                                :class="
                                    node.collapsed
                                        ? 'pi-caret-right'
                                        : 'pi-caret-down'
                                "
                            ></i>
                        </button>

                        <!-- Content: rendered markdown or editable textarea -->
                        <div
                            v-if="focusId !== node.id"
                            class="note-prose prose prose-sm dark:prose-invert text-surface-800 dark:text-surface-200 min-h-[1.75rem] flex-1 cursor-text py-1 text-sm"
                            @click="setFocus(node.id)"
                            v-html="renderMarkdown(node.content)"
                        ></div>
                        <textarea
                            v-else
                            class="text-surface-800 dark:text-surface-200 min-h-[1.75rem] flex-1 resize-none overflow-hidden border-none bg-transparent py-1 text-sm leading-snug outline-none"
                            rows="1"
                            :value="node.content"
                            :ref="(el) => { if (el) nodeRefs[node.id] = el as HTMLTextAreaElement }"
                            @blur="
                                handleBlur(node);
                                if (focusId === node.id) focusId = null;
                            "
                            @focus="focusId = node.id"
                            @input="handleInput($event, node)"
                            @keydown="handleKeydown($event, node)"
                            @paste="handlePaste($event, node)"
                            @vue:mounted="
                                ($event: any) => {
                                    const el = $event.el as HTMLTextAreaElement;
                                    el.style.height = 'auto';
                                    el.style.height = el.scrollHeight + 'px';
                                }
                            "
                        />

                        <!-- Hover actions -->
                        <div
                            class="mt-1 flex shrink-0 gap-0.5 opacity-0 transition-opacity"
                            :class="{ 'opacity-100': hoveredId === node.id }"
                        >
                            <button
                                class="text-surface-400 hover:text-primary-500 rounded p-0.5"
                                title="Add image"
                                @click="openFilePicker(node)"
                            >
                                <i
                                    class="pi text-xs"
                                    :class="
                                        uploadingImages.has(node.id)
                                            ? 'pi-spinner pi-spin'
                                            : 'pi-image'
                                    "
                                ></i>
                            </button>
                            <button
                                class="text-surface-400 hover:text-primary-500 rounded p-0.5"
                                title="Add child"
                                @click="addChild(node)"
                            >
                                <i class="pi pi-plus text-xs"></i>
                            </button>
                            <button
                                class="text-surface-400 rounded p-0.5 hover:text-red-500"
                                title="Delete"
                                @click="handleDelete(node)"
                            >
                                <i class="pi pi-trash text-xs"></i>
                            </button>
                        </div>
                    </div>
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
