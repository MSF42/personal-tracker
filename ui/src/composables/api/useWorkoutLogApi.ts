import { useApi } from '@/composables/api/useApi';
import type {
    ExerciseHistoryEntry,
    SetLog,
    WorkoutLog,
    WorkoutLogDetail,
    WorkoutLogUpdate,
} from '@/types/WorkoutLog';

export function useWorkoutLogApi() {
    const api = useApi();

    const getWorkoutLogs = async () =>
        api.getData<WorkoutLog[]>('workout-logs');

    const getWorkoutLog = async (id: number) =>
        api.getData<WorkoutLogDetail>(`workout-logs/${id}`);

    const createWorkoutLog = async (
        routineId: number,
        date: string,
        notes?: string | null,
    ) =>
        api.postWithParams<WorkoutLog>('workout-logs', {
            routine_id: routineId,
            date,
            notes: notes || undefined,
        });

    const logSet = async (
        workoutLogId: number,
        exerciseId: number,
        setNumber: number,
        reps: number,
        weight?: number | null,
    ) =>
        api.postWithParams<SetLog>(`workout-logs/${workoutLogId}/sets`, {
            exercise_id: exerciseId,
            set_number: setNumber,
            reps,
            weight: weight || undefined,
        });

    const getExerciseHistory = async (exerciseId: number) =>
        api.getData<ExerciseHistoryEntry[]>(
            `workout-logs/exercise/${exerciseId}/history`,
        );

    const updateWorkoutLog = async (id: number, data: WorkoutLogUpdate) =>
        api.put<WorkoutLogUpdate, WorkoutLog>(`workout-logs/${id}`, data);

    const deleteWorkoutLog = async (id: number) =>
        api.remove(`workout-logs/${id}`);

    const getExerciseLastPerformed = async () =>
        api.getData<Record<number, string>>(
            'workout-logs/exercise-last-performed',
        );

    return {
        getWorkoutLogs,
        getWorkoutLog,
        createWorkoutLog,
        updateWorkoutLog,
        deleteWorkoutLog,
        logSet,
        getExerciseHistory,
        getExerciseLastPerformed,
    };
}
