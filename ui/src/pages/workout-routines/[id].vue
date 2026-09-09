<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import ExerciseHistoryDialog from '@/components/ExerciseHistoryDialog.vue';
import LoadingState from '@/components/LoadingState.vue';
import LogWorkoutDialog from '@/components/LogWorkoutDialog.vue';
import NotFoundState from '@/components/NotFoundState.vue';
import StatTileGrid from '@/components/StatTileGrid.vue';
import WorkoutLogDetailDialog from '@/components/WorkoutLogDetailDialog.vue';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useWorkoutRoutineApi } from '@/composables/api/useWorkoutRoutineApi';
import { useSmartBack } from '@/composables/useSmartBack';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type {
    ExerciseHistoryEntry,
    RoutineLogSummary,
} from '@/types/WorkoutLog';
import type { RoutineExercise, WorkoutRoutine } from '@/types/WorkoutRoutine';
import { detailTableClass } from '@/utils/detailTable';
import { formatDate } from '@/utils/format';

const route = useRoute<'/workout-routines/[id]'>();
const { back } = useSmartBack('/workout-routines');
const { getWorkoutRoutine, getRoutineExercises } = useWorkoutRoutineApi();
const {
    getLogsByRoutine,
    getExercisePRs,
    getExerciseLastPerformed,
    getExerciseHistory,
} = useWorkoutLogApi();
const { fmtWeight } = useUnits();
const toast = useToast();

const routine = ref<WorkoutRoutine | null>(null);
const exercises = ref<RoutineExercise[]>([]);
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

    const [exercisesRes, logsRes, prsRes, lastPerformedRes] = await Promise.all(
        [
            getRoutineExercises(id),
            getLogsByRoutine(id),
            getExercisePRs(),
            getExerciseLastPerformed(),
        ],
    );
    if (exercisesRes.success && exercisesRes.data)
        exercises.value = exercisesRes.data;
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

// --- View/Edit workout log dialog -----------------------------------------------
const showLogDetail = ref(false);
const viewingLogId = ref<number | null>(null);

function openLogDetail(logId: number) {
    viewingLogId.value = logId;
    showLogDetail.value = true;
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
            back-to="/workout-routines"
            entity="routine"
        />

        <div v-else-if="routine" class="flex flex-col gap-6">
            <div class="flex items-start justify-between gap-4">
                <div>
                    <h1 class="text-2xl font-bold">{{ routine.name }}</h1>
                    <p
                        v-if="routine.description"
                        class="text-surface-500 mt-1 text-sm"
                    >
                        {{ routine.description }}
                    </p>
                </div>
                <AppButton
                    icon="pi pi-play"
                    label="Log Workout"
                    @click="showLogDialog = true"
                />
            </div>

            <StatTileGrid :tiles="heroTiles" />

            <div>
                <h3 class="mb-2 text-sm font-medium">Exercises</h3>
                <div
                    v-if="exercises.length === 0"
                    class="text-surface-500 text-sm"
                >
                    No exercises in this routine yet.
                </div>
                <div v-else class="overflow-x-auto">
                    <table :class="detailTableClass">
                        <thead>
                            <tr>
                                <th>Exercise</th>
                                <th>Muscle Group</th>
                                <th>Prescription</th>
                                <th>PR</th>
                                <th>Last Performed</th>
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
                            </tr>
                        </tbody>
                    </table>
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
        <WorkoutLogDetailDialog
            v-model:visible="showLogDetail"
            :log-id="viewingLogId"
            @updated="refreshHistory"
        />
    </div>
</template>
