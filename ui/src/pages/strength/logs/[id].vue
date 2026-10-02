<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import ExerciseHistoryDialog from '@/components/ExerciseHistoryDialog.vue';
import LoadingState from '@/components/LoadingState.vue';
import NotFoundState from '@/components/NotFoundState.vue';
import StatTileGrid from '@/components/StatTileGrid.vue';
import { useTaskApi } from '@/composables/api/useTaskApi';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useWorkoutRoutineApi } from '@/composables/api/useWorkoutRoutineApi';
import { useSmartBack } from '@/composables/useSmartBack';
import { completeTasksLinkedToWorkout } from '@/composables/useTaskLinks';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type {
    ExerciseHistoryEntry,
    SetLog,
    WorkoutLogDetail,
} from '@/types/WorkoutLog';
import { formatDate } from '@/utils/format';
import { fromIsoDate, toIsoDate } from '@/utils/week';

const route = useRoute<'/strength/logs/[id]'>();
const { back } = useSmartBack('/strength/logs');
const { getWorkoutLog, updateSet, updateWorkoutLog, getExerciseHistory } =
    useWorkoutLogApi();
const { getRoutineExercises } = useWorkoutRoutineApi();
const { getTasks, updateTask } = useTaskApi();
const { fmtWeight, weightUnit, toKg, fromKg, roundWeight } = useUnits();
const toast = useToast();

const detail = ref<WorkoutLogDetail | null>(null);
const loading = ref(true);
const notFound = ref(false);
// Exercise ids the routine prescribes; anything else in the log was added for
// that session only. Null until loaded, so nothing is flagged prematurely.
const routineExerciseIds = ref<Set<number> | null>(null);

async function load(id: number) {
    loading.value = true;
    notFound.value = false;
    detail.value = null;
    routineExerciseIds.value = null;
    const res = await getWorkoutLog(id);
    if (res.success && res.data) detail.value = res.data;
    else notFound.value = true;
    loading.value = false;
    if (res.success && res.data) {
        const exRes = await getRoutineExercises(res.data.routine_id);
        if (exRes.success && exRes.data) {
            routineExerciseIds.value = new Set(exRes.data.map((e) => e.id));
        }
    }
}

function isAddedExercise(exerciseId: number): boolean {
    return (
        routineExerciseIds.value !== null &&
        !routineExerciseIds.value.has(exerciseId)
    );
}

// Vue Router reuses this component instance across param changes, so fetch off
// the param, not only on mount.
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

const title = computed(() => {
    if (!detail.value) return 'Workout Log';
    const routine = detail.value.routine_name ?? 'Workout';
    return `${routine} — ${formatDate(detail.value.date)}`;
});

interface SetGroup {
    exerciseId: number;
    exerciseName: string;
    sets: WorkoutLogDetail['sets'];
}

const setGroups = computed<SetGroup[]>(() => {
    if (!detail.value) return [];
    const groups: SetGroup[] = [];
    for (const set of detail.value.sets) {
        let group = groups.find((g) => g.exerciseName === set.exercise_name);
        if (!group) {
            group = {
                exerciseId: set.exercise_id,
                exerciseName: set.exercise_name,
                sets: [],
            };
            groups.push(group);
        }
        group.sets.push(set);
    }
    return groups;
});

const heroTiles = computed(() => {
    if (!detail.value) return [];
    const sets = detail.value.sets;
    const totalVolumeKg = sets.reduce(
        (sum, s) => sum + s.reps * (s.weight ?? 0),
        0,
    );
    return [
        {
            label: 'Total Volume',
            value:
                totalVolumeKg > 0
                    ? `${Math.round(fromKg(totalVolumeKg)).toLocaleString()} ${weightUnit.value}`
                    : '—',
        },
        { label: 'Total Sets', value: String(sets.length) },
        { label: 'Exercises', value: String(setGroups.value.length) },
    ];
});

// --- Date / Notes editing ----------------------------------------------------
const editForm = reactive({ date: '', notes: '' });

watch(detail, (d) => {
    if (d) {
        editForm.date = d.date;
        editForm.notes = d.notes ?? '';
    }
});

// AppDatePicker binds to a Date; editForm.date stays a plain ISO string.
const editDateModel = computed<Date | null>({
    get: () => (editForm.date ? fromIsoDate(editForm.date) : null),
    set: (value) => {
        editForm.date = value ? toIsoDate(value) : '';
    },
});

async function saveDetails() {
    if (!detail.value) return;
    const res = await updateWorkoutLog(detail.value.id, {
        date: editForm.date,
        notes: editForm.notes || null,
    });
    if (res.success && res.data) {
        detail.value.date = res.data.date;
        detail.value.notes = res.data.notes;
        toast.showSuccess('Workout log updated');
    }
}

// --- Inline set editing --------------------------------------------------------
const editingSetId = ref<number | null>(null);
const editSetReps = ref(0);
const editSetWeight = ref(0);

function startEditSet(set: SetLog) {
    editingSetId.value = set.id;
    editSetReps.value = set.reps;
    // Edit in the user's unit; convert back to kg on save.
    editSetWeight.value =
        set.weight != null ? roundWeight(fromKg(set.weight)) : 0;
}

