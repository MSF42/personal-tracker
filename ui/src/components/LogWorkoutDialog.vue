<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';

import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useWorkoutRoutineApi } from '@/composables/api/useWorkoutRoutineApi';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type { RoutineExercise } from '@/types/WorkoutRoutine';
import { formatDate } from '@/utils/format';

const props = withDefaults(
    defineProps<{
        routineId: number | null;
        routineName: string;
        /** Set to reopen this dialog against an existing in-progress log
         *  instead of starting a new one. */
        resumeLogId?: number | null;
    }>(),
    { resumeLogId: null },
);
// `completed` distinguishes a real "Complete Workout" from a plain "Save"
// (progress kept, still in-progress) — callers that only care about
// refreshing a list can ignore the argument entirely.
const emit = defineEmits<{ logged: [completed: boolean] }>();
const visible = defineModel<boolean>('visible', { required: true });
const { getRoutineExercises } = useWorkoutRoutineApi();
const {
    createWorkoutLog,
    logSet,
    updateSet,
    getExerciseHistory,
    getWorkoutLog,
    updateWorkoutLog,
} = useWorkoutLogApi();
const toast = useToast();
const { weightUnit, toKg, fromKg } = useUnits();

const todayStr = new Date().toISOString().split('T')[0] as string;

const logExercises = ref<RoutineExercise[]>([]);
const logStep = ref<1 | 2>(1);
const workoutLogId = ref<number | null>(null);
const logForm = reactive({
    date: todayStr,
    notes: '',
});

interface SetEntry {
    /** The set_logs row id, once this entry has been persisted at least
     *  once — null for a set that's never been saved. Determines whether
     *  persisting it again is an update or a first-time create. */
    setId: number | null;
    exerciseId: number;
    exerciseName: string;
    setNumber: number;
    reps: number;
    weight: null | number;
}

const setEntries = ref<SetEntry[]>([]);
// exerciseId -> setNumber -> "135 × 8" / "BW × 8", the value logged for that
// set the last time this exercise was performed — shown next to each row.
const lastSets = ref<Record<number, Record<number, string>>>({});
// exerciseId -> the date those values came from, shown once per exercise.
const lastSetsDate = ref<Record<number, string>>({});

const dialogHeader = computed(() =>
    props.resumeLogId
        ? `Resume Workout: ${props.routineName}`
        : `Log Workout: ${props.routineName}`,
);

async function loadLastSets(exerciseIds: number[]) {
    lastSets.value = {};
    lastSetsDate.value = {};
    await Promise.all(
        exerciseIds.map(async (exerciseId) => {
            const res = await getExerciseHistory(exerciseId);
            if (!res.success || !res.data) return;
            // Exclude this session's own sets — when resuming, a set saved
            // earlier this same visit would otherwise show up as "last
            // time," which is both circular (it's already visible in the
            // row itself) and hides the actually-prior session.
            const priorHistory = res.data.filter(
                (e) => e.workout_log_id !== workoutLogId.value,
            );
            if (priorHistory.length === 0) return;
            // History is ordered by date desc, then set number; take the
            // most recent prior session only.
            const lastDate = priorHistory[0]!.date;
            const lastSession = priorHistory.filter((e) => e.date === lastDate);
            lastSetsDate.value[exerciseId] = lastDate;
            const bySetNumber: Record<number, string> = {};
            for (const e of lastSession) {
                bySetNumber[e.set_number] =
                    e.weight != null && e.weight > 0
                        ? `${Math.round(fromKg(e.weight) * 10) / 10} × ${e.reps}`
                        : `BW × ${e.reps}`;
            }
            lastSets.value[exerciseId] = bySetNumber;
        }),
    );
}

/** One entry per set the routine prescribes, defaulted from the prescription
 *  and unsaved — the starting point for both a fresh log and a resumed one. */
