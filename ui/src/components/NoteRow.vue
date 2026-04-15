<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';

import NoteDueBadges from '@/components/NoteDueBadges.vue';
import { useNoteApi } from '@/composables/api/useNoteApi';
import { useUiState } from '@/composables/useUiState';
import type { NoteTreeNode } from '@/types/Note';
import { renderMarkdown } from '@/utils/markdown';

const props = defineProps<{
    node: NoteTreeNode;
    depth: number;
    isFocused: boolean;
    focusedNodeId: number | null;
}>();

const emit = defineEmits<{
    'toggle-collapse': [node: NoteTreeNode];
    'set-focus': [node: NoteTreeNode];
    zoom: [nodeId: number];
    input: [event: Event, node: NoteTreeNode];
    blur: [node: NoteTreeNode];
    keydown: [event: KeyboardEvent, node: NoteTreeNode];
    paste: [event: ClipboardEvent, node: NoteTreeNode];
    'add-child': [node: NoteTreeNode];
    delete: [node: NoteTreeNode];
    'save-due': [node: NoteTreeNode, due: string | null];
    'cycle-recurrence': [node: NoteTreeNode];
    complete: [node: NoteTreeNode];
}>();

const { uploadNoteImage } = useNoteApi();
const ui = useUiState();
const router = useRouter();

const hovered = ref(false);
const uploading = ref(false);
const showDueEditor = ref(false);
const dueDraft = ref('');

async function uploadAndInsertImage(
    file: File,
    textarea: HTMLTextAreaElement | null,
) {
    uploading.value = true;
    try {
        const res = await uploadNoteImage(file);
        if (!res.success || !res.data) return;
        const markdownImg = `![](${res.data.url})`;
        const cursorPos = textarea?.selectionStart ?? props.node.content.length;
        const newContent =
            props.node.content.slice(0, cursorPos) +
            markdownImg +
            props.node.content.slice(cursorPos);
        emit(
            'input',
            { target: { value: newContent } } as unknown as Event,
            props.node,
        );
    } finally {
        uploading.value = false;
    }
}

function handlePaste(e: ClipboardEvent) {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
        if (item.type.startsWith('image/')) {
            e.preventDefault();
            const file = item.getAsFile();
            if (!file) return;
            const textarea = document.querySelector(
                `[data-note-id="${props.node.id}"] textarea`,
            ) as HTMLTextAreaElement | null;
            uploadAndInsertImage(file, textarea);
            return;
        }
    }
    emit('paste', e, props.node);
}

function openFilePicker() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = () => {
        const file = input.files?.[0];
        if (!file) return;
        uploadAndInsertImage(file, null);
    };
    input.click();
}

function openDueEditor() {
    dueDraft.value = props.node.due_date ?? '';
    showDueEditor.value = true;
}

function saveDue() {
    showDueEditor.value = false;
    const value = dueDraft.value.trim() || null;
    emit('save-due', props.node, value);
}

// Delegated click handler for rendered markdown. Navigates on wiki-link
// clicks and opens the palette pre-filled for tag/mention clicks so it never
// falls through to the textarea focus path.
function onRenderedClick(e: MouseEvent) {
    const target = e.target as HTMLElement;
    const wiki = target.closest('[data-wiki]') as HTMLElement | null;
    if (wiki) {
        e.preventDefault();
        e.stopPropagation();
        const name = wiki.getAttribute('data-wiki') || '';
        ui.openPalette(name);
        return;
    }
    const tag = target.closest('[data-tag]') as HTMLElement | null;
    if (tag) {
        e.preventDefault();
        e.stopPropagation();
        ui.openPalette(tag.getAttribute('data-tag') || '');
        return;
    }
    const mention = target.closest('[data-mention]') as HTMLElement | null;
    if (mention) {
        e.preventDefault();
        e.stopPropagation();
        ui.openPalette(mention.getAttribute('data-mention') || '');
        return;
    }
    emit('set-focus', props.node);
}

// Avoids an "unused import" warning when router is only consulted elsewhere.
void router;
</script>

