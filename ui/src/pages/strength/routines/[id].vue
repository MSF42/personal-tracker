<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import ConfirmDeleteDialog from '@/components/ConfirmDeleteDialog.vue';
import ExerciseHistoryDialog from '@/components/ExerciseHistoryDialog.vue';
import LoadingState from '@/components/LoadingState.vue';
import LogWorkoutDialog from '@/components/LogWorkoutDialog.vue';
import NotFoundState from '@/components/NotFoundState.vue';
import StatTileGrid from '@/components/StatTileGrid.vue';
import { useExerciseApi } from '@/composables/api/useExerciseApi';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useWorkoutRoutineApi } from '@/composables/api/useWorkoutRoutineApi';
import { useSmartBack } from '@/composables/useSmartBack';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type { Exercise } from '@/types/Exercise';
import type {
    ExerciseHistoryEntry,
    RoutineLogSummary,
} from '@/types/WorkoutLog';
import type { RoutineExercise, WorkoutRoutine } from '@/types/WorkoutRoutine';
import { detailTableClass } from '@/utils/detailTable';
import { formatDate } from '@/utils/format';

const route = useRoute<'/strength/routines/[id]'>();
const router = useRouter();
const { back } = useSmartBack('/strength/routines');
const {
    getWorkoutRoutine,
    updateWorkoutRoutine,
    getRoutineExercises,
    addRoutineExercise,
    removeRoutineExercise,
} = useWorkoutRoutineApi();
const {
    getLogsByRoutine,
    getExercisePRs,
    getExerciseLastPerformed,
    getExerciseHistory,
} = useWorkoutLogApi();
const { getExercises } = useExerciseApi();
const { fmtWeight } = useUnits();
const toast = useToast();

const routine = ref<WorkoutRoutine | null>(null);
const exercises = ref<RoutineExercise[]>([]);
const allExercises = ref<Exercise[]>([]);
const logs = ref<RoutineLogSummary[]>([]);
const exercisePRs = ref<Record<number, number>>({});
const exerciseLastPerformed = ref<Record<number, string>>({});
const loading = ref(true);
const notFound = ref(false);

const todayStr = new Date().toISOString().split('T')[0] as string;
const currentMonthPrefix = todayStr.slice(0, 7);

async function load(id: number) {
    loading.value = true;
    notFound.value = false;
    routine.value = null;
    exercises.value = [];
    logs.value = [];

    const routineRes = await getWorkoutRoutine(id);
    if (!routineRes.success || !routineRes.data) {
        notFound.value = true;
        loading.value = false;
        return;
    }
    routine.value = routineRes.data;
    editForm.name = routineRes.data.name;
    editForm.description = routineRes.data.description ?? '';

    const [exercisesRes, allExRes, logsRes, prsRes, lastPerformedRes] =
        await Promise.all([
            getRoutineExercises(id),
            getExercises(),
            getLogsByRoutine(id),
            getExercisePRs(),
            getExerciseLastPerformed(),
        ]);
    if (exercisesRes.success && exercisesRes.data)
        exercises.value = exercisesRes.data;
    if (allExRes.success && allExRes.data) allExercises.value = allExRes.data;
    if (logsRes.success && logsRes.data) logs.value = logsRes.data;
    if (prsRes.success && prsRes.data) exercisePRs.value = prsRes.data;
    if (lastPerformedRes.success && lastPerformedRes.data)
        exerciseLastPerformed.value = lastPerformedRes.data;
    loading.value = false;
}

// Vue Router reuses this component instance across param changes, so the
// fetch must react to the param, not only mount.
watch(
    () => route.params.id,
    (value) => {
        const id = Number(value);
        if (Number.isNaN(id)) {
            notFound.value = true;
            loading.value = false;
            return;
        }
        void load(id);
    },
    { immediate: true },
);

const heroTiles = computed(() => {
    const timesPerformed = logs.value.length;
    const lastPerformed = logs.value[0]?.date; // logs are ordered by date desc
    const thisMonth = logs.value.filter((l) =>
        l.date.startsWith(currentMonthPrefix),
    ).length;
    return [
        { label: 'Times Performed', value: String(timesPerformed) },
        {
            label: 'Last Performed',
            value: lastPerformed ? formatDate(lastPerformed) : '—',
        },
        { label: 'This Month', value: String(thisMonth) },
    ];
});

// --- Name / Description editing ------------------------------------------------
const editForm = reactive({ name: '', description: '' });

const isNameValid = computed(() => editForm.name.trim() !== '');
const saveTooltip = computed(() =>
    isNameValid.value ? undefined : 'Name is required',
);