function buildEntriesFromPrescription(): SetEntry[] {
    const entries: SetEntry[] = [];
    for (const ex of logExercises.value) {
        for (let s = 1; s <= ex.sets; s++) {
            entries.push({
                setId: null,
                exerciseId: ex.id,
                exerciseName: ex.name,
                setNumber: s,
                reps: ex.reps,
                weight: null,
            });
        }
    }
    return entries;
}

async function openFresh(routineId: number) {
    logStep.value = 1;
    workoutLogId.value = null;
    logForm.date = todayStr;
    logForm.notes = '';
    setEntries.value = [];

    const res = await getRoutineExercises(routineId);
    if (res.success && res.data) {
        logExercises.value = res.data;
    }
}

async function openResume(routineId: number, logId: number) {
    workoutLogId.value = logId;
    setEntries.value = [];

    const [exercisesRes, logRes] = await Promise.all([
        getRoutineExercises(routineId),
        getWorkoutLog(logId),
    ]);
    if (exercisesRes.success && exercisesRes.data) {
        logExercises.value = exercisesRes.data;
    }

    // Reconcile the prescription against what's already been logged: a slot
    // with a matching saved set shows its real value and remembers its row
    // id (so persisting again updates it instead of creating a duplicate);
    // everything else starts blank exactly like a fresh log.
    const entries = buildEntriesFromPrescription();
    if (logRes.success && logRes.data) {
        for (const entry of entries) {
            const saved = logRes.data.sets.find(
                (s) =>
                    s.exercise_id === entry.exerciseId &&
                    s.set_number === entry.setNumber,
            );
            if (saved) {
                entry.setId = saved.id;
                entry.reps = saved.reps;
                entry.weight =
                    saved.weight != null ? fromKg(saved.weight) : null;
            }
        }
    }
    setEntries.value = entries;
    await loadLastSets(logExercises.value.map((ex) => ex.id));
    logStep.value = 2;
}

watch(
    () => [visible.value, props.routineId, props.resumeLogId] as const,
    ([isVisible, routineId, resumeLogId]) => {
        if (!isVisible || !routineId) return;
        if (resumeLogId) {
            void openResume(routineId, resumeLogId);
        } else {
            void openFresh(routineId);
        }
    },
);

async function createLog() {
    if (!props.routineId) return;
    const res = await createWorkoutLog(
        props.routineId,
        logForm.date,
        logForm.notes || null,
    );
    if (res.success && res.data) {
        workoutLogId.value = res.data.id;
        setEntries.value = buildEntriesFromPrescription();
        logStep.value = 2;
        toast.showSuccess('Workout log created');
        emit('logged', false);
        await loadLastSets(logExercises.value.map((ex) => ex.id));
    }
}

/** Create or update this entry's row, whichever it needs — there's no
 *  per-set "save" step anymore, so every entry gets persisted (or
 *  re-persisted, if it was already saved and edited since) when the
 *  workout is saved or completed. */
async function persistEntry(entry: SetEntry) {
    if (!workoutLogId.value) return;
    const weightKg = entry.weight != null ? toKg(entry.weight) : null;
    if (entry.setId != null) {
        await updateSet(workoutLogId.value, entry.setId, {
            reps: entry.reps,
            weight: weightKg,
        });
        return;
    }
    const res = await logSet(
        workoutLogId.value,
        entry.exerciseId,
        entry.setNumber,
        entry.reps,
        weightKg,
    );
    if (res.success && res.data) {
        entry.setId = res.data.id;
    }
}

async function persistAllSets() {
    await Promise.all(setEntries.value.map((e) => persistEntry(e)));
}

async function saveAndClose() {
    await persistAllSets();
    emit('logged', false);
    visible.value = false;
}

async function completeAndClose() {
    await persistAllSets();
    if (workoutLogId.value) {
        await updateWorkoutLog(workoutLogId.value, { completed: true });
    }
    toast.showSuccess('Workout completed');
    emit('logged', true);
    visible.value = false;
}

