<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import ConfirmDeleteDialog from '@/components/ConfirmDeleteDialog.vue';
import LoadingState from '@/components/LoadingState.vue';
import { useMeasurementApi } from '@/composables/api/useMeasurementApi';
import { useLoading } from '@/composables/useLoading';
import { useToast } from '@/composables/useToast';
import type { Measurement, MeasurementEntry } from '@/types/Measurement';
import { registerCharts } from '@/utils/chart';
import { formatDate } from '@/utils/format';
import { fromIsoDate, toIsoDate } from '@/utils/week';

registerCharts();

const {
    getMeasurements,
    createMeasurement,
    updateMeasurement,
    deleteMeasurement,
    getEntries,
    createEntry,
    updateEntry,
    deleteEntry,
} = useMeasurementApi();
const toast = useToast();
const { loading, withLoading } = useLoading();

const measurements = ref<Measurement[]>([]);
const selectedId = ref<number | null>(null);
const entries = ref<MeasurementEntry[]>([]);

const selectedMeasurement = computed(() =>
    measurements.value.find((m) => m.id === selectedId.value),
);

// --- Add/Edit Measurement Dialog ---
const showMeasurementDialog = ref(false);
const editingMeasurementId = ref<number | null>(null);
const measurementForm = reactive({ name: '', unit: '' });
const measurementFormError = ref('');

const isMeasurementFormValid = computed(
    () => measurementForm.name.trim() !== '',
);
const measurementSaveTooltip = computed(() =>
    isMeasurementFormValid.value ? undefined : 'Name is required',
);
const measurementDialogHeader = computed(() =>
    editingMeasurementId.value ? 'Edit Measurement' : 'Add Measurement',
);

function openAddMeasurement() {
    editingMeasurementId.value = null;
    measurementForm.name = '';
    measurementForm.unit = '';
    measurementFormError.value = '';
    showMeasurementDialog.value = true;
}

function openEditMeasurement() {
    if (!selectedMeasurement.value) return;
    editingMeasurementId.value = selectedMeasurement.value.id;
    measurementForm.name = selectedMeasurement.value.name;
    measurementForm.unit = selectedMeasurement.value.unit;
    measurementFormError.value = '';
    showMeasurementDialog.value = true;
}

async function saveMeasurementForm() {
    measurementFormError.value = '';
    if (editingMeasurementId.value) {
        const res = await updateMeasurement(editingMeasurementId.value, {
            name: measurementForm.name,
            unit: measurementForm.unit,
        });
        if (res.success) {
            toast.showSuccess('Measurement updated');
            showMeasurementDialog.value = false;
            await loadMeasurements();
        } else {
            measurementFormError.value =
                res.error?.message ?? 'Something went wrong';
        }
    } else {
        const res = await createMeasurement({
            name: measurementForm.name,
            unit: measurementForm.unit,
        });
        if (res.success && res.data) {
            toast.showSuccess('Measurement added');
            showMeasurementDialog.value = false;
            await loadMeasurements();
            await selectMeasurement(res.data.id);
        } else {
            measurementFormError.value =
                res.error?.message ?? 'Something went wrong';
        }
    }
}

// --- Delete Measurement ---
const showDeleteMeasurement = ref(false);

async function confirmDeleteMeasurement() {
    if (!selectedId.value) return;
    const res = await deleteMeasurement(selectedId.value);
    if (res.success) {
        toast.showSuccess('Measurement deleted');
        showDeleteMeasurement.value = false;
        await loadMeasurements();
        if (measurements.value.length > 0) {
            await selectMeasurement(measurements.value[0]!.id);
        } else {
            selectedId.value = null;
            entries.value = [];
        }
    } else {
        toast.showError(res.error?.message ?? 'Failed to delete measurement');
    }
}

// --- Entry Dialog ---
const showEntryDialog = ref(false);
const editingEntryId = ref<number | null>(null);
const today = new Date().toISOString().split('T')[0] as string;
const entryForm = reactive({
    date: today,
    value: null as number | null,
    notes: '',
});
const entryFormError = ref('');
const isEntryFormValid = computed(
    () => entryForm.date !== '' && entryForm.value !== null,
);
const entrySaveTooltip = computed(() => {
    if (entryForm.date === '') return 'Date is required';
    if (entryForm.value === null) return 'Value is required';
    return undefined;
});
// AppDatePicker binds to a Date; entryForm.date stays a plain ISO string.
const entryDateModel = computed<Date | null>({
    get: () => (entryForm.date ? fromIsoDate(entryForm.date) : null),
    set: (value) => {
        entryForm.date = value ? toIsoDate(value) : '';
    },
});