async function saveDetails() {
    if (!routine.value || !isNameValid.value) return;
    const res = await updateWorkoutRoutine(routine.value.id, {
        name: editForm.name,
        description: editForm.description || null,
    });
    if (res.success && res.data) {
        routine.value = res.data;
        toast.showSuccess('Routine updated');
    } else {
        toast.showError(res.error?.message ?? 'Failed to update routine');
    }
}

// --- Add / remove exercises --------------------------------------------------
const addExerciseForm = reactive({
    exerciseId: null as number | null,
    sets: 3,
    reps: 10,
});

const availableExercises = computed(() => {
    const usedIds = new Set(exercises.value.map((re) => re.id));
    return allExercises.value.filter((e) => !usedIds.has(e.id));
});

async function refreshExercises() {
    if (!routine.value) return;
    const res = await getRoutineExercises(routine.value.id);
    if (res.success && res.data) exercises.value = res.data;
}

async function handleAddExercise() {
    if (!routine.value || !addExerciseForm.exerciseId) return;
    const res = await addRoutineExercise(
        routine.value.id,
        addExerciseForm.exerciseId,
        addExerciseForm.sets,
        addExerciseForm.reps,
    );
    if (res.success) {
        toast.showSuccess('Exercise added to routine');
        addExerciseForm.exerciseId = null;
        addExerciseForm.sets = 3;
        addExerciseForm.reps = 10;
        await refreshExercises();
    } else {
        toast.showError(res.error?.message ?? 'Failed to add exercise');
    }
}

const showRemoveExerciseConfirm = ref(false);
const removingExerciseId = ref<number | null>(null);

function confirmRemoveExercise(exerciseId: number) {
    removingExerciseId.value = exerciseId;
    showRemoveExerciseConfirm.value = true;
}

async function handleRemoveExercise() {
    if (!routine.value || removingExerciseId.value === null) return;
    const res = await removeRoutineExercise(
        routine.value.id,
        removingExerciseId.value,
    );
    if (res.success) {
        toast.showSuccess('Exercise removed from routine');
        await refreshExercises();
    } else {
        toast.showError(res.error?.message ?? 'Failed to remove exercise');
    }
    showRemoveExerciseConfirm.value = false;
    removingExerciseId.value = null;
}

// --- Exercise history dialog ---------------------------------------------------
const showHistory = ref(false);
const historyExerciseName = ref('');
const historyEntries = ref<ExerciseHistoryEntry[]>([]);

async function openExerciseHistory(exerciseId: number, exerciseName: string) {
    historyExerciseName.value = exerciseName;
    const res = await getExerciseHistory(exerciseId);
    if (res.success && res.data) {
        historyEntries.value = res.data;
        showHistory.value = true;
    } else {
        toast.showError('Failed to load exercise history');
    }
}

// --- Log Workout ---------------------------------------------------------------
const showLogDialog = ref(false);

async function refreshHistory() {
    if (!routine.value) return;
    const res = await getLogsByRoutine(routine.value.id);
    if (res.success && res.data) logs.value = res.data;
}

function openLogDetail(logId: number) {
    void router.push(`/strength/logs/${logId}`);
}
</script>