function getExerciseGroups() {
    const groups: { exerciseId: number; name: string; sets: SetEntry[] }[] = [];
    for (const entry of setEntries.value) {
        let group = groups.find((g) => g.exerciseId === entry.exerciseId);
        if (!group) {
            group = {
                exerciseId: entry.exerciseId,
                name: entry.exerciseName,
                sets: [],
            };
            groups.push(group);
        }
        group.sets.push(entry);
    }
    return groups;
}
</script>

<template>
    <AppDialog
        v-model:visible="visible"
        :header="dialogHeader"
        modal
        :style="{ width: '40rem', maxWidth: '92vw' }"
    >
        <!-- Step 1: Date + Notes (fresh logs only — resuming skips straight
             to step 2, since the date/notes were already set at creation) -->
        <div v-if="logStep === 1" class="flex flex-col gap-4">
            <div>
                <label class="mb-1 block text-sm font-medium">Date</label>
                <AppInputText
                    v-model="logForm.date"
                    class="w-full"
                    type="date"
                />
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium">Notes</label>
                <AppTextarea
                    v-model="logForm.notes"
                    class="w-full"
                    placeholder="Optional notes..."
                    rows="2"
                />
            </div>
            <div
                v-if="logExercises.length === 0"
                class="text-surface-500 text-sm"
            >
                This routine has no exercises. Add exercises first.
            </div>
            <div class="flex justify-end gap-2">
                <AppButton label="Cancel" text @click="visible = false" />
                <AppButton
                    :disabled="logExercises.length === 0"
                    label="Start Workout"
                    @click="createLog"
                />
            </div>
        </div>

        <!-- Step 2: Log Sets -->
        <div v-if="logStep === 2" class="flex flex-col gap-4">
            <div
                v-for="group in getExerciseGroups()"
                :key="group.exerciseId"
                class="border-surface-200 dark:border-surface-700 rounded-lg border p-3"
            >
                <div class="mb-2 flex items-baseline justify-between">
                    <div class="font-medium">{{ group.name }}</div>
                    <div
                        v-if="lastSetsDate[group.exerciseId]"
                        class="text-surface-400 text-xs"
                    >
                        Last: {{ formatDate(lastSetsDate[group.exerciseId]!) }}
                    </div>
                    <div v-else class="text-surface-400 text-xs">
                        No previous sets
                    </div>
                </div>
                <div class="flex flex-col gap-2">
                    <div
                        v-for="entry in group.sets"
                        :key="entry.setNumber"
                        class="flex items-center gap-2"
                    >
                        <span class="text-surface-500 w-16 text-sm">
                            Set {{ entry.setNumber }}
                        </span>
                        <div class="w-14 shrink-0">
                            <AppInputNumber
                                v-model="entry.reps"
                                fluid
                                :min="0"
                                placeholder="Reps"
                            />
                        </div>
                        <span class="text-surface-500 text-xs">reps</span>
                        <div class="w-16 shrink-0">
                            <AppInputNumber
                                v-model="entry.weight"
                                fluid
                                :max-fraction-digits="1"
                                :min="0"
                                placeholder="Wt"
                            />
                        </div>
                        <span class="text-surface-500 w-8 text-xs">{{
                            weightUnit
                        }}</span>
                        <span class="text-surface-400 flex-1 text-xs">
                            {{
                                lastSets[group.exerciseId]?.[entry.setNumber] ??
                                '—'
                            }}
                        </span>
                    </div>
                </div>
            </div>
            <div class="flex justify-end gap-2">
                <AppButton
                    label="Save"
                    outlined
                    title="Save your progress — you can resume this workout later from the Logs tab"
                    @click="saveAndClose"
                />
                <AppButton
                    icon="pi pi-check"
                    label="Complete Workout"
                    @click="completeAndClose"
                />
            </div>
        </div>
    </AppDialog>
</template>
