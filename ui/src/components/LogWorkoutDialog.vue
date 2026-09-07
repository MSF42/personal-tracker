<script setup lang="ts">
import { reactive, ref, watch } from 'vue';

import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useWorkoutRoutineApi } from '@/composables/api/useWorkoutRoutineApi';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type { RoutineExercise, WorkoutRoutine } from '@/types/WorkoutRoutine';
import { formatDate } from '@/utils/format';

const props = defineProps<{ routine: WorkoutRoutine | null }>();
const emit = defineEmits<{ logged: [] }>();
const visible = defineModel<boolean>('visible', { required: true });
const { getRoutineExercises } = useWorkoutRoutineApi();
const { createWorkoutLog, logSet, getExerciseHistory } = useWorkoutLogApi();
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
    exerciseId: number;
    exerciseName: string;
    setNumber: number;
    reps: number;
    weight: null | number;
    saved: boolean;
}

const setEntries = ref<SetEntry[]>([]);
// exerciseId -> "Last (31 Aug 2026): 30 × 8, 30 × 8 lbs", shown while logging
const lastSets = ref<Record<number, string>>({});

async function loadLastSets(exerciseIds: number[]) {
    lastSets.value = {};
    await Promise.all(
        exerciseIds.map(async (exerciseId) => {
            const res = await getExerciseHistory(exerciseId);
            if (!res.success || !res.data || res.data.length === 0) return;
            // History is ordered by date desc, then set number; take the
            // most recent session only.
            const lastDate = res.data[0]!.date;
            const lastSession = res.data.filter((e) => e.date === lastDate);
            const weighted = lastSession.some(
                (e) => e.weight != null && e.weight > 0,
            );
            const sets = lastSession.map((e) =>
                e.weight != null && e.weight > 0
                    ? `${Math.round(fromKg(e.weight) * 10) / 10} × ${e.reps}`
                    : `BW × ${e.reps}`,
            );
            const unit = weighted ? ` ${weightUnit.value}` : '';
            lastSets.value[exerciseId] =
                `Last (${formatDate(lastDate)}): ${sets.join(', ')}${unit}`;
        }),
    );
}

async function open(routine: WorkoutRoutine) {
    logStep.value = 1;
    workoutLogId.value = null;
    logForm.date = todayStr;
    logForm.notes = '';
    setEntries.value = [];

    const res = await getRoutineExercises(routine.id);
    if (res.success && res.data) {
        logExercises.value = res.data;
    }
}

watch(
    () => [visible.value, props.routine?.id] as const,
    ([open_, id]) => {
        if (open_ && props.routine && id) void open(props.routine);
    },
);

async function createLog() {
    if (!props.routine) return;
    const res = await createWorkoutLog(
        props.routine.id,
        logForm.date,
        logForm.notes || null,
    );
    if (res.success && res.data) {
        workoutLogId.value = res.data.id;
        // Build set entries from routine exercises
        const entries: SetEntry[] = [];
        for (const ex of logExercises.value) {
            for (let s = 1; s <= ex.sets; s++) {
                entries.push({
                    exerciseId: ex.id,
                    exerciseName: ex.name,
                    setNumber: s,
                    reps: ex.reps,
                    weight: null,
                    saved: false,
                });
            }
        }
        setEntries.value = entries;
        logStep.value = 2;
        toast.showSuccess('Workout log created');
        emit('logged');
        await loadLastSets(logExercises.value.map((ex) => ex.id));
    }
}

async function saveSet(entry: SetEntry) {
    if (!workoutLogId.value) return;
    const res = await logSet(
        workoutLogId.value,
        entry.exerciseId,
        entry.setNumber,
        entry.reps,
        entry.weight != null ? toKg(entry.weight) : null,
    );
    if (res.success) {
        entry.saved = true;
    }
}

async function saveAllAndClose() {
    const unsaved = setEntries.value.filter((e) => !e.saved);
    await Promise.all(unsaved.map((e) => saveSet(e)));
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
        :header="`Log Workout: ${routine?.name ?? ''}`"
        modal
        :style="{ width: '40rem', maxWidth: '92vw' }"
    >
        <!-- Step 1: Date + Notes -->
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
                <div class="font-medium">{{ group.name }}</div>
                <div
                    class="text-surface-500 dark:text-surface-400 mb-2 text-xs"
                >
                    {{ lastSets[group.exerciseId] ?? 'No previous sets' }}
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
                        <AppInputNumber
                            v-model="entry.reps"
                            class="w-24"
                            :disabled="entry.saved"
                            :min="0"
                            placeholder="Reps"
                        />
                        <span class="text-surface-500 text-xs">reps</span>
                        <AppInputNumber
                            v-model="entry.weight"
                            class="w-24"
                            :disabled="entry.saved"
                            :max-fraction-digits="1"
                            :min="0"
                            placeholder="Weight"
                        />
                        <span class="text-surface-500 text-xs">{{
                            weightUnit
                        }}</span>
                        <AppButton
                            v-if="!entry.saved"
                            aria-label="Save set"
                            icon="pi pi-check"
                            severity="success"
                            size="small"
                            text
                            @click="saveSet(entry)"
                        />
                        <i v-else class="pi pi-check-circle text-green-500" />
                    </div>
                </div>
            </div>
            <div class="flex justify-end">
                <AppButton label="Done" @click="saveAllAndClose" />
            </div>
        </div>
    </AppDialog>
</template>
