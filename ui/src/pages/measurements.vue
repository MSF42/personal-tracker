<script setup lang="ts">
import {
    CategoryScale,
    Chart,
    Filler,
    Legend,
    LinearScale,
    LineController,
    LineElement,
    PointElement,
    Title,
    Tooltip,
} from 'chart.js';
import { computed, onMounted, reactive, ref } from 'vue';

import { useMeasurementApi } from '@/composables/api/useMeasurementApi';
import { useToast } from '@/composables/useToast';
import type { Measurement, MeasurementEntry } from '@/types/Measurement';
import { formatDate } from '@/utils/format';

Chart.register(
    CategoryScale,
    Filler,
    Legend,
    LinearScale,
    LineController,
    LineElement,
    PointElement,
    Title,
    Tooltip,
);

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

const measurements = ref<Measurement[]>([]);
const selectedId = ref<number | null>(null);
const entries = ref<MeasurementEntry[]>([]);

const selectedMeasurement = computed(() =>
    measurements.value.find((m) => m.id === selectedId.value),
);

// --- Add Measurement Dialog ---
const showAddMeasurement = ref(false);
const measurementForm = reactive({ name: '', unit: '' });
const addMeasurementError = ref('');

function openAddMeasurement() {
    measurementForm.name = '';
    measurementForm.unit = '';
    addMeasurementError.value = '';
    showAddMeasurement.value = true;
}

async function saveMeasurement() {
    addMeasurementError.value = '';
    if (!measurementForm.name.trim()) {
        addMeasurementError.value = 'Name is required';
        return;
    }
    const res = await createMeasurement({
        name: measurementForm.name,
        unit: measurementForm.unit,
    });
    if (res.success && res.data) {
        toast.showSuccess('Measurement added');
        showAddMeasurement.value = false;
        await loadMeasurements();
        await selectMeasurement(res.data.id);
    } else if (!res.success) {
        addMeasurementError.value = res.error?.message ?? 'Something went wrong';
    }
}

// --- Edit Measurement Dialog ---
const showEditMeasurement = ref(false);
const editMeasurementForm = reactive({ name: '', unit: '' });
const editMeasurementError = ref('');

function openEditMeasurement() {
    if (!selectedMeasurement.value) return;
    editMeasurementForm.name = selectedMeasurement.value.name;
    editMeasurementForm.unit = selectedMeasurement.value.unit;
    editMeasurementError.value = '';
    showEditMeasurement.value = true;
}

async function saveEditMeasurement() {
    if (!selectedId.value) return;
    editMeasurementError.value = '';
    if (!editMeasurementForm.name.trim()) {
        editMeasurementError.value = 'Name is required';
        return;
    }
    const res = await updateMeasurement(selectedId.value, {
        name: editMeasurementForm.name,
        unit: editMeasurementForm.unit,
    });
    if (res.success) {
        toast.showSuccess('Measurement updated');
        showEditMeasurement.value = false;
        await loadMeasurements();
    } else {
        editMeasurementError.value = res.error?.message ?? 'Something went wrong';
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
    }
}

// --- Entry Dialog ---
const showEntryDialog = ref(false);
const editingEntryId = ref<number | null>(null);
const today = new Date().toISOString().split('T')[0] as string;
const entryForm = reactive({
    date: today,
    value: 0,
    notes: '',
});
const entryFormError = ref('');

