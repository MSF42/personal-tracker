import { ref } from 'vue';

import { useTaskApi } from '@/composables/api/useTaskApi';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useWorkoutRoutineApi } from '@/composables/api/useWorkoutRoutineApi';
import { useToast } from '@/composables/useToast';
import type { Task } from '@/types/Task';
import type { WorkoutRoutine } from '@/types/WorkoutRoutine';

/**
 * Marks complete any incomplete task linked to this workout routine whose
 * due date matches the workout log being completed. Called from wherever a
 * workout log can actually be marked completed (LogWorkoutDialog,
 * WorkoutLogDetailDialog) rather than tracked by "which task opened this
 * dialog" — a workout started via a linked task can just as easily be
 * resumed and finished later from the Workout Logs list, a routine's
 * history, or anywhere else, and the task should still complete then too.
 *
 * Takes `getTasks`/`updateTask` as arguments rather than calling
 * `useTaskApi()` itself — this runs after an `await` inside the caller's
 * completion handler, and by then Vue's component-instance context (which
 * `inject()`-based composables like the HTTP backend's toast need) is gone.
 * Callers should resolve `useTaskApi()` synchronously at setup time, same
 * as every other `use*Api()` call in the app, and pass the methods through.
 */
export async function completeTasksLinkedToWorkout(
    getTasks: ReturnType<typeof useTaskApi>['getTasks'],
    updateTask: ReturnType<typeof useTaskApi>['updateTask'],
    routineId: number,
    date: string,
): Promise<void> {
    const res = await getTasks({ completed: false });
    if (!res.success || !res.data) return;
    const matches = res.data.filter(
        (t) =>
            t.link_type === 'workout_routine' &&
            t.link_routine_id === routineId &&
            t.due_date === date,
    );
    await Promise.all(
        matches.map((t) => updateTask(t.id, { completed: true })),
    );
}

/**
 * Shared "enter" behavior for a task linked to a workout routine or a run —
 * used by both the homepage calendar and the Tasks list, so clicking a
 * linked task opens the right modal (resuming an in-progress workout log if
 * one exists) and, on real completion, marks the task done too.
 *
 * `refresh` is called after anything here changes task/workout/run state —
 * callers reload whatever lists they show (tasks, workout logs, runs).
 */
export function useTaskLinks(refresh: () => Promise<void> | void) {
    const { updateTask } = useTaskApi();
    const { getLogsByRoutine } = useWorkoutLogApi();
    const { getWorkoutRoutines } = useWorkoutRoutineApi();
    const toast = useToast();

    const routines = ref<WorkoutRoutine[]>([]);

    async function loadRoutines() {
        const res = await getWorkoutRoutines();
        if (res.success && res.data) routines.value = res.data;
    }

    const showLogWorkoutDialog = ref(false);
    const activeRoutineId = ref<number | null>(null);
    const activeRoutineName = ref('');
    const activeResumeLogId = ref<number | null>(null);

    const showRunDialog = ref(false);
    const runDefaultDate = ref<string | null>(null);

    // Only the Run flow needs this: a run has no stable id to match a task
    // against the way a routine does, so we track which task (if any)
    // opened this dialog and complete it on save. The workout flow doesn't
    // need this — LogWorkoutDialog and WorkoutLogDetailDialog complete any
    // task linked to that routine+date themselves once the workout is
    // actually completed, which also covers resuming/completing it later
    // from anywhere else in the app (not just this dialog instance).
    const pendingLinkedTaskId = ref<number | null>(null);

    async function openLinkedWorkout(task: Task) {
        if (task.link_routine_id == null) return;
        const routine = routines.value.find(
            (r) => r.id === task.link_routine_id,
        );
        if (!routine) {
            toast.showError('Linked routine no longer exists');
            return;
        }

        const logsRes = await getLogsByRoutine(routine.id);
        const inProgress =
            logsRes.success && logsRes.data
                ? logsRes.data.find((l) => !l.completed)
                : undefined;

        activeRoutineId.value = routine.id;
        activeRoutineName.value = routine.name;
        activeResumeLogId.value = inProgress?.id ?? null;
        showLogWorkoutDialog.value = true;
    }

    function openLinkedRun(task: Task) {
        pendingLinkedTaskId.value = task.id;
        runDefaultDate.value = task.due_date;
        showRunDialog.value = true;
    }

    /** The plain "Add Run" entry point shares this same dialog — make sure
     *  a linked task abandoned earlier (dialog closed without saving) can
     *  never get completed by an unrelated save through this path. */
    function openPlainRun(defaultDate: string | null = null) {
        pendingLinkedTaskId.value = null;
        runDefaultDate.value = defaultDate;
        showRunDialog.value = true;
    }

    // Task completion for a completed workout is handled inside
    // LogWorkoutDialog/WorkoutLogDetailDialog themselves (see
    // completeTasksLinkedToWorkout above) — this just refreshes.
    async function onWorkoutLogged() {
        await refresh();
    }

    async function onRunSaved() {
        if (pendingLinkedTaskId.value != null) {
            await updateTask(pendingLinkedTaskId.value, { completed: true });
            pendingLinkedTaskId.value = null;
        }
        await refresh();
    }

    return {
        routines,
        loadRoutines,
        showLogWorkoutDialog,
        activeRoutineId,
        activeRoutineName,
        activeResumeLogId,
        showRunDialog,
        runDefaultDate,
        openLinkedWorkout,
        openLinkedRun,
        openPlainRun,
        onWorkoutLogged,
        onRunSaved,
    };
}
