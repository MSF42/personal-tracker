<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';

import { useRunningApi } from '@/composables/api/useRunningApi';
import { useTaskApi } from '@/composables/api/useTaskApi';
import { useBadgeAnnouncer } from '@/composables/useBadgeAnnouncer';
import { useFileDrop } from '@/composables/useFileDrop';
import { completeTasksLinkedToRun } from '@/composables/useTaskLinks';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type { RunningActivity } from '@/types/Running';
import { fromIsoDate, toIsoDate } from '@/utils/week';

const props = withDefaults(
    defineProps<{ run: RunningActivity | null; defaultDate?: string | null }>(),
    { defaultDate: null },
);
// `saved` carries the run's id so a caller can jump to its detail page.
const emit = defineEmits<{ saved: [runId: number] }>();
const visible = defineModel<boolean>('visible', { required: true });

const { createActivity, updateActivity, importGpx, importFit } =
    useRunningApi();
const { getTasks, updateTask } = useTaskApi();
const toast = useToast();
const { announceBadges } = useBadgeAnnouncer();
const { distanceUnit, toKm, fromKm } = useUnits();

const formError = ref('');
const isFormValid = computed(() => form.date.trim() !== '');
const saveTooltip = computed(() =>
    isFormValid.value ? undefined : 'Date is required',
);
const dialogHeader = computed(() => (props.run ? 'Edit Run' : 'Add Run'));

const form = reactive({
    date: toIsoDate(new Date()),
    title: '',
    minutes: 0,
    seconds: 0,
    distance_km: 0,
    notes: '',
});
// AppDatePicker binds to a Date; form.date stays a plain ISO string.
const dateModel = computed<Date | null>({
    get: () => (form.date ? fromIsoDate(form.date) : null),
    set: (value) => {
        form.date = value ? toIsoDate(value) : '';
    },
});

// Populate the form whenever the dialog opens: reset for "add", or load the
// run being edited. `editingId` state lives entirely in the parent — this
// dialog is a plain form over the `run` prop.
watch(visible, (isVisible) => {
    if (!isVisible) return;
    formError.value = '';
    const run = props.run;
    if (run) {
        form.date = run.date;
        form.title = run.title ?? '';
        form.minutes = Math.floor(run.duration_seconds / 60);
        form.seconds = run.duration_seconds % 60;
        form.distance_km = parseFloat(fromKm(run.distance_km).toFixed(2));
        form.notes = run.notes ?? '';
    } else {
        form.date = props.defaultDate ?? toIsoDate(new Date());
        form.title = '';
        form.minutes = 0;
        form.seconds = 0;
        form.distance_km = 0;
        form.notes = '';
    }
});

async function save() {
    formError.value = '';
    const payload = {
        date: form.date,
        duration_seconds: form.minutes * 60 + form.seconds,
        distance_km: toKm(form.distance_km),
        notes: form.notes || null,
        title: form.title || null,
    };
    const res = props.run
        ? await updateActivity(props.run.id, payload)
        : await createActivity(payload);
    if (res.success && res.data) {
        toast.showSuccess(props.run ? 'Run updated' : 'Run added');
        // A brand-new run on a given day satisfies any "run" task due that day.
        if (!props.run) {
            await completeTasksLinkedToRun(getTasks, updateTask, res.data.date);
            void announceBadges([res.data]);
        }
        visible.value = false;
        emit('saved', res.data.id);
    } else {
        formError.value = res.error?.message ?? 'Failed to save run';
    }
}

// --- Import GPX/FIT ---------------------------------------------------------
// A single-file quick import, for entering one run from a device file
// without leaving this dialog. The Running list page's own toolbar keeps its
// separate multi-file bulk-import flow untouched.
const importFileInput = ref<HTMLInputElement | null>(null);

function triggerImport() {
    importFileInput.value?.click();
}

async function importOneFile(file: File) {
    formError.value = '';
    const isFit = file.name.toLowerCase().endsWith('.fit');
    const res = isFit ? await importFit(file) : await importGpx(file);
    if (res.success && res.data) {
        toast.showSuccess('Run imported');
        await completeTasksLinkedToRun(
            getTasks,
            updateTask,
            res.data.activity.date,
        );
        void announceBadges([res.data.activity]);
        visible.value = false;
        emit('saved', res.data.activity.id);
    } else if (res.error?.code === 'CONFLICT') {
        toast.showWarning(
            'Already imported',
            'This file matches a run that’s already in your log.',
        );
    } else {
        formError.value = res.error?.message ?? 'Import failed';
    }
}

