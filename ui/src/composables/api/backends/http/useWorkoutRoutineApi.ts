import type { RoutineExercise } from '@/types/WorkoutRoutine';
import type {
    WorkoutRoutine,
    WorkoutRoutineCreate,
    WorkoutRoutineUpdate,
} from '@/types/WorkoutRoutine';

import { useApi } from './useApi';

export function useWorkoutRoutineApi() {
    const api = useApi();

    const getWorkoutRoutines = async () =>
        api.getData<WorkoutRoutine[]>('workout-routines');

    const createWorkoutRoutine = async (routine: WorkoutRoutineCreate) =>
        api.post<WorkoutRoutineCreate, WorkoutRoutine>(
            'workout-routines',
            routine,
        );

    const updateWorkoutRoutine = async (
        id: number,
        routine: WorkoutRoutineUpdate,
    ) =>
        api.put<WorkoutRoutineUpdate, WorkoutRoutine>(
            `workout-routines/${id}`,
            routine,
        );

    const deleteWorkoutRoutine = async (id: number) =>
        api.remove(`workout-routines/${id}`);

    const getRoutineExercises = async (routineId: number) =>
        api.getData<RoutineExercise[]>(
            `workout-routines/${routineId}/exercises`,
        );

    const addRoutineExercise = async (
        routineId: number,
        exerciseId: number,
        sets: number,
        reps: number,
    ) =>
        api.postWithParams<RoutineExercise>(
            `workout-routines/${routineId}/exercises`,
            { exercise_id: exerciseId, sets, reps },
        );

    const removeRoutineExercise = async (
        routineId: number,
        exerciseId: number,
    ) => api.remove(`workout-routines/${routineId}/exercises/${exerciseId}`);

    return {
        getWorkoutRoutines,
        createWorkoutRoutine,
        updateWorkoutRoutine,
        deleteWorkoutRoutine,
        getRoutineExercises,
        addRoutineExercise,
        removeRoutineExercise,
    };
}
