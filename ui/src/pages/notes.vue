<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';

import { useNoteApi } from '@/composables/api/useNoteApi';
import type { NoteTreeNode } from '@/types/Note';
import { renderMarkdown } from '@/utils/markdown';

const {
    getNotes,
    createNote,
    updateNote,
    moveNote,
    deleteNote,
    uploadNoteImage,
} = useNoteApi();

const tree = ref<NoteTreeNode[]>([]);
const focusId = ref<number | null>(null);
const selectedNoteId = ref<number | null>(null);
const focusedNodeId = ref<number | null>(null);
const nodeRefs = ref<Record<number, HTMLTextAreaElement>>({});

const selectedNote = computed(
    () =>
        selectedNoteId.value
            ? findInTree(tree.value, selectedNoteId.value)
            : null,
);

function findInTree(nodes: NoteTreeNode[], id: number): NoteTreeNode | null {
    for (const n of nodes) {
        if (n.id === id) return n;
        const found = findInTree(n.children, id);
        if (found) return found;
    }
    return null;
}

function findPath(
    nodes: NoteTreeNode[],
    id: number,
    path: NoteTreeNode[],
): NoteTreeNode[] | null {
    for (const n of nodes) {
        if (n.id === id) return [...path, n];
        const found = findPath(n.children, id, [...path, n]);
        if (found) return found;
    }
    return null;
}

const focusedNode = computed(() =>
    focusedNodeId.value && selectedNote.value
        ? findInTree(selectedNote.value.children, focusedNodeId.value)
        : null,
);

const viewRoot = computed(
    () => focusedNode.value ?? selectedNote.value ?? null,
);

const focusedPath = computed<NoteTreeNode[]>(() =>
    focusedNodeId.value && selectedNote.value
        ? (findPath(selectedNote.value.children, focusedNodeId.value, []) ?? [])
        : [],
);

interface FlatNode {
    node: NoteTreeNode;
    depth: number;
}

const flatNodes = computed<FlatNode[]>(() => {
    const result: FlatNode[] = [];
    function walk(nodes: NoteTreeNode[], depth: number) {
        for (const node of nodes) {
            result.push({ node, depth });
            if (!node.collapsed && node.children.length) {
                walk(node.children, depth + 1);
            }
        }
    }
    walk(viewRoot.value?.children ?? [], 0);
    return result;
});

async function loadData() {
    const res = await getNotes();
    if (res.success && res.data) {
        tree.value = res.data;
        if (tree.value.length > 0 && !selectedNoteId.value) {
            selectedNoteId.value = tree.value[0]!.id;
        }
    }
}

onMounted(loadData);

watch(selectedNoteId, () => {
    focusedNodeId.value = null;
});

function setFocus(id: number) {
    focusId.value = id;
    nextTick(() => {
        nodeRefs.value[id]?.focus();
    });
}

function focusTitleArea() {
    nextTick(() => {
        const el = document.querySelector(
            '[data-title-area]',
        ) as HTMLTextAreaElement | null;
        el?.focus();
    });
}

function findParentAndIndex(
    nodes: NoteTreeNode[],
    id: number,
    parent: NoteTreeNode | null = null,
): {
    parent: NoteTreeNode | null;
    index: number;
    siblings: NoteTreeNode[];
} | null {
    for (let i = 0; i < nodes.length; i++) {
        const current = nodes[i]!;
        if (current.id === id) {
            return { parent, index: i, siblings: nodes };
        }
        if (current.children.length) {
            const found = findParentAndIndex(current.children, id, current);
            if (found) return found;
        }
    }
    return null;
}

// Track which nodes have unsaved content changes
const dirtyNodes = new Set<number>();

function handleInput(e: Event, node: NoteTreeNode) {
    const el = e.target as HTMLTextAreaElement;
    node.content = el.value;
    dirtyNodes.add(node.id);
    autoResize(e);
}

async function handleBlur(node: NoteTreeNode) {
    if (dirtyNodes.has(node.id)) {
        dirtyNodes.delete(node.id);
        await updateNote(node.id, { content: node.content });
    }
}

async function toggleCollapse(node: NoteTreeNode) {
    const newVal = !node.collapsed;
    await updateNote(node.id, { collapsed: newVal });
    node.collapsed = newVal;
}

async function addSibling(afterNode: NoteTreeNode) {
    const info = findParentAndIndex(tree.value, afterNode.id);
    if (!info) return;

    const newSortOrder = afterNode.sort_order + 1;

    // Bump sort_order for subsequent siblings
    for (let i = info.index + 1; i < info.siblings.length; i++) {
        const sibling = info.siblings[i]!;
        sibling.sort_order++;
        await moveNote(sibling.id, {
            parent_id: info.parent?.id ?? null,
            sort_order: sibling.sort_order,
        });
    }

    const res = await createNote({
        parent_id: info.parent?.id ?? null,
        content: '',
        sort_order: newSortOrder,
    });
    if (res.success && res.data) {
        const newNode: NoteTreeNode = {
            ...res.data,
            children: [],
        };
        info.siblings.splice(info.index + 1, 0, newNode);
        setFocus(newNode.id);
    }
}

