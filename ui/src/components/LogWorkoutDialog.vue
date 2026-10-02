<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';

import { useExerciseApi } from '@/composables/api/useExerciseApi';
import { useTaskApi } from '@/composables/api/useTaskApi';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useWorkoutRoutineApi } from '@/composables/api/useWorkoutRoutineApi';
import { completeTasksLinkedToWorkout } from '@/composables/useTaskLinks';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type { Exercise } from '@/types/Exercise';
import type { ExerciseHistoryEntry } from '@/types/WorkoutLog';
import type { RoutineExercise } from '@/types/WorkoutRoutine';
import { formatDate } from '@/utils/format';
import { fromIsoDate, toIsoDate } from '@/utils/week';

const props = withDefaults(
    defineProps<{
        routineId: number | null;
        routineName: string;
        /** Set to reopen this dialog against an existing in-progress log
         *  instead of starting a new one. */
        resumeLogId?: number | null;
        /** Pre-fill the new log's date (e.g. a linked task's due date) so
         *  completing it matches that task. Defaults to today. */
        defaultDate?: string | null;
    }>(),
    { resumeLogId: null, defaultDate: null },
);
// `completed` distinguishes a real "Complete Workout" from a plain "Save"
// (progress kept, still in-progress); `logId` lets a caller jump to the log's
// detail page. Callers that only refresh a list can ignore both args.
const emit = defineEmits<{ logged: [completed: boolean, logId: number] }>();
const visible = defineModel<boolean>('visible', { required: true });
const { getRoutineExercises } = useWorkoutRoutineApi();
const {
    createWorkoutLog,
    logSet,
    updateSet,
    deleteSet,
    getExerciseHistory,
    getWorkoutLog,
    updateWorkoutLog,
} = useWorkoutLogApi();
const { getExercises } = useExerciseApi();
const { getTasks, updateTask } = useTaskApi();
const toast = useToast();
const { weightUnit, toKg, fromKg, roundWeight } = useUnits();

const todayStr = new Date().toISOString().split('T')[0] as string;