function openAddEntry() {
    editingEntryId.value = null;
    entryForm.date = today;
    entryForm.value = null;
    entryForm.notes = '';
    entryFormError.value = '';
    showEntryDialog.value = true;
}

function openEditEntry(entry: MeasurementEntry) {
    editingEntryId.value = entry.id;
    entryForm.date = entry.date;
    entryForm.value = entry.value;
    entryForm.notes = entry.notes ?? '';
    entryFormError.value = '';
    showEntryDialog.value = true;
}

async function saveEntry() {
    if (!selectedId.value || entryForm.value === null) return;
    const value = entryForm.value;
    entryFormError.value = '';
    if (editingEntryId.value) {
        const res = await updateEntry(editingEntryId.value, {
            date: entryForm.date,
            value,
            notes: entryForm.notes || null,
        });
        if (res.success) {
            toast.showSuccess('Entry updated');
            showEntryDialog.value = false;
            await loadEntries();
        } else {
            entryFormError.value = res.error?.message ?? 'Something went wrong';
        }
    } else {
        const res = await createEntry(selectedId.value, {
            date: entryForm.date,
            value,
            notes: entryForm.notes || null,
        });
        if (res.success) {
            toast.showSuccess('Entry added');
            showEntryDialog.value = false;
            await loadEntries();
        } else {
            entryFormError.value = res.error?.message ?? 'Something went wrong';
        }
    }
}

// --- Delete Entry ---
const showDeleteEntry = ref(false);
const deletingEntryId = ref<number | null>(null);

function confirmDeleteEntry(id: number) {
    deletingEntryId.value = id;
    showDeleteEntry.value = true;
}

async function executeDeleteEntry() {
    if (!deletingEntryId.value) return;
    const res = await deleteEntry(deletingEntryId.value);
    if (res.success) {
        toast.showSuccess('Entry deleted');
    } else {
        toast.showError(res.error?.message ?? 'Failed to delete entry');
    }
    showDeleteEntry.value = false;
    deletingEntryId.value = null;
    await loadEntries();
}

// --- Reorder measurements ---
const canMoveEarlier = computed(() => {
    if (!selectedId.value) return false;
    return measurements.value.findIndex((m) => m.id === selectedId.value) > 0;
});
const canMoveLater = computed(() => {
    if (!selectedId.value) return false;
    const idx = measurements.value.findIndex((m) => m.id === selectedId.value);
    return idx !== -1 && idx < measurements.value.length - 1;
});

async function moveMeasurement(direction: -1 | 1) {
    if (!selectedId.value) return;
    const idx = measurements.value.findIndex((m) => m.id === selectedId.value);
    const swapIdx = idx + direction;
    if (idx === -1 || swapIdx < 0 || swapIdx >= measurements.value.length)
        return;
    const current = measurements.value[idx]!;
    const neighbor = measurements.value[swapIdx]!;
    const [resCurrent, resNeighbor] = await Promise.all([
        updateMeasurement(current.id, { sort_order: neighbor.sort_order }),
        updateMeasurement(neighbor.id, { sort_order: current.sort_order }),
    ]);
    if (resCurrent.success && resNeighbor.success) {
        await loadMeasurements();
    } else {
        toast.showError('Failed to reorder measurements');
    }
}

// --- Export entries as CSV ---
function csvField(value: string): string {
    return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}

