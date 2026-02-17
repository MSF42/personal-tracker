<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import ExerciseHistoryDialog from '@/components/ExerciseHistoryDialog.vue';
import { useExerciseApi } from '@/composables/api/useExerciseApi';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useToast } from '@/composables/useToast';
import type {
    Exercise,
    ExerciseCreate,
    ExerciseUpdate,
} from '@/types/Exercise';
import type { ExerciseHistoryEntry } from '@/types/WorkoutLog';

const { getExercises, createExercise, updateExercise, deleteExercise } =
    useExerciseApi();
const { getExerciseHistory, getExerciseLastPerformed } = useWorkoutLogApi();
const toast = useToast();

const exercises = ref<Exercise[]>([]);
const exerciseLastPerformed = ref<Record<number, string>>({});

const muscleGroupOptions = [
    { label: 'All', value: '' },
    { label: 'Back', value: 'back' },
    { label: 'Chest', value: 'chest' },
    { label: 'Biceps', value: 'biceps' },
    { label: 'Triceps', value: 'triceps' },
    { label: 'Shoulders', value: 'shoulders' },
    { label: 'Legs', value: 'legs' },
];

const muscleGroupFormOptions = muscleGroupOptions.filter((o) => o.value !== '');

// --- Filters ---
const showFilters = ref(false);
const filters = reactive({
    muscleGroup: '',
    equipment: '',
    search: '',
});

const hasActiveFilters = computed(() =>
    Boolean(filters.muscleGroup || filters.equipment || filters.search),
);

function clearFilters() {
    filters.muscleGroup = '';
    filters.equipment = '';
    filters.search = '';
}

const filteredExercises = computed(() => {
    return exercises.value.filter((e) => {
        if (
            filters.muscleGroup &&
            e.muscle_group.toLowerCase() !== filters.muscleGroup.toLowerCase()
        )
            return false;
        if (
            filters.equipment &&
            (!e.equipment ||
                !e.equipment
                    .toLowerCase()
                    .includes(filters.equipment.toLowerCase()))
        )
            return false;
        if (
            filters.search &&
            !e.name.toLowerCase().includes(filters.search.toLowerCase())
        )
            return false;
        return true;
    });
});

// --- Stats ---
const stats = computed(() => {
    const filtered = filteredExercises.value;
    const muscleGroups = new Set(filtered.map((e) => e.muscle_group));
    const withEquipment = filtered.filter((e) => e.equipment).length;
    return {
        total: filtered.length,
        muscleGroups: muscleGroups.size,
        withEquipment,
    };
});

// --- Dialog state ---
const showDialog = ref(false);
const editingId = ref<number | null>(null);
const showDeleteConfirm = ref(false);
const deletingId = ref<number | null>(null);

const form = reactive({
    name: '',
    muscle_group: '',
    equipment: '',
    description: '',
    instructions: '',
});

function resetForm() {
    form.name = '';
    form.muscle_group = '';
    form.equipment = '';
    form.description = '';
    form.instructions = '';
    editingId.value = null;
}

function openAddDialog() {
    resetForm();
    showDialog.value = true;
}

function openEditDialog(exercise: Exercise) {
    editingId.value = exercise.id;
    form.name = exercise.name;
    form.muscle_group = exercise.muscle_group;
    form.equipment = exercise.equipment ?? '';
    form.description = exercise.description ?? '';
    form.instructions = exercise.instructions ?? '';
    showDialog.value = true;
}

async function saveExercise() {
    if (editingId.value) {
        const payload: ExerciseUpdate = {
            name: form.name,
            muscle_group: form.muscle_group,
            equipment: form.equipment || null,
            description: form.description || null,
            instructions: form.instructions || null,
        };
        const res = await updateExercise(editingId.value, payload);
        if (res.success) {
            toast.showSuccess('Exercise updated');
        }
    } else {
        const payload: ExerciseCreate = {
            name: form.name,
            muscle_group: form.muscle_group,
            equipment: form.equipment || null,
            description: form.description || null,
            instructions: form.instructions || null,
        };
        const res = await createExercise(payload);
        if (res.success) {
            toast.showSuccess('Exercise added');
        }
    }
    showDialog.value = false;
    await loadData();
}

