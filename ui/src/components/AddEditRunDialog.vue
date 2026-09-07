<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';

import { useRunningApi } from '@/composables/api/useRunningApi';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type { RunningActivity } from '@/types/Running';
import { toIsoDate } from '@/utils/week';

const props = withDefaults(
    defineProps<{ run: RunningActivity | null; defaultDate?: string | null }>(),
    { defaultDate: null },
);
const emit = defineEmits<{ saved: [] }>();
const visible = defineModel<boolean>('visible', { required: true });

const { createActivity, updateActivity, importGpx, importFit } =
    useRunningApi();
const toast = useToast();
const { distanceUnit, toKm, fromKm } = useUnits();

// The local/offline backend has no Python GPX/FIT parser to import with —
// hide the button there rather than show one that can only fail.
const importSupported = import.meta.env.VITE_BACKEND !== 'local';

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
    if (res.success) {
        toast.showSuccess(props.run ? 'Run updated' : 'Run added');
        visible.value = false;
        emit('saved');
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

async function handleImportFile(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;

    formError.value = '';
    const isFit = file.name.toLowerCase().endsWith('.fit');
    const res = isFit ? await importFit(file) : await importGpx(file);
    if (res.success && res.data) {
        toast.showSuccess('Run imported');
        visible.value = false;
        emit('saved');
    } else if (res.error?.code === 'CONFLICT') {
        toast.showWarning(
            'Already imported',
            'This file matches a run that’s already in your log.',
        );
    } else {
        formError.value = res.error?.message ?? 'Import failed';
    }
}
</script>

<template>
    <AppDialog
        v-model:visible="visible"
        :header="dialogHeader"
        modal
        :style="{ width: '28rem', maxWidth: '92vw' }"
    >
        <div class="flex flex-col gap-4">
            <div v-if="!run && importSupported" class="flex flex-col gap-3">
                <AppButton
                    icon="pi pi-upload"
                    label="Import GPX / FIT"
                    outlined
                    @click="triggerImport"
                />
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
                <AppInputText v-model="form.date" class="w-full" type="date" />
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
