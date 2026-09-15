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
 * workout log can actually be marked completed (the Log Workout dialog, the
 * workout log detail page) rather than tracked by "which task opened this
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
 * The run equivalent of {@link completeTasksLinkedToWorkout}: marks complete any
 * incomplete task linked to "a run" whose due date matches a run just logged.
 * A run task carries no target (there's no run-template entity), so the match is
 * date-only — any run on that day satisfies "go for a run today". Called from
 * wherever a run gets created (the Add Run dialog's manual save and single-file
 * import, plus the Running page's bulk import) so the task completes regardless
 * of how the run was entered — not only when the run dialog was opened by
 * clicking the task on the calendar.
 *
 * Same argument-passing rationale as the workout version: it runs after an
 * `await` in the caller, past the point where `inject()`-based composables work,
 * so the caller resolves `useTaskApi()` at setup and passes the methods through.
 */
export async function completeTasksLinkedToRun(
    getTasks: ReturnType<typeof useTaskApi>['getTasks'],
    updateTask: ReturnType<typeof useTaskApi>['updateTask'],
    date: string,
): Promise<void> {
    const res = await getTasks({ completed: false });
    if (!res.success || !res.data) return;
    const matches = res.data.filter(
        (t) => t.link_type === 'run' && t.due_date === date,
    );
    await Promise.all(
        matches.map((t) => updateTask(t.id, { completed: true })),
    );
}

/**
 * Shared "enter" behavior for a task linked to a workout routine or a run —
 * used by both the homepage calendar and the Tasks list, so clicking a
 * linked task opens the right modal (resuming an in-progress workout log if
 * one exists). Completing the linked activity marks the task done, but that
 * now lives in the dialogs themselves (see `completeTasksLinkedToWorkout` /
 * `completeTasksLinkedToRun`) so it fires no matter how the activity was
 * reached — this composable only opens the right modal and refreshes.
 *
 * `refresh` is called after anything here changes task/workout/run state —
 * callers reload whatever lists they show (tasks, workout logs, runs).
 */
export function useTaskLinks(refresh: () => Promise<void> | void) {
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
    // The linked task's due date — used as the new log's default date so
    // completing a workout planned for a future/past day still checks off
    // that day's task (matched by routine + date).
    const activeWorkoutDate = ref<string | null>(null);

    const showRunDialog = ref(false);
    const runDefaultDate = ref<string | null>(null);

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
        activeWorkoutDate.value = task.due_date;
        showLogWorkoutDialog.value = true;
    }

    /** Opening the Add Run dialog — from a linked task's `due_date`, or with
     *  no date for the plain "Add Run" action. A matching run task completes
     *  itself when the run is saved (see `completeTasksLinkedToRun`), so both
     *  entry points behave the same here. */
    function openRunDialog(defaultDate: string | null = null) {
        runDefaultDate.value = defaultDate;
        showRunDialog.value = true;
    }

    const openLinkedRun = (task: Task) => openRunDialog(task.due_date);
    const openPlainRun = (defaultDate: string | null = null) =>
        openRunDialog(defaultDate);

    // Task completion for a completed workout / saved run is handled inside
    // the dialogs themselves (completeTasksLinkedToWorkout /
    // completeTasksLinkedToRun) — these just refresh whatever list the caller
    // shows.
    async function onWorkoutLogged() {
        await refresh();
    }

    async function onRunSaved() {
        await refresh();
    }

    return {
        routines,
        loadRoutines,
        showLogWorkoutDialog,
        activeRoutineId,
        activeRoutineName,
        activeResumeLogId,
        activeWorkoutDate,
        showRunDialog,
        runDefaultDate,
        openLinkedWorkout,
        openLinkedRun,
        openPlainRun,
        onWorkoutLogged,
        onRunSaved,
    };
}
