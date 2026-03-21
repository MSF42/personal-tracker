import type {
    ExerciseHistoryEntry,
    SetLog,
    SetLogUpdate,
    WorkoutLog,
    WorkoutLogDetail,
    WorkoutLogUpdate,
} from '@/types/WorkoutLog';

import { useApi } from './useApi';

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
        api.post<object, WorkoutLog>('workout-logs', {
            routine_id: routineId,
            date,
            notes: notes || null,
        });

    const logSet = async (
        workoutLogId: number,
        exerciseId: number,
        setNumber: number,
        reps: number,
        weight?: number | null,
    ) =>
        api.post<object, SetLog>(`workout-logs/${workoutLogId}/sets`, {
            exercise_id: exerciseId,
            set_number: setNumber,
            reps,
            weight: weight ?? null,
        });

    const getExerciseHistory = async (exerciseId: number) =>
        api.getData<ExerciseHistoryEntry[]>(
            `workout-logs/exercise/${exerciseId}/history`,
        );

    const updateSet = async (
        workoutLogId: number,
        setId: number,
        data: SetLogUpdate,
    ) =>
        api.put<SetLogUpdate, SetLog>(
            `workout-logs/${workoutLogId}/sets/${setId}`,
            data,
        );

    const updateWorkoutLog = async (id: number, data: WorkoutLogUpdate) =>
        api.put<WorkoutLogUpdate, WorkoutLog>(`workout-logs/${id}`, data);

    const deleteWorkoutLog = async (id: number) =>
        api.remove(`workout-logs/${id}`);

    const getExerciseLastPerformed = async () =>
        api.getData<Record<number, string>>(
            'workout-logs/exercise-last-performed',
        );

    const getExercisePRs = async () =>
        api.getData<Record<number, number>>('workout-logs/exercise-prs');

    return {
        getWorkoutLogs,
        getWorkoutLog,
        createWorkoutLog,
        updateWorkoutLog,
        updateSet,
        deleteWorkoutLog,
        logSet,
        getExerciseHistory,
        getExerciseLastPerformed,
        getExercisePRs,
    };
}
