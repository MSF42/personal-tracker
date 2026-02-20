<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';

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
    walk(tree.value, 0);
    return result;
});

async function loadData() {
    const res = await getNotes();
    if (res.success && res.data) {
        tree.value = res.data;
    }
}

onMounted(loadData);

function setFocus(id: number) {
    focusId.value = id;
    nextTick(() => {
        const el = document.querySelector(
            `[data-note-id="${id}"] textarea`,
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
        setFocus(newNode.id);
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
</script>

<template>
    <div class="mx-auto max-w-4xl p-6">
        <div class="mb-6 flex items-center justify-between">
            <h1 class="text-2xl font-bold">Notes</h1>
            <AppButton
                icon="pi pi-plus"
                label="Add Note"
                @click="addRootNote"
            />
        </div>

        <div v-if="flatNodes.length === 0" class="py-16 text-center">
            <p class="text-surface-400 mb-4 text-lg">No notes yet</p>
            <AppButton
                icon="pi pi-plus"
                label="Add Note"
                @click="addRootNote"
            />
        </div>

        <div v-else class="space-y-0">
            <div
                v-for="{ node, depth } in flatNodes"
                :key="node.id"
                class="hover:bg-surface-50 dark:hover:bg-surface-800 group flex items-start gap-1 rounded py-0.5"
                :data-note-id="node.id"
                :style="{ paddingLeft: depth * 1.5 + 'rem' }"
                @mouseenter="hoveredId = node.id"
                @mouseleave="hoveredId = null"
            >
                <!-- Collapse toggle / bullet -->
                <button
                    class="mt-1.5 flex h-5 w-5 shrink-0 items-center justify-center rounded"
                    :class="
                        node.children.length
                            ? 'text-surface-500 hover:bg-surface-200 dark:hover:bg-surface-700 cursor-pointer'
                            : 'text-surface-300 dark:text-surface-600 cursor-default'
                    "
                    tabindex="-1"
                    @click="
                        node.children.length ? toggleCollapse(node) : undefined
                    "
                >
                    <i
                        v-if="node.children.length"
                        class="pi text-xs"
                        :class="
                            node.collapsed
                                ? 'pi-chevron-right'
                                : 'pi-chevron-down'
                        "
                    ></i>
                    <span
                        v-else
                        class="bg-surface-400 dark:bg-surface-500 inline-block h-1.5 w-1.5 rounded-full"
                    ></span>
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
                    @blur="
                        handleBlur(node);
                        focusId = null;
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
    </div>
</template>