<template>
    <div
        class="group relative flex items-start gap-1 rounded py-0.5 hover:bg-stone-100 dark:hover:bg-stone-800"
        :data-note-id="node.id"
        :style="{ paddingLeft: depth * 1.5 + 'rem' }"
        @mouseenter="hovered = true"
        @mouseleave="hovered = false"
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
            :title="
                'Zoom into ' + node.content.split('\n')[0]?.trim() || 'Untitled'
            "
            @click="emit('zoom', node.id)"
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
            :style="{ left: Math.max(0, depth * 1.5 - 0.5) + 'rem' }"
            tabindex="-1"
            @click="emit('toggle-collapse', node)"
        >
            <i
                class="pi text-[8px]"
                :class="node.collapsed ? 'pi-caret-right' : 'pi-caret-down'"
            ></i>
        </button>

        <!-- Content: rendered markdown or editable textarea -->
        <div
            v-if="!isFocused"
            class="note-prose prose prose-sm dark:prose-invert text-surface-800 dark:text-surface-200 min-h-[1.75rem] flex-1 cursor-text py-1 text-sm"
            @click="onRenderedClick"
            v-html="renderMarkdown(node.content)"
        ></div>
        <textarea
            v-else
            class="text-surface-800 dark:text-surface-200 min-h-[1.75rem] flex-1 resize-none overflow-hidden border-none bg-transparent py-1 text-sm leading-snug outline-none"
            rows="1"
            :value="node.content"
            @blur="emit('blur', node)"
            @input="emit('input', $event, node)"
            @keydown="emit('keydown', $event, node)"
            @paste="handlePaste"
            @vue:mounted="
                ($event: any) => {
                    const el = $event.el as HTMLTextAreaElement;
                    el.style.height = 'auto';
                    el.style.height = el.scrollHeight + 'px';
                    el.focus();
                }
            "
        />

        <!-- Due date / recurrence badges, always visible when set -->
        <NoteDueBadges
            :node="node"
            @complete="emit('complete', node)"
            @cycle-recurrence="emit('cycle-recurrence', node)"
            @edit-due="openDueEditor()"
        />

        <!-- Hover actions -->
        <div
            class="mt-1 flex shrink-0 gap-0.5 opacity-0 transition-opacity"
            :class="{ 'opacity-100': hovered }"
        >
            <button
                class="text-surface-400 hover:text-primary-500 rounded p-0.5"
                title="Set due date"
                @click="openDueEditor"
            >
                <i class="pi pi-calendar text-xs"></i>
            </button>
            <button
                class="text-surface-400 hover:text-primary-500 rounded p-0.5"
                title="Cycle recurrence"
                @click="emit('cycle-recurrence', node)"
            >
                <i class="pi pi-replay text-xs"></i>
            </button>
            <button
                class="text-surface-400 hover:text-primary-500 rounded p-0.5"
                title="Add image"
                @click="openFilePicker"
            >
                <i
                    class="pi text-xs"
                    :class="uploading ? 'pi-spinner pi-spin' : 'pi-image'"
                ></i>
            </button>
            <button
                class="text-surface-400 hover:text-primary-500 rounded p-0.5"
                title="Add child"
                @click="emit('add-child', node)"
            >
                <i class="pi pi-plus text-xs"></i>
            </button>
            <button
                class="text-surface-400 rounded p-0.5 hover:text-red-500"
                title="Delete"
                @click="emit('delete', node)"
            >
                <i class="pi pi-trash text-xs"></i>
            </button>
        </div>

        <!-- Due date popover -->
        <div
            v-if="showDueEditor"
            class="border-surface-200 bg-surface-0 dark:border-surface-700 dark:bg-surface-900 absolute top-8 right-2 z-30 rounded-lg border p-2 shadow-xl"
            @click.stop
        >
            <input
                v-model="dueDraft"
                class="border-surface-200 bg-surface-0 dark:border-surface-700 dark:bg-surface-900 rounded border px-2 py-1 text-xs outline-none"
                type="date"
                @keydown.enter="saveDue"
                @keydown.escape="showDueEditor = false"
            />
            <div class="mt-1 flex gap-1">
                <button
                    class="bg-primary-500 hover:bg-primary-600 rounded px-2 py-0.5 text-[10px] text-white"
                    @click="saveDue"
                >
                    Save
                </button>
                <button
                    v-if="node.due_date"
                    class="bg-surface-100 hover:bg-surface-200 dark:bg-surface-800 rounded px-2 py-0.5 text-[10px] hover:text-red-500"
                    @click="
                        dueDraft = '';
                        saveDue();
                    "
                >
                    Clear
                </button>
            </div>
        </div>
    </div>
</template>