function openAddEntry() {
    editingEntryId.value = null;
    entryForm.date = today;
    entryForm.value = 0;
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
    if (!selectedId.value) return;
    entryFormError.value = '';
    if (editingEntryId.value) {
        const res = await updateEntry(editingEntryId.value, {
            date: entryForm.date,
            value: entryForm.value,
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
            value: entryForm.value,
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
    }
    showDeleteEntry.value = false;
    deletingEntryId.value = null;
    await loadEntries();
}

// --- Chart ---
const chartData = computed(() => {
    const sorted = [...entries.value].sort((a, b) =>
        a.date.localeCompare(b.date),
    );
    const unit = selectedMeasurement.value?.unit ?? '';
    return {
        labels: sorted.map((e) => formatDate(e.date)),
        datasets: [
            {
                label: unit ? `Value (${unit})` : 'Value',
                data: sorted.map((e) => e.value),
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

onMounted(async () => {
    await loadMeasurements();
    if (measurements.value.length > 0) {
        await selectMeasurement(measurements.value[0]!.id);
    }
});

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

        <!-- Measurement Tabs -->
        <div
            v-if="measurements.length"
            class="mb-6 flex flex-wrap items-center gap-2"
        >
            <AppButton
                v-for="m in measurements"
                :key="m.id"
                :label="m.name"
                :outlined="selectedId !== m.id"
                size="small"
                @click="selectMeasurement(m.id)"
            />
            <AppButton
                v-if="selectedMeasurement"
                icon="pi pi-pencil"
                rounded
                severity="secondary"
                size="small"
                text
                @click="openEditMeasurement"
            />
            <AppButton
                v-if="selectedMeasurement"
                icon="pi pi-trash"
                rounded
                severity="danger"
                size="small"
                text
                @click="showDeleteMeasurement = true"
            />
        </div>

        <div
            v-if="!measurements.length"
            class="text-surface-500 py-12 text-center"
        >
            No measurements yet. Add one to get started.
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
                <AppButton
                    icon="pi pi-plus"
                    label="Add Entry"
                    @click="openAddEntry"
                />
            </div>

            <!-- Entries Table -->
            <AppDataTable
                sort-field="date"
                :sort-order="-1"
                striped-rows
                :value="entries"
            >
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
                                icon="pi pi-pencil"
                                rounded
                                severity="info"
                                text
                                @click="openEditEntry(data as MeasurementEntry)"
                            />
                            <AppButton
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

        <!-- Add Measurement Dialog -->
        <AppDialog
            v-model:visible="showAddMeasurement"
            header="Add Measurement"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium"> Name </label>
                    <AppInputText
                        v-model="measurementForm.name"
                        class="w-full"
                        placeholder="e.g. Waist"
                    />
                    <p
                        v-if="addMeasurementError"
                        class="mt-1 text-sm text-red-500"
                    >
                        {{ addMeasurementError }}
                    </p>
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium"> Unit </label>
                    <AppInputText
                        v-model="measurementForm.unit"
                        class="w-full"
                        placeholder="e.g. inches"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showAddMeasurement = false"
                    />
                    <AppButton label="Save" @click="saveMeasurement" />
                </div>
            </div>
        </AppDialog>

        <!-- Edit Measurement Dialog -->
        <AppDialog
            v-model:visible="showEditMeasurement"
            header="Edit Measurement"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium"> Name </label>
                    <AppInputText
                        v-model="editMeasurementForm.name"
                        class="w-full"
                    />
                    <p
                        v-if="editMeasurementError"
                        class="mt-1 text-sm text-red-500"
                    >
                        {{ editMeasurementError }}
                    </p>
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium"> Unit </label>
                    <AppInputText
                        v-model="editMeasurementForm.unit"
                        class="w-full"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showEditMeasurement = false"
                    />
                    <AppButton label="Save" @click="saveEditMeasurement" />
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
                    <AppInputText
                        v-model="entryForm.date"
                        class="w-full"
                        type="date"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Value
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
                <p
                    v-if="entryFormError"
                    class="text-sm text-red-500"
                >
                    {{ entryFormError }}
                </p>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showEntryDialog = false"
                    />
                    <AppButton label="Save" @click="saveEntry" />
                </div>
            </div>
        </AppDialog>

        <!-- Delete Measurement Confirmation -->
        <AppDialog
            v-model:visible="showDeleteMeasurement"
            header="Delete Measurement"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <p>
                Delete
                <strong>{{ selectedMeasurement?.name }}</strong>
                and all its entries?
            </p>
            <div class="mt-4 flex justify-end gap-2">
                <AppButton
                    label="Cancel"
                    text
                    @click="showDeleteMeasurement = false"
                />
                <AppButton
                    label="Delete"
                    severity="danger"
                    @click="confirmDeleteMeasurement"
                />
            </div>
        </AppDialog>

        <!-- Delete Entry Confirmation -->
        <AppDialog
            v-model:visible="showDeleteEntry"
            header="Delete Entry"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <p>Are you sure you want to delete this entry?</p>
            <div class="mt-4 flex justify-end gap-2">
                <AppButton
                    label="Cancel"
                    text
                    @click="showDeleteEntry = false"
                />
                <AppButton
                    label="Delete"
                    severity="danger"
                    @click="executeDeleteEntry"
                />
            </div>
        </AppDialog>
    </div>
</template>
