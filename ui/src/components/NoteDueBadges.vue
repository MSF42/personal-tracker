<script setup lang="ts">
import type { NoteTreeNode, RecurrenceType } from '@/types/Note';

defineProps<{ node: NoteTreeNode }>();

const emit = defineEmits<{
    'edit-due': [];
    'cycle-recurrence': [];
    complete: [];
}>();

function recurrenceLabel(r: RecurrenceType | null | undefined): string {
    return r ?? '';
}
</script>

<template>
    <div
        v-if="node.due_date || node.recurrence_type"
        class="mt-1 flex shrink-0 items-center gap-1"
    >
        <button
            v-if="node.due_date"
            class="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] text-emerald-700 hover:bg-emerald-200 dark:bg-emerald-900/60 dark:text-emerald-300 dark:hover:bg-emerald-900"
            :title="
                node.recurrence_type
                    ? `Complete & roll forward (${node.recurrence_type})`
                    : 'Complete (clear due date)'
            "
            @click.stop="emit('complete')"
        >
            ✓
        </button>
        <button
            v-if="node.due_date"
            class="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] text-amber-700 hover:bg-amber-200 dark:bg-amber-900/60 dark:text-amber-300 dark:hover:bg-amber-900"
            @click.stop="emit('edit-due')"
        >
            ◆ {{ node.due_date }}
        </button>
        <button
            v-if="node.recurrence_type"
            class="bg-surface-100 text-surface-500 hover:bg-surface-200 dark:bg-surface-800 dark:text-surface-400 dark:hover:bg-surface-700 rounded px-1.5 py-0.5 text-[10px]"
            @click.stop="emit('cycle-recurrence')"
        >
            ↻ {{ recurrenceLabel(node.recurrence_type) }}
        </button>
    </div>
</template>
