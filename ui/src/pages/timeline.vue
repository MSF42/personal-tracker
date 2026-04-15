<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { useNoteApi } from '@/composables/api/useNoteApi';
import type { NoteTreeNode } from '@/types/Note';

// Timeline view — groups top-level notes by how recently they were touched.
// Matches the timeline page in the companion outboard app and borrows the
// same bucket labels so the two feel consistent.

const { getNotes } = useNoteApi();
const router = useRouter();

const rootNotes = ref<NoteTreeNode[]>([]);

function flattenRoots(tree: NoteTreeNode[]): NoteTreeNode[] {
    // Only root-level notes participate in the timeline. Inbox is still
    // included — it gets touched whenever a quick capture happens and is a
    // useful signal.
    return [...tree].sort((a, b) =>
        (b.updated_at || '').localeCompare(a.updated_at || ''),
    );
}

onMounted(async () => {
    const res = await getNotes();
    if (res.success && res.data) rootNotes.value = flattenRoots(res.data);
});

const DAY_MS = 86_400_000;

function bucketFor(updatedAt: string): string {
    const now = Date.now();
    const ts = Date.parse(updatedAt);
    if (Number.isNaN(ts)) return 'Older';
    const age = now - ts;
    if (age < DAY_MS) return 'Today';
    if (age < 2 * DAY_MS) return 'Yesterday';
    if (age < 7 * DAY_MS) return 'This week';
    if (age < 30 * DAY_MS) return 'This month';
    if (age < 90 * DAY_MS) return 'Last 3 months';
    return 'Older';
}

const ORDER = [
    'Today',
    'Yesterday',
    'This week',
    'This month',
    'Last 3 months',
    'Older',
];

const grouped = computed(() => {
    const groups: Record<string, NoteTreeNode[]> = {};
    for (const note of rootNotes.value) {
        const label = bucketFor(note.updated_at);
        (groups[label] ??= []).push(note);
    }
    return ORDER.filter((k) => groups[k]?.length).map((k) => ({
        label: k,
        items: groups[k]!,
    }));
});

function relative(iso: string): string {
    const ts = Date.parse(iso);
    if (Number.isNaN(ts)) return '';
    const diff = Date.now() - ts;
    const m = Math.floor(diff / 60_000);
    const h = Math.floor(m / 60);
    const d = Math.floor(h / 24);
    if (d > 0) return `${d}d ago`;
    if (h > 0) return `${h}h ago`;
    if (m > 0) return `${m}m ago`;
    return 'just now';
}

function openNote(id: number) {
    router.push(`/notes?note=${id}`);
}

function titleOf(note: NoteTreeNode): string {
    const first = note.content.split('\n')[0]?.trim();
    return first || 'Untitled';
}
</script>

<template>
    <div class="mx-auto max-w-3xl px-4 py-6">
        <div
            class="text-surface-400 text-[10px] font-semibold tracking-[0.2em] uppercase"
        >
            Timeline
        </div>
        <h1
            class="text-surface-900 dark:text-surface-100 mt-1 text-2xl font-semibold tracking-tight"
        >
            What you've been working on
        </h1>

        <div
            v-if="!rootNotes.length"
            class="text-surface-500 mt-6 text-sm italic"
        >
            No notes yet.
        </div>

        <div v-for="group in grouped" :key="group.label" class="mt-6">
            <div
                class="text-primary-500 mb-2 text-[10px] font-semibold tracking-widest uppercase"
            >
                {{ group.label }}
            </div>
            <div class="relative pl-5">
                <div
                    class="bg-surface-200 dark:bg-surface-700 absolute top-0 bottom-0 left-1 w-px"
                ></div>
                <button
                    v-for="note in group.items"
                    :key="note.id"
                    class="group relative mb-3 block w-full text-left"
                    @click="openNote(note.id)"
                >
                    <span
                        class="bg-primary-400 absolute top-1.5 -left-[17px] h-2 w-2 rounded-full"
                    ></span>
                    <div class="flex items-baseline gap-2">
                        <span
                            class="text-surface-900 dark:text-surface-100 group-hover:text-primary-500 text-sm font-semibold transition-colors"
                        >
                            {{ titleOf(note) }}
                        </span>
                        <span
                            class="text-surface-400 ml-auto text-[10px] tracking-wider"
                        >
                            {{ relative(note.updated_at) }}
                        </span>
                    </div>
                </button>
            </div>
        </div>
    </div>
</template>