<template>
    <div class="mx-auto max-w-4xl p-6">
        <button
            class="text-surface-500 hover:text-surface-900 dark:hover:text-surface-100 mb-4 inline-flex cursor-pointer items-center gap-1.5 text-sm"
            type="button"
            @click="back"
        >
            <i class="pi pi-arrow-left text-xs"></i>
            Back
        </button>

        <LoadingState v-if="loading" />

        <NotFoundState
            v-else-if="notFound"
            back-label="Back to Workout Routines"
            back-to="/strength/routines"
            entity="routine"
        />

        <div v-else-if="routine" class="flex flex-col gap-6">
            <div class="flex flex-wrap items-start justify-between gap-3">
                <h1 class="text-2xl font-bold">
                    {{ editForm.name || 'Routine' }}
                </h1>
                <AppButton
                    icon="pi pi-play"
                    label="Log Workout"
                    @click="showLogDialog = true"
                />
            </div>

            <StatTileGrid :tiles="heroTiles" />

            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Name <span class="text-red-500">*</span>
                    </label>
                    <AppInputText v-model="editForm.name" class="w-full" />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Description
                    </label>
                    <AppTextarea
                        v-model="editForm.description"
                        class="w-full"
                        rows="4"
                    />
                </div>
                <div class="flex justify-end">
                    <span v-tooltip.top="saveTooltip">
                        <AppButton
                            :disabled="!isNameValid"
                            label="Save Changes"
                            size="small"
                            @click="saveDetails"
                        />
                    </span>
                </div>
            </div>

            <div>
                <h3 class="mb-2 text-sm font-medium">Exercises</h3>
                <div
                    v-if="exercises.length === 0"
                    class="text-surface-500 mb-3 text-sm"
                >
                    No exercises in this routine yet.
                </div>
                <div v-else class="mb-3 overflow-x-auto">
                    <table :class="detailTableClass">
                        <thead>
                            <tr>
                                <th>Exercise</th>
                                <th>Muscle Group</th>
                                <th>Prescription</th>
                                <th>PR</th>
                                <th>Last Performed</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="ex in exercises" :key="ex.id">
                                <td>
                                    <button
                                        class="text-primary cursor-pointer hover:underline"
                                        @click="
                                            openExerciseHistory(ex.id, ex.name)
                                        "
                                    >
                                        {{ ex.name }}
                                    </button>
                                </td>
                                <td><AppTag :value="ex.muscle_group" /></td>
                                <td>{{ ex.sets }} × {{ ex.reps }}</td>
                                <td>
                                    {{
                                        exercisePRs[ex.id]
                                            ? fmtWeight(exercisePRs[ex.id])
                                            : '—'
                                    }}
                                </td>
                                <td>
                                    {{
                                        exerciseLastPerformed[ex.id]
                                            ? formatDate(
                                                  exerciseLastPerformed[ex.id]!,
                                              )
                                            : '—'
                                    }}
                                </td>
                                <td>
                                    <AppButton
                                        aria-label="Remove exercise from routine"
                                        icon="pi pi-trash"
                                        rounded
                                        severity="danger"
                                        size="small"
                                        text
                                        @click="confirmRemoveExercise(ex.id)"
                                    />
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- Add exercise -->
                <div
                    class="border-surface-200 dark:border-surface-700 rounded-lg border p-3"
                >
                    <div class="mb-2 text-sm font-medium">Add Exercise</div>
                    <div class="flex flex-wrap items-end gap-2">
                        <div class="min-w-48 flex-1">
                            <AppSelect
                                v-model="addExerciseForm.exerciseId"
                                class="w-full"
                                option-label="name"
                                option-value="id"
                                :options="availableExercises"
                                placeholder="Select exercise..."
                            />
                        </div>
                        <div class="w-20">
                            <label class="mb-1 block text-xs">Sets</label>
                            <AppInputNumber
                                v-model="addExerciseForm.sets"
                                fluid
                                :min="1"
                            />
                        </div>
                        <div class="w-20">
                            <label class="mb-1 block text-xs">Reps</label>
                            <AppInputNumber
                                v-model="addExerciseForm.reps"
                                fluid
                                :min="1"
                            />
                        </div>
                        <AppButton
                            :disabled="!addExerciseForm.exerciseId"
                            icon="pi pi-plus"
                            label="Add"
                            size="small"
                            @click="handleAddExercise"
                        />
                    </div>
                </div>
            </div>

            <div>
                <h3 class="mb-2 text-sm font-medium">Session History</h3>
                <div v-if="logs.length === 0" class="text-surface-500 text-sm">
                    No sessions logged for this routine yet.
                </div>
                <div v-else class="overflow-x-auto">
                    <table :class="detailTableClass">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Notes</th>
                                <th>Sets</th>
                                <th>Volume</th>
                                <th>Status</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="log in logs" :key="log.id">
                                <td>{{ formatDate(log.date) }}</td>
                                <td class="max-w-xs truncate">
                                    {{ log.notes ?? '—' }}
                                </td>
                                <td>{{ log.total_sets }}</td>
                                <td>
                                    {{
                                        log.total_volume > 0
                                            ? fmtWeight(log.total_volume)
                                            : '—'
                                    }}
                                </td>
                                <td>
                                    <AppTag
                                        v-if="!log.completed"
                                        severity="warn"
                                        value="In Progress"
                                    />
                                </td>
                                <td>
                                    <button
                                        class="text-primary cursor-pointer hover:underline"
                                        type="button"
                                        @click="openLogDetail(log.id)"
                                    >
                                        View
                                    </button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <LogWorkoutDialog
            v-model:visible="showLogDialog"
            :routine-id="routine?.id ?? null"
            :routine-name="routine?.name ?? ''"
            @logged="refreshHistory"
        />
        <ExerciseHistoryDialog
            v-model:visible="showHistory"
            :entries="historyEntries"
            :exercise-name="historyExerciseName"
        />
        <ConfirmDeleteDialog
            v-model:visible="showRemoveExerciseConfirm"
            @confirm="handleRemoveExercise"
        >
            Are you sure you want to remove this exercise from the routine?
        </ConfirmDeleteDialog>
    </div>
</template>
