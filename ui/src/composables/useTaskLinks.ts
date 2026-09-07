import { ref } from 'vue';

import { useTaskApi } from '@/composables/api/useTaskApi';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useWorkoutRoutineApi } from '@/composables/api/useWorkoutRoutineApi';
import { useToast } from '@/composables/useToast';
import type { Task } from '@/types/Task';
import type { WorkoutRoutine } from '@/types/WorkoutRoutine';

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

    // Set only when the currently-open dialog was reached via a linked
    // task's click — null for the plain "Add Run" quick action, which
    // shares the same dialog but shouldn't complete anything on save.
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

        pendingLinkedTaskId.value = task.id;
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

    async function completeLinkedTaskIfAny() {
        if (pendingLinkedTaskId.value == null) return;
        await updateTask(pendingLinkedTaskId.value, { completed: true });
        pendingLinkedTaskId.value = null;
    }

    async function onWorkoutLogged(completed: boolean) {
        if (completed) await completeLinkedTaskIfAny();
        else pendingLinkedTaskId.value = null;
        await refresh();
    }

    async function onRunSaved() {
        await completeLinkedTaskIfAny();
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
