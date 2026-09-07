<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import ExerciseHistoryDialog from '@/components/ExerciseHistoryDialog.vue';
import LoadingState from '@/components/LoadingState.vue';
import NotFoundState from '@/components/NotFoundState.vue';
import StatTileGrid from '@/components/StatTileGrid.vue';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useSmartBack } from '@/composables/useSmartBack';
import { useUnits } from '@/composables/useUnits';
import type {
    ExerciseHistoryEntry,
    SetLog,
    WorkoutLogDetail,
} from '@/types/WorkoutLog';
import { formatDate } from '@/utils/format';

const route = useRoute<'/workout-logs/[id]'>();
const { back } = useSmartBack('/workout-logs');
const { getWorkoutLog, updateSet, getExerciseHistory } = useWorkoutLogApi();
const { fmtWeight, weightUnit, toKg, fromKg } = useUnits();

const detail = ref<WorkoutLogDetail | null>(null);
const loading = ref(true);
const notFound = ref(false);

async function load(id: number) {
    loading.value = true;
    notFound.value = false;
    detail.value = null;

    const res = await getWorkoutLog(id);
    if (!res.success || !res.data) {
        notFound.value = true;
        loading.value = false;
        return;
    }
    detail.value = res.data;
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

const header = computed(() => {
    if (!detail.value) return '';
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

// --- Hero tiles --------------------------------------------------------------
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

// --- Inline set editing --------------------------------------------------------
const editingSetId = ref<number | null>(null);
const editSetReps = ref(0);
const editSetWeight = ref(0);

function startEditSet(set: SetLog) {
    editingSetId.value = set.id;
    editSetReps.value = set.reps;
    // Edit in the user's unit; convert back to kg on save.
    editSetWeight.value =
        set.weight != null ? Math.round(fromKg(set.weight) * 100) / 100 : 0;
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
    }
    editingSetId.value = null;
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
    }
}
</script>

<template>
    <div class="mx-auto max-w-3xl p-6">
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
            back-to="/workout-logs"
            entity="workout log"
        />

        <div v-else-if="detail" class="flex flex-col gap-6">
            <h1 class="text-2xl font-bold">{{ header }}</h1>

            <StatTileGrid :tiles="heroTiles" />

            <p
                v-if="detail.notes"
                class="text-surface-600 dark:text-surface-400 text-sm"
            >
                <span class="font-medium">Notes:</span> {{ detail.notes }}
            </p>

            <div
                v-if="setGroups.length === 0"
                class="text-surface-500 text-center text-sm"
            >
                No sets logged for this workout.
            </div>

            <div
                v-for="group in setGroups"
                :key="group.exerciseName"
                class="border-surface-200 dark:border-surface-700 rounded-lg border p-4"
            >
                <button
                    class="text-primary mb-2 cursor-pointer font-medium hover:underline"
                    @click="
                        openExerciseHistory(
                            group.exerciseId,
                            group.exerciseName,
                        )
                    "
                >
                    {{ group.exerciseName }}
                </button>
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
                            <AppInputNumber
                                v-model="editSetReps"
                                :max="999"
                                :min="1"
                                size="small"
                                style="width: 5rem"
                            />
                            <span class="text-surface-500">reps ×</span>
                            <AppInputNumber
                                v-model="editSetWeight"
                                :max="9999"
                                :max-fraction-digits="2"
                                :min="0"
                                size="small"
                                style="width: 6rem"
                            />
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

        <ExerciseHistoryDialog
            v-model:visible="showHistory"
            :entries="historyEntries"
            :exercise-name="historyExerciseName"
        />
    </div>
</template>