function confirmDelete(id: number) {
    deletingId.value = id;
    showDeleteConfirm.value = true;
}

async function executeDelete() {
    if (deletingId.value) {
        const res = await deleteExercise(deletingId.value);
        if (res.success) {
            toast.showSuccess('Exercise deleted');
        }
    }
    showDeleteConfirm.value = false;
    deletingId.value = null;
    await loadData();
}

// --- Exercise History Dialog ---
const showHistory = ref(false);
const historyExerciseName = ref('');
const historyEntries = ref<ExerciseHistoryEntry[]>([]);

async function openExerciseHistory(exerciseId: number, exerciseName: string) {
    historyExerciseName.value = exerciseName;
    const res = await getExerciseHistory(exerciseId);
    if (res.success && res.data) {
        historyEntries.value = res.data;
        showHistory.value = true;
    }
}

// --- Data loading ---
async function loadData() {
    const [res, lastPerformedRes] = await Promise.all([
        getExercises(),
        getExerciseLastPerformed(),
    ]);
    if (res.success && res.data) exercises.value = res.data;
    if (lastPerformedRes.success && lastPerformedRes.data)
        exerciseLastPerformed.value = lastPerformedRes.data;
}

onMounted(loadData);

const dialogHeader = computed(() =>
    editingId.value ? 'Edit Exercise' : 'Add Exercise',
);
</script>