async function addChild(parentNode: NoteTreeNode) {
    const res = await createNote({
        parent_id: parentNode.id,
        content: '',
    });
    if (res.success && res.data) {
        const newNode: NoteTreeNode = {
            ...res.data,
            children: [],
        };
        parentNode.children.push(newNode);
        parentNode.collapsed = false;
        await updateNote(parentNode.id, { collapsed: false });
        setFocus(newNode.id);
    }
}

async function addRootNote() {
    const res = await createNote({ content: '' });
    if (res.success && res.data) {
        const newNode: NoteTreeNode = {
            ...res.data,
            children: [],
        };
        tree.value.push(newNode);
        selectedNoteId.value = newNode.id;
        focusTitleArea();
    }
}

async function deleteRootNote(node: NoteTreeNode) {
    const idx = tree.value.findIndex((n) => n.id === node.id);
    if (idx === -1) return;
    await deleteNote(node.id);
    tree.value.splice(idx, 1);
    if (selectedNoteId.value === node.id) {
        selectedNoteId.value = tree.value[0]?.id ?? null;
    }
}

async function handleDelete(node: NoteTreeNode) {
    const info = findParentAndIndex(tree.value, node.id);
    if (!info) return;

    await deleteNote(node.id);
    info.siblings.splice(info.index, 1);

    // Focus previous visible node
    const flat = flatNodes.value;
    const idx = flat.findIndex((f) => f.node.id === node.id);
    if (idx > 0) {
        setFocus(flat[idx - 1]!.node.id);
    }
}

async function indent(node: NoteTreeNode) {
    const info = findParentAndIndex(tree.value, node.id);
    if (!info || info.index === 0) return;

    const prevSibling = info.siblings[info.index - 1]!;

    // Remove from current position
    info.siblings.splice(info.index, 1);

    // Add as last child of previous sibling
    const newSortOrder = prevSibling.children.length;
    prevSibling.children.push(node);
    prevSibling.collapsed = false;

    await moveNote(node.id, {
        parent_id: prevSibling.id,
        sort_order: newSortOrder,
    });
    await updateNote(prevSibling.id, { collapsed: false });
    setFocus(node.id);
}

async function outdent(node: NoteTreeNode) {
    const info = findParentAndIndex(tree.value, node.id);
    if (!info || !info.parent) return;

    const grandparentInfo = findParentAndIndex(tree.value, info.parent.id);
    if (!grandparentInfo) return;

    // Remove from parent's children
    info.siblings.splice(info.index, 1);

    // Insert after parent in grandparent's children
    const parentIdx = grandparentInfo.index;
    const newSortOrder = info.parent.sort_order + 1;

    // Bump subsequent siblings of grandparent
    for (let i = parentIdx + 1; i < grandparentInfo.siblings.length; i++) {
        const gpSibling = grandparentInfo.siblings[i]!;
        gpSibling.sort_order++;
        await moveNote(gpSibling.id, {
            parent_id: grandparentInfo.parent?.id ?? null,
            sort_order: gpSibling.sort_order,
        });
    }

    grandparentInfo.siblings.splice(parentIdx + 1, 0, node);

    await moveNote(node.id, {
        parent_id: grandparentInfo.parent?.id ?? null,
        sort_order: newSortOrder,
    });
    setFocus(node.id);
}

async function flushNode(node: NoteTreeNode) {
    if (dirtyNodes.has(node.id)) {
        dirtyNodes.delete(node.id);
        await updateNote(node.id, { content: node.content });
    }
}

function handleKeydown(e: KeyboardEvent, node: NoteTreeNode) {
    const target = e.target as HTMLTextAreaElement;

    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        flushNode(node).then(() => addSibling(node));
        return;
    }

    if (e.key === 'Tab' && !e.shiftKey) {
        e.preventDefault();
        flushNode(node).then(() => indent(node));
        return;
    }

    if (e.key === 'Tab' && e.shiftKey) {
        e.preventDefault();
        flushNode(node).then(() => outdent(node));
        return;
    }

    if (e.key === 'Backspace' && target.value === '') {
        e.preventDefault();
        handleDelete(node);
        return;
    }

    if (e.key === 'ArrowUp' && target.selectionStart === 0) {
        e.preventDefault();
        const flat = flatNodes.value;
        const idx = flat.findIndex((f) => f.node.id === node.id);
        if (idx > 0) setFocus(flat[idx - 1]!.node.id);
        return;
    }

    if (
        e.key === 'ArrowDown' &&
        target.selectionStart === target.value.length
    ) {
        e.preventDefault();
        const flat = flatNodes.value;
        const idx = flat.findIndex((f) => f.node.id === node.id);
        if (idx < flat.length - 1) setFocus(flat[idx + 1]!.node.id);
    }
}

function autoResize(e: Event) {
    const el = e.target as HTMLTextAreaElement;
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
}

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
        dirtyNodes.add(node.id);
        await updateNote(node.id, { content: node.content });
        dirtyNodes.delete(node.id);
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
    // Focus the node first so the textarea exists
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

function noteTitle(node: NoteTreeNode): string {
    const first = node.content.split('\n')[0]?.trim();
    return first || 'Untitled';
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