async function saveSet(set: SetLog) {
    if (!detail.value) return;
    const res = await updateSet(detail.value.id, set.id, {
        reps: editSetReps.value,
        weight: toKg(editSetWeight.value),
    });
    if (res.success && res.data) {
        const idx = detail.value.sets.findIndex((s) => s.id === set.id);
        if (idx !== -1) detail.value.sets[idx] = res.data;
        toast.showSuccess('Set updated');
        editingSetId.value = null;
    } else {
        toast.showError(res.error?.message ?? 'Failed to update set');
    }
}

// --- Complete workout ------------------------------------------------------
async function completeWorkout() {
    if (!detail.value) return;
    const res = await updateWorkoutLog(detail.value.id, { completed: true });
    if (res.success && res.data) {
        detail.value.completed = true;
        await completeTasksLinkedToWorkout(
            getTasks,
            updateTask,
            detail.value.routine_id,
            detail.value.date,
        );
        toast.showSuccess('Workout completed');
    }
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
            back-label="Back to Workout Logs"
            back-to="/strength/logs"
            entity="workout log"
        />

        <div v-else-if="detail" class="flex flex-col gap-6">
            <div class="flex flex-wrap items-center justify-between gap-3">
                <h1 class="text-2xl font-bold">{{ title }}</h1>
                <div class="flex items-center gap-3">
                    <AppTag
                        v-if="!detail.completed"
                        severity="warn"
                        value="In Progress"
                    />
                    <AppTag v-else severity="success" value="Complete" />
                    <AppButton
                        v-if="!detail.completed"
                        icon="pi pi-check"
                        label="Complete Workout"
                        size="small"
                        @click="completeWorkout"
                    />
                </div>
            </div>

            <StatTileGrid :tiles="heroTiles" />

            <div class="flex flex-col gap-4">
                <div class="w-48">
                    <label class="mb-1 block text-sm font-medium">Date</label>
                    <AppDatePicker
                        v-model="editDateModel"
                        date-format="yy M dd"
                        icon-display="input"
                        show-icon
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Notes
                    </label>
                    <AppTextarea
                        v-model="editForm.notes"
                        class="w-full"
                        rows="2"
                    />
                </div>
                <div class="flex justify-end">
                    <AppButton
                        label="Save Changes"
                        size="small"
                        @click="saveDetails"
                    />
                </div>
            </div>

            <div
                v-if="setGroups.length === 0"
                class="text-surface-500 text-center text-sm"
            >
                No sets logged for this workout.
            </div>

            <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div
                    v-for="group in setGroups"
                    :key="group.exerciseName"
                    class="border-surface-200 dark:border-surface-700 rounded-lg border p-4"
                >
                    <div class="mb-2 flex items-center gap-2">
                        <button
                            class="text-primary cursor-pointer font-medium hover:underline"
                            @click="
                                openExerciseHistory(
                                    group.exerciseId,
                                    group.exerciseName,
                                )
                            "
                        >
                            {{ group.exerciseName }}
                        </button>
                        <AppTag
                            v-if="isAddedExercise(group.exerciseId)"
                            severity="secondary"
                            title="Added for this session only — not part of the routine"
                            value="Added"
                        />
                    </div>
                    <div class="flex flex-col gap-1">
                        <div
                            v-for="set in group.sets"
                            :key="set.id"
                            class="text-surface-600 dark:text-surface-400 flex items-center gap-2 text-sm"
                        >
                            <span class="text-surface-500 w-12 shrink-0">
                                Set {{ set.set_number }}
                            </span>
                            <template v-if="editingSetId !== set.id">
                                <span>{{ set.reps }} reps</span>
                                <span>
                                    {{
                                        set.weight !== null
                                            ? fmtWeight(set.weight)
                                            : '—'
                                    }}
                                </span>
                                <button
                                    class="text-surface-400 hover:text-primary ml-1"
                                    title="Edit set"
                                    @click="startEditSet(set)"
                                >
                                    <i class="pi pi-pencil text-xs" />
                                </button>
                            </template>
                            <template v-else>
                                <div class="w-16 shrink-0">
                                    <AppInputNumber
                                        v-model="editSetReps"
                                        fluid
                                        :max="999"
                                        :min="1"
                                        size="small"
                                    />
                                </div>
                                <span class="text-surface-500">reps ×</span>
                                <div class="w-20 shrink-0">
                                    <AppInputNumber
                                        v-model="editSetWeight"
                                        fluid
                                        :max="9999"
                                        :max-fraction-digits="2"
                                        :min="0"
                                        size="small"
                                    />
                                </div>
                                <span class="text-surface-500">{{
                                    weightUnit
                                }}</span>
                                <button
                                    class="text-green-500 hover:text-green-600"
                                    title="Save"
                                    @click="saveSet(set)"
                                >
                                    <i class="pi pi-check text-sm" />
                                </button>
                                <button
                                    class="text-red-400 hover:text-red-600"
                                    title="Cancel"
                                    @click="editingSetId = null"
                                >
                                    <i class="pi pi-times text-sm" />
                                </button>
                            </template>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <ExerciseHistoryDialog
            v-model:visible="showHistory"
            :entries="historyEntries"
            :exercise-name="historyExerciseName"
        />
    </div>
</template>