<template>
    <div class="mx-auto max-w-6xl p-6">
        <h1 class="mb-6 text-2xl font-bold">Exercises</h1>

        <!-- Stats Cards -->
        <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <AppCard>
                <template #title>Total Exercises</template>
                <template #content>
                    <div class="text-2xl font-bold">{{ stats.total }}</div>
                    <div class="text-surface-500 text-sm">
                        {{ stats.total === 1 ? 'exercise' : 'exercises' }}
                    </div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>Muscle Groups</template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{ stats.muscleGroups }}
                    </div>
                    <div class="text-surface-500 text-sm">distinct groups</div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>With Equipment</template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{ stats.withEquipment }}
                    </div>
                    <div class="text-surface-500 text-sm">
                        {{
                            stats.withEquipment === 1 ? 'exercise' : 'exercises'
                        }}
                        with equipment
                    </div>
                </template>
            </AppCard>
        </div>

        <!-- Table Header -->
        <div class="mb-4 flex items-center justify-between">
            <h2 class="text-xl font-semibold">Exercise List</h2>
            <div class="flex gap-2">
                <AppButton
                    :icon="showFilters ? 'pi pi-filter-slash' : 'pi pi-filter'"
                    :label="showFilters ? 'Hide Filters' : 'Filters'"
                    outlined
                    :severity="hasActiveFilters ? 'warn' : 'secondary'"
                    @click="showFilters = !showFilters"
                />
                <AppButton
                    icon="pi pi-plus"
                    label="Add Exercise"
                    @click="openAddDialog"
                />
            </div>
        </div>

        <!-- Filters Panel -->
        <div
            v-if="showFilters"
            class="border-surface-200 dark:border-surface-700 mb-4 rounded-lg border p-4"
        >
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Muscle Group
                    </label>
                    <AppSelect
                        v-model="filters.muscleGroup"
                        class="w-full"
                        option-label="label"
                        option-value="value"
                        :options="muscleGroupOptions"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Equipment
                    </label>
                    <AppInputText
                        v-model="filters.equipment"
                        class="w-full"
                        placeholder="Search equipment..."
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Search
                    </label>
                    <AppInputText
                        v-model="filters.search"
                        class="w-full"
                        placeholder="Search by name..."
                    />
                </div>
            </div>
            <div class="mt-3 flex items-center justify-between">
                <span class="text-surface-500 text-sm">
                    {{ filteredExercises.length }} of
                    {{ exercises.length }} exercises
                </span>
                <AppButton
                    v-if="hasActiveFilters"
                    icon="pi pi-times"
                    label="Clear Filters"
                    severity="secondary"
                    size="small"
                    text
                    @click="clearFilters"
                />
            </div>
        </div>

        <!-- Data Table -->
        <AppDataTable
            sort-field="name"
            :sort-order="1"
            striped-rows
            :value="filteredExercises"
        >
            <AppColumn field="name" header="Name" sortable>
                <template #body="{ data }">
                    <button
                        class="text-primary cursor-pointer font-medium hover:underline"
                        @click="
                            openExerciseHistory(
                                (data as Exercise).id,
                                (data as Exercise).name,
                            )
                        "
                    >
                        {{ (data as Exercise).name }}
                    </button>
                </template>
            </AppColumn>
            <AppColumn field="muscle_group" header="Muscle Group" sortable>
                <template #body="{ data }">
                    <AppTag :value="(data as Exercise).muscle_group" />
                </template>
            </AppColumn>
            <AppColumn field="equipment" header="Equipment" sortable>
                <template #body="{ data }">
                    <span v-if="(data as Exercise).equipment">
                        {{ (data as Exercise).equipment }}
                    </span>
                    <span v-else class="text-surface-400">&mdash;</span>
                </template>
            </AppColumn>
            <AppColumn field="description" header="Description">
                <template #body="{ data }">
                    <span
                        v-if="(data as Exercise).description"
                        class="line-clamp-1"
                    >
                        {{ (data as Exercise).description }}
                    </span>
                    <span v-else class="text-surface-400">&mdash;</span>
                </template>
            </AppColumn>
            <AppColumn header="Last Performed" sort-field="id" sortable>
                <template #body="{ data }">
                    <span v-if="exerciseLastPerformed[(data as Exercise).id]">
                        {{ exerciseLastPerformed[(data as Exercise).id] }}
                    </span>
                    <span v-else class="text-surface-400">&mdash;</span>
                </template>
            </AppColumn>
            <AppColumn header="Actions" style="width: 8rem">
                <template #body="{ data }">
                    <div class="row-actions flex gap-2">
                        <AppButton
                            icon="pi pi-pencil"
                            rounded
                            severity="info"
                            text
                            @click="openEditDialog(data as Exercise)"
                        />
                        <AppButton
                            icon="pi pi-trash"
                            rounded
                            severity="danger"
                            text
                            @click="confirmDelete((data as Exercise).id)"
                        />
                    </div>
                </template>
            </AppColumn>
        </AppDataTable>

        <!-- Add/Edit Dialog -->
        <AppDialog
            v-model:visible="showDialog"
            :header="dialogHeader"
            modal
            :style="{ width: '28rem' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">Name</label>
                    <AppInputText v-model="form.name" class="w-full" />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Muscle Group
                    </label>
                    <AppSelect
                        v-model="form.muscle_group"
                        class="w-full"
                        option-label="label"
                        option-value="value"
                        :options="muscleGroupFormOptions"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Equipment
                    </label>
                    <AppInputText v-model="form.equipment" class="w-full" />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Description
                    </label>
                    <AppTextarea
                        v-model="form.description"
                        class="w-full"
                        rows="2"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Instructions
                    </label>
                    <AppTextarea
                        v-model="form.instructions"
                        class="w-full"
                        rows="3"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showDialog = false"
                    />
                    <AppButton label="Save" @click="saveExercise" />
                </div>
            </div>
        </AppDialog>

        <!-- Exercise History Dialog -->
        <ExerciseHistoryDialog
            v-model:visible="showHistory"
            :entries="historyEntries"
            :exercise-name="historyExerciseName"
        />

        <!-- Delete Confirmation Dialog -->
        <AppDialog
            v-model:visible="showDeleteConfirm"
            header="Confirm Delete"
            modal
            :style="{ width: '24rem' }"
        >
            <p>Are you sure you want to delete this exercise?</p>
            <div class="mt-4 flex justify-end gap-2">
                <AppButton
                    label="Cancel"
                    text
                    @click="showDeleteConfirm = false"
                />
                <AppButton
                    label="Delete"
                    severity="danger"
                    @click="executeDelete"
                />
            </div>
        </AppDialog>
    </div>
</template>