const logExercises = ref<RoutineExercise[]>([]);
const logStep = ref<1 | 2>(1);
const workoutLogId = ref<number | null>(null);
const logForm = reactive({
    date: todayStr,
    notes: '',
});
// AppDatePicker binds to a Date; logForm.date stays a plain ISO string (sent
// to the API as-is).
const logDateModel = computed<Date | null>({
    get: () => (logForm.date ? fromIsoDate(logForm.date) : null),
    set: (value) => {
        logForm.date = value ? toIsoDate(value) : '';
    },
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
// exerciseId -> setNumber -> "8 × 135" / "8 × BW", the value logged for that
// set the last time this exercise was performed — shown next to each row.
// Reps-then-weight to match the order of the Reps/Wt input columns.
const lastSets = ref<Record<number, Record<number, string>>>({});
// exerciseId -> the date those values came from, shown once per exercise.
const lastSetsDate = ref<Record<number, string>>({});
// Exercises toggled off for this session (e.g. sitting out an injured lift) —
// their entries are disabled and excluded from persistAllSets entirely, so no
// set row gets created and the "last time" hint keeps pointing at the last
// session where the exercise was actually performed.
const skippedExercises = reactive(new Set<number>());

function toggleSkip(exerciseId: number, skipped: boolean) {
    if (skipped) {
        skippedExercises.add(exerciseId);
    } else {
        skippedExercises.delete(exerciseId);
    }
}

// --- Session-only exercises and sets -----------------------------------------
// Exercises added here (and extra sets on any exercise) are logged against
// this workout only — the routine's own exercise list is never touched.
const allExercises = ref<Exercise[]>([]);
const addExerciseId = ref<number | null>(null);
// Saved set rows removed in the dialog; deleted on the next Save/Complete so
// closing without saving leaves the log as it was, like any other edit here.
const pendingSetDeletes = ref<number[]>([]);

const availableExercises = computed(() => {
    const inSession = new Set(setEntries.value.map((e) => e.exerciseId));
    return allExercises.value.filter((ex) => !inSession.has(ex.id));
});

async function loadAllExercises() {
    const res = await getExercises();
    if (res.success && res.data) {
        allExercises.value = [...res.data].sort((a, b) =>
            a.name.localeCompare(b.name),
        );
    }
}

function prescribedSets(exerciseId: number): number {
    return logExercises.value.find((ex) => ex.id === exerciseId)?.sets ?? 0;
}

function isAddedExercise(exerciseId: number): boolean {
    return !logExercises.value.some((ex) => ex.id === exerciseId);
}

/** Only the last set in a group can be removed (keeps set numbers
 *  contiguous), and never one the routine prescribes — skip the exercise
 *  instead. An added exercise always keeps at least one set; use Remove to
 *  drop it entirely. */
function canRemoveSet(group: ExerciseGroup, entry: SetEntry): boolean {
    if (group.sets[group.sets.length - 1] !== entry) return false;
    const floor = isAddedExercise(group.exerciseId)
        ? 1
        : prescribedSets(group.exerciseId);
    return entry.setNumber > floor;
}

function dropEntries(predicate: (e: SetEntry) => boolean) {
    for (const entry of setEntries.value) {
        if (predicate(entry) && entry.setId != null) {
            pendingSetDeletes.value.push(entry.setId);
        }
    }
    setEntries.value = setEntries.value.filter((e) => !predicate(e));
}

function addSet(group: ExerciseGroup) {
    const last = group.sets[group.sets.length - 1]!;
    const entry: SetEntry = {
        setId: null,
        exerciseId: group.exerciseId,
        exerciseName: group.name,
        setNumber: last.setNumber + 1,
        reps: last.reps,
        weight: last.weight,
    };
    // Insert right after the group's last set so the group stays contiguous.
    const idx = setEntries.value.indexOf(last);
    setEntries.value.splice(idx + 1, 0, entry);
}

function removeSet(entry: SetEntry) {
    dropEntries((e) => e === entry);
}

function removeExercise(exerciseId: number) {
    dropEntries((e) => e.exerciseId === exerciseId);
    delete lastSets.value[exerciseId];
    delete lastSetsDate.value[exerciseId];
}

async function addExercise(exerciseId: number | null) {
    addExerciseId.value = null;
    const exercise = allExercises.value.find((ex) => ex.id === exerciseId);
    if (!exercise) return;
    const prior = await loadLastSetsFor(exercise.id);
    // Start from last session's shape (set count + reps) when there is one;
    // otherwise a single blank set to fill in and grow with "Add set".
    const setCount = prior.length > 0 ? prior.length : 1;
    for (let s = 1; s <= setCount; s++) {
        setEntries.value.push({
            setId: null,
            exerciseId: exercise.id,
            exerciseName: exercise.name,
            setNumber: s,
            reps: prior.find((p) => p.set_number === s)?.reps ?? 0,
            weight: null,
        });
    }
}

const dialogHeader = computed(() =>
    props.resumeLogId
        ? `Resume Workout: ${props.routineName}`
        : `Log Workout: ${props.routineName}`,
);

/** Fill the "last time" hints for one exercise; returns that prior session's
 *  sets (empty if it's never been performed). */
async function loadLastSetsFor(
    exerciseId: number,
): Promise<ExerciseHistoryEntry[]> {
    const res = await getExerciseHistory(exerciseId);
    if (!res.success || !res.data) return [];
    // Exclude this session's own sets — when resuming, a set saved earlier
    // this same visit would otherwise show up as "last time," which is both
    // circular (it's already visible in the row itself) and hides the
    // actually-prior session.
    const priorHistory = res.data.filter(
        (e) => e.workout_log_id !== workoutLogId.value,
    );
    if (priorHistory.length === 0) return [];
    // History is ordered by date desc, then set number; take the most recent
    // prior session only.
    const lastDate = priorHistory[0]!.date;
    const lastSession = priorHistory.filter((e) => e.date === lastDate);
    lastSetsDate.value[exerciseId] = lastDate;
    const bySetNumber: Record<number, string> = {};
    for (const e of lastSession) {
        bySetNumber[e.set_number] =
            e.weight != null && e.weight > 0
                ? `${e.reps} × ${roundWeight(fromKg(e.weight))}`
                : `${e.reps} × BW`;
    }
    lastSets.value[exerciseId] = bySetNumber;
    return lastSession;
}

async function loadLastSets(exerciseIds: number[]) {
    lastSets.value = {};
    lastSetsDate.value = {};
    await Promise.all(exerciseIds.map((id) => loadLastSetsFor(id)));
}

function sessionExerciseIds(): number[] {
    return [...new Set(setEntries.value.map((e) => e.exerciseId))];
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
    logForm.date = props.defaultDate ?? todayStr;
    logForm.notes = '';
    setEntries.value = [];
    pendingSetDeletes.value = [];
    skippedExercises.clear();
    void loadAllExercises();

    const res = await getRoutineExercises(routineId);
    if (res.success && res.data) {
        logExercises.value = res.data;
    }
}

async function openResume(routineId: number, logId: number) {
    workoutLogId.value = logId;
    setEntries.value = [];
    pendingSetDeletes.value = [];
    skippedExercises.clear();
    void loadAllExercises();

    const [exercisesRes, logRes] = await Promise.all([
        getRoutineExercises(routineId),
        getWorkoutLog(logId),
    ]);
    if (exercisesRes.success && exercisesRes.data) {
        logExercises.value = exercisesRes.data;
    }
    // Step 2 (resumed logs skip step 1) never shows the date field, but we
    // still need the log's real date — not whatever was left over from a
    // previous dialog session — to match it against a linked task on
    // completion.
    if (logRes.success && logRes.data) {
        logForm.date = logRes.data.date;
    }

    // Reconcile the prescription against what's already been logged: a slot
    // with a matching saved set shows its real value and remembers its row
    // id (so persisting again updates it instead of creating a duplicate);
    // everything else starts blank exactly like a fresh log. Saved sets with
    // no matching slot — exercises added just for this session, or extra
    // sets — are appended as-is.
    const entries = buildEntriesFromPrescription();
    if (logRes.success && logRes.data) {
        for (const saved of logRes.data.sets) {
            const weight = saved.weight != null ? fromKg(saved.weight) : null;
            const slot = entries.find(
                (e) =>
                    e.exerciseId === saved.exercise_id &&
                    e.setNumber === saved.set_number,
            );
            if (slot) {
                slot.setId = saved.id;
                slot.reps = saved.reps;
                slot.weight = weight;
                continue;
            }
            const entry: SetEntry = {
                setId: saved.id,
                exerciseId: saved.exercise_id,
                exerciseName: saved.exercise_name,
                setNumber: saved.set_number,
                reps: saved.reps,
                weight,
            };
            // Keep each exercise's sets contiguous and in set order.
            let insertAt = entries.length;
            for (let i = entries.length - 1; i >= 0; i--) {
                if (entries[i]!.exerciseId === saved.exercise_id) {
                    insertAt = i + 1;
                    break;
                }
            }
            entries.splice(insertAt, 0, entry);
        }
    }
    setEntries.value = entries;
    await loadLastSets(sessionExerciseIds());
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
        emit('logged', false, res.data.id);
        await loadLastSets(logExercises.value.map((ex) => ex.id));
    }
}

/** Create or update this entry's row, whichever it needs — there's no
 *  per-set "save" step anymore, so every entry gets persisted (or
 *  re-persisted, if it was already saved and edited since) when the
 *  workout is saved or completed. */
async function persistEntry(entry: SetEntry): Promise<boolean> {
    if (!workoutLogId.value) return false;
    const weightKg = entry.weight != null ? toKg(entry.weight) : null;
    if (entry.setId != null) {
        const res = await updateSet(workoutLogId.value, entry.setId, {
            reps: entry.reps,
            weight: weightKg,
        });
        return res.success;
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
    return res.success;
}

async function applyPendingDeletes(): Promise<boolean> {
    const logId = workoutLogId.value;
    if (!logId) return false;
    const ids = pendingSetDeletes.value;
    const results = await Promise.all(ids.map((id) => deleteSet(logId, id)));
    // Keep only the ones that failed, so a retry picks them up.
    pendingSetDeletes.value = ids.filter((_, i) => !results[i]!.success);
    return pendingSetDeletes.value.length === 0;
}

async function persistAllSets(): Promise<boolean> {
    // Deletes first, so a removed-then-re-added set number never briefly
    // exists twice.
    const deletesOk = await applyPendingDeletes();
    const results = await Promise.all(
        setEntries.value
            .filter((e) => !skippedExercises.has(e.exerciseId))
            .map((e) => persistEntry(e)),
    );
    return deletesOk && results.every(Boolean);
}

async function saveAndClose() {
    const ok = await persistAllSets();
    if (!ok) {
        toast.showError('Some sets failed to save — try again');
        return;
    }
    toast.showSuccess('Progress saved');
    emit('logged', false, workoutLogId.value ?? 0);
    visible.value = false;
}

/** Names of exercises (not skipped) that still have a set missing reps or
 *  weight — completing with one of these blank would otherwise poison that
 *  exercise's "last time" hint the same way a skipped-but-unmarked exercise
 *  would. Save has no such gate; this only guards Complete. */
function incompleteExerciseNames(): string[] {
    const names = new Set<string>();
    for (const entry of setEntries.value) {
        if (skippedExercises.has(entry.exerciseId)) continue;
        if (!entry.reps || entry.weight == null) {
            names.add(entry.exerciseName);
        }
    }
    return [...names];
}

async function completeAndClose() {
    const missing = incompleteExerciseNames();
    if (missing.length > 0) {
        toast.showError(
            `Missing reps or weight: ${missing.join(', ')}`,
            'Fill them in, or mark the exercise as skipped.',
        );
        return;
    }
    const ok = await persistAllSets();
    if (!ok) {
        toast.showError('Some sets failed to save — try again');
        return;
    }
    if (workoutLogId.value) {
        const res = await updateWorkoutLog(workoutLogId.value, {
            completed: true,
        });
        if (!res.success) {
            toast.showError(res.error?.message ?? 'Failed to complete workout');
            return;
        }
    }
    if (props.routineId) {
        await completeTasksLinkedToWorkout(
            getTasks,
            updateTask,
            props.routineId,
            logForm.date,
        );
    }
    toast.showSuccess('Workout completed');
    emit('logged', true, workoutLogId.value ?? 0);
    visible.value = false;
}

interface ExerciseGroup {
    exerciseId: number;
    name: string;
    sets: SetEntry[];
}

function getExerciseGroups() {
    const groups: ExerciseGroup[] = [];
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
                <AppDatePicker
                    v-model="logDateModel"
                    date-format="yy M dd"
                    fluid
                    icon-display="input"
                    show-icon
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
                :class="{
                    'opacity-50': skippedExercises.has(group.exerciseId),
                }"
            >
                <div class="mb-1 flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="font-medium">{{ group.name }}</span>
                        <AppTag
                            v-if="isAddedExercise(group.exerciseId)"
                            severity="secondary"
                            title="Logged for this session only — the routine is unchanged"
                            value="This session only"
                        />
                    </div>
                    <AppButton
                        v-if="isAddedExercise(group.exerciseId)"
                        icon="pi pi-trash"
                        label="Remove"
                        severity="danger"
                        size="small"
                        text
                        @click="removeExercise(group.exerciseId)"
                    />
                    <label
                        v-else
                        class="text-surface-500 dark:text-surface-400 flex cursor-pointer items-center gap-1.5 text-xs"
                    >
                        <AppToggleSwitch
                            :model-value="
                                skippedExercises.has(group.exerciseId)
                            "
                            @update:model-value="
                                (v: boolean) => toggleSkip(group.exerciseId, v)
                            "
                        />
                        Skip this time
                    </label>
                </div>
                <!-- Empty placeholders matching the set rows' Set/reps/Wt/unit
                     columns below, so "Last: …" lines up directly above the
                     per-set last-values column instead of floating at the
                     far right. -->
                <div
                    class="text-surface-400 mb-1 flex items-center gap-2 text-xs"
                >
                    <span class="w-16"></span>
                    <div class="w-14 shrink-0"></div>
                    <span class="invisible">reps</span>
                    <div class="w-16 shrink-0"></div>
                    <span class="w-8"></span>
                    <span class="flex-1">
                        {{
                            lastSetsDate[group.exerciseId]
                                ? `Last: ${formatDate(lastSetsDate[group.exerciseId]!)}`
                                : 'No previous sets'
                        }}
                    </span>
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
                                :disabled="
                                    skippedExercises.has(group.exerciseId)
                                "
                                fluid
                                :min="0"
                                placeholder="Reps"
                            />
                        </div>
                        <span class="text-surface-500 text-xs">reps</span>
                        <div class="w-16 shrink-0">
                            <AppInputNumber
                                v-model="entry.weight"
                                :disabled="
                                    skippedExercises.has(group.exerciseId)
                                "
                                fluid
                                :max-fraction-digits="2"
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
                        <button
                            v-if="canRemoveSet(group, entry)"
                            class="text-surface-400 cursor-pointer hover:text-red-500"
                            title="Remove set"
                            type="button"
                            @click="removeSet(entry)"
                        >
                            <i class="pi pi-times text-xs" />
                        </button>
                    </div>
                </div>
                <AppButton
                    v-if="!skippedExercises.has(group.exerciseId)"
                    class="mt-1"
                    icon="pi pi-plus"
                    label="Add set"
                    size="small"
                    text
                    @click="addSet(group)"
                />
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium">
                    Add exercise
                    <span class="text-surface-500 font-normal">
                        (this session only)
                    </span>
                </label>
                <AppSelect
                    v-model="addExerciseId"
                    auto-filter-focus
                    class="w-full"
                    filter
                    filter-placeholder="Search exercises..."
                    option-label="name"
                    option-value="id"
                    :options="availableExercises"
                    placeholder="Select an exercise to add..."
                    reset-filter-on-hide
                    @change="addExercise($event.value)"
                >
                    <template #option="{ option }">
                        <div class="flex w-full items-center justify-between">
                            <span>{{ option.name }}</span>
                            <span class="text-surface-500 text-xs capitalize">
                                {{ option.muscle_group }}
                            </span>
                        </div>
                    </template>
                </AppSelect>
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