function exportEntriesCsv() {
    if (!selectedMeasurement.value) return;
    const unit = selectedMeasurement.value.unit;
    const header = ['Date', unit ? `Value (${unit})` : 'Value', 'Notes'];
    const rows = [...entries.value]
        .sort((a, b) => a.date.localeCompare(b.date))
        .map((e) => [e.date, String(e.value), e.notes ?? '']);
    const csv = [header, ...rows]
        .map((row) => row.map(csvField).join(','))
        .join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${selectedMeasurement.value.name}.csv`;
    link.click();
    URL.revokeObjectURL(url);
}

// --- Chart ---
// Points sit on a numeric (real-time) x-axis rather than a category axis of
// formatted date labels — a category axis spaces entries evenly by count,
// which is wrong whenever entries aren't evenly spaced in time (e.g. daily
// for a week, then a two-week gap).
const chartData = computed(() => {
    const sorted = [...entries.value].sort((a, b) =>
        a.date.localeCompare(b.date),
    );
    const unit = selectedMeasurement.value?.unit ?? '';
    return {
        datasets: [
            {
                label: unit ? `Value (${unit})` : 'Value',
                data: sorted.map((e) => ({
                    x: fromIsoDate(e.date).getTime(),
                    y: e.value,
                })),
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                fill: true,
                tension: 0.3,
            },
        ],
    };
});

const chartOptions = computed(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
        x: {
            type: 'linear' as const,
            ticks: {
                callback: (value: number) =>
                    formatDate(toIsoDate(new Date(value))),
            },
        },
        y: {
            title: {
                display: true,
                text: selectedMeasurement.value?.unit || 'Value',
            },
        },
    },
}));

// --- Data Loading ---
async function loadMeasurements() {
    const res = await getMeasurements();
    if (res.success && res.data) {
        measurements.value = res.data;
    } else if (!res.success) {
        toast.showError('Failed to load measurements');
    }
}

async function loadEntries() {
    if (!selectedId.value) {
        entries.value = [];
        return;
    }
    const res = await getEntries(selectedId.value);
    if (res.success && res.data) {
        entries.value = res.data;
    }
}

async function selectMeasurement(id: number) {
    selectedId.value = id;
    entries.value = [];
    await loadEntries();
}

onMounted(() =>
    withLoading(async () => {
        await loadMeasurements();
        if (measurements.value.length > 0) {
            await selectMeasurement(measurements.value[0]!.id);
        }
    }),
);

const entryDialogHeader = computed(() =>
    editingEntryId.value ? 'Edit Entry' : 'Add Entry',
);
</script>

<template>
    <div class="mx-auto max-w-6xl p-6">
        <div class="mb-6 flex items-center justify-between">
            <h1 class="text-2xl font-bold">Measurements</h1>
            <AppButton
                icon="pi pi-plus"
                label="Add Measurement"
                @click="openAddMeasurement"
            />
        </div>

        <LoadingState v-if="loading" label="Loading measurements…" />

        <!-- Measurement Tabs -->
        <div
            v-else-if="measurements.length"
            class="mb-6 flex flex-wrap items-center gap-2"
            role="tablist"
        >
            <AppButton
                v-for="m in measurements"
                :key="m.id"
                :aria-selected="selectedId === m.id"
                :label="m.name"
                :outlined="selectedId !== m.id"
                role="tab"
                size="small"
                @click="selectMeasurement(m.id)"
            />
            <AppButton
                v-if="selectedMeasurement"
                aria-label="Move earlier"
                :disabled="!canMoveEarlier"
                icon="pi pi-arrow-left"
                rounded
                severity="secondary"
                size="small"
                text
                title="Move earlier"
                @click="moveMeasurement(-1)"
            />
            <AppButton
                v-if="selectedMeasurement"
                aria-label="Move later"
                :disabled="!canMoveLater"
                icon="pi pi-arrow-right"
                rounded
                severity="secondary"
                size="small"
                text
                title="Move later"
                @click="moveMeasurement(1)"
            />
            <AppButton
                v-if="selectedMeasurement"
                aria-label="Edit measurement"
                icon="pi pi-pencil"
                rounded
                severity="secondary"
                size="small"
                text
                @click="openEditMeasurement"
            />
            <AppButton
                v-if="selectedMeasurement"
                aria-label="Delete measurement"
                icon="pi pi-trash"
                rounded
                severity="danger"
                size="small"
                text
                @click="showDeleteMeasurement = true"
            />
        </div>

        <div v-else class="flex flex-col items-center py-10 text-center">
            <i
                class="pi pi-inbox text-surface-300 dark:text-surface-600 mb-3 text-4xl"
            ></i>
            <p class="text-surface-500 mb-3">No measurements yet</p>
            <AppButton
                icon="pi pi-plus"
                label="Add your first measurement"
                size="small"
                @click="openAddMeasurement"
            />
        </div>

        <!-- Selected measurement view -->
        <template v-if="selectedMeasurement">
            <!-- Chart -->
            <div v-if="entries.length > 1" class="mb-6">
                <h2 class="mb-3 text-xl font-semibold">
                    {{ selectedMeasurement.name }} Over Time
                </h2>
                <div class="h-64">
                    <AppChart
                        :data="chartData"
                        :options="chartOptions"
                        type="line"
                    />
                </div>
            </div>

            <!-- Entry Table Header -->
            <div class="mb-4 flex items-center justify-between">
                <h2 class="text-xl font-semibold">
                    {{ selectedMeasurement.name }} Log
                </h2>
                <div class="flex gap-2">
                    <AppButton
                        v-if="entries.length > 0"
                        icon="pi pi-download"
                        label="Export CSV"
                        outlined
                        severity="secondary"
                        @click="exportEntriesCsv"
                    />
                    <AppButton
                        icon="pi pi-plus"
                        label="Add Entry"
                        @click="openAddEntry"
                    />
                </div>
            </div>

            <!-- Entries Table -->
            <AppDataTable
                sort-field="date"
                :sort-order="-1"
                striped-rows
                :value="entries"
            >
                <template #empty>
                    <div class="flex flex-col items-center py-10 text-center">
                        <i
                            class="pi pi-inbox text-surface-300 dark:text-surface-600 mb-3 text-4xl"
                        ></i>
                        <p class="text-surface-500 mb-3">No entries yet</p>
                        <AppButton
                            icon="pi pi-plus"
                            label="Add your first entry"
                            size="small"
                            @click="openAddEntry"
                        />
                    </div>
                </template>
                <AppColumn field="date" header="Date" sortable>
                    <template #body="{ data }">
                        {{ formatDate((data as MeasurementEntry).date) }}
                    </template>
                </AppColumn>
                <AppColumn field="value" header="Value" sortable>
                    <template #body="{ data }">
                        {{ (data as MeasurementEntry).value }}
                        {{ selectedMeasurement.unit }}
                    </template>
                </AppColumn>
                <AppColumn field="notes" header="Notes" />
                <AppColumn header="Actions" style="width: 6rem">
                    <template #body="{ data }">
                        <div class="flex gap-2">
                            <AppButton
                                aria-label="Edit entry"
                                icon="pi pi-pencil"
                                rounded
                                severity="info"
                                text
                                @click="openEditEntry(data as MeasurementEntry)"
                            />
                            <AppButton
                                aria-label="Delete entry"
                                icon="pi pi-trash"
                                rounded
                                severity="danger"
                                text
                                @click="
                                    confirmDeleteEntry(
                                        (data as MeasurementEntry).id,
                                    )
                                "
                            />
                        </div>
                    </template>
                </AppColumn>
            </AppDataTable>
        </template>

        <!-- Add/Edit Measurement Dialog -->
        <AppDialog
            v-model:visible="showMeasurementDialog"
            :header="measurementDialogHeader"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Name <span class="text-red-500">*</span>
                    </label>
                    <AppInputText
                        v-model="measurementForm.name"
                        class="w-full"
                        placeholder="e.g. Waist"
                    />
                    <p
                        v-if="measurementFormError"
                        class="mt-1 text-sm text-red-500"
                    >
                        {{ measurementFormError }}
                    </p>
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium"> Unit </label>
                    <AppInputText
                        v-model="measurementForm.unit"
                        class="w-full"
                        placeholder="e.g. inches"
                    />
                    <p class="text-surface-400 mt-1 text-xs">
                        Free-form text, independent of the units set in
                        Settings.
                    </p>
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showMeasurementDialog = false"
                    />
                    <span v-tooltip.top="measurementSaveTooltip">
                        <AppButton
                            :disabled="!isMeasurementFormValid"
                            label="Save"
                            @click="saveMeasurementForm"
                        />
                    </span>
                </div>
            </div>
        </AppDialog>

        <!-- Add/Edit Entry Dialog -->
        <AppDialog
            v-model:visible="showEntryDialog"
            :header="entryDialogHeader"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium"> Date </label>
                    <AppDatePicker
                        v-model="entryDateModel"
                        date-format="yy M dd"
                        fluid
                        icon-display="input"
                        show-icon
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Value <span class="text-red-500">*</span>
                        <span
                            v-if="selectedMeasurement?.unit"
                            class="text-surface-400"
                        >
                            ({{ selectedMeasurement.unit }})
                        </span>
                    </label>
                    <AppInputNumber
                        v-model="entryForm.value"
                        class="w-full"
                        :max-fraction-digits="2"
                        placeholder="Enter a value"
                        :step="0.1"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Notes
                    </label>
                    <AppTextarea
                        v-model="entryForm.notes"
                        class="w-full"
                        rows="2"
                    />
                </div>
                <p v-if="entryFormError" class="text-sm text-red-500">
                    {{ entryFormError }}
                </p>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showEntryDialog = false"
                    />
                    <span v-tooltip.top="entrySaveTooltip">
                        <AppButton
                            :disabled="!isEntryFormValid"
                            label="Save"
                            @click="saveEntry"
                        />
                    </span>
                </div>
            </div>
        </AppDialog>

        <!-- Delete Measurement Confirmation -->
        <ConfirmDeleteDialog
            v-model:visible="showDeleteMeasurement"
            @confirm="confirmDeleteMeasurement"
        >
            Delete
            <strong>{{ selectedMeasurement?.name }}</strong>
            and all its entries?
        </ConfirmDeleteDialog>

        <!-- Delete Entry Confirmation -->
        <ConfirmDeleteDialog
            v-model:visible="showDeleteEntry"
            @confirm="executeDeleteEntry"
        >
            Are you sure you want to delete this entry?
        </ConfirmDeleteDialog>
    </div>
</template>