async function handleImportFile(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (file) await importOneFile(file);
}

// Drag a .gpx/.fit file onto the dialog as a shortcut for the picker above —
// only one file is used (this dialog adds a single run), matching how it
// only ever imports one file via the button too. Only live in add mode with
// import support, same gate as the button/input above.
const canImportViaDrop = computed(() => !props.run);
const {
    isOver: isFileDragOver,
    onDragEnter,
    onDragOver,
    onDragLeave,
    onFileDrop,
} = useFileDrop((files) => void importOneFile(files[0]!), ['.gpx', '.fit']);

function onDialogDragEnter(e: DragEvent) {
    if (canImportViaDrop.value) onDragEnter(e);
}
function onDialogDragOver(e: DragEvent) {
    if (canImportViaDrop.value) onDragOver(e);
}
function onDialogDragLeave(e: DragEvent) {
    if (canImportViaDrop.value) onDragLeave(e);
}
function onDialogDrop(e: DragEvent) {
    if (canImportViaDrop.value) onFileDrop(e);
}
</script>

<template>
    <AppDialog
        v-model:visible="visible"
        :header="dialogHeader"
        modal
        :style="{ width: '28rem', maxWidth: '92vw' }"
    >
        <div
            class="relative flex flex-col gap-4"
            @dragenter="onDialogDragEnter"
            @dragleave="onDialogDragLeave"
            @dragover="onDialogDragOver"
            @drop="onDialogDrop"
        >
            <div
                v-if="isFileDragOver"
                class="border-primary-400 bg-surface-0/90 dark:bg-surface-900/90 pointer-events-none absolute -inset-2 z-10 flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed"
            >
                <i class="pi pi-upload text-primary-500 text-2xl"></i>
                <p class="text-sm font-medium">Drop to import</p>
            </div>
            <div v-if="!run" class="flex flex-col gap-3">
                <AppButton
                    icon="pi pi-upload"
                    label="Import GPX / FIT"
                    outlined
                    @click="triggerImport"
                />
                <p class="text-surface-400 -mt-1.5 text-center text-xs">
                    or drag a file onto this window
                </p>
                <input
                    ref="importFileInput"
                    accept=".gpx,.fit"
                    class="hidden"
                    type="file"
                    @change="handleImportFile"
                />
                <div class="text-surface-400 flex items-center gap-2 text-xs">
                    <div
                        class="border-surface-200 dark:border-surface-700 h-px flex-1 border-t"
                    ></div>
                    or enter manually
                    <div
                        class="border-surface-200 dark:border-surface-700 h-px flex-1 border-t"
                    ></div>
                </div>
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium">
                    Date <span class="text-red-500">*</span>
                </label>
                <AppDatePicker
                    v-model="dateModel"
                    date-format="yy M dd"
                    fluid
                    icon-display="input"
                    show-icon
                />
                <p v-if="formError" class="mt-1 text-sm text-red-500">
                    {{ formError }}
                </p>
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium">Title</label>
                <AppInputText
                    v-model="form.title"
                    class="w-full"
                    placeholder="e.g. Morning Run"
                />
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium">
                    Distance ({{ distanceUnit }})
                </label>
                <AppInputNumber
                    v-model="form.distance_km"
                    class="w-full"
                    :max-fraction-digits="2"
                    :min-fraction-digits="1"
                    :step="0.1"
                    :suffix="' ' + distanceUnit"
                />
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium">Duration</label>
                <div class="flex items-center gap-2">
                    <AppInputNumber
                        v-model="form.minutes"
                        class="min-w-0 flex-1"
                        fluid
                        :min="0"
                        suffix=" min"
                    />
                    <AppInputNumber
                        v-model="form.seconds"
                        class="min-w-0 flex-1"
                        fluid
                        :max="59"
                        :min="0"
                        suffix=" sec"
                    />
                </div>
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium">Notes</label>
                <AppTextarea v-model="form.notes" class="w-full" rows="2" />
            </div>
            <div class="flex justify-end gap-2">
                <AppButton label="Cancel" text @click="visible = false" />
                <span v-tooltip.top="saveTooltip">
                    <AppButton
                        :disabled="!isFormValid"
                        label="Save"
                        @click="save"
                    />
                </span>
            </div>
        </div>
    </AppDialog>
</template>
