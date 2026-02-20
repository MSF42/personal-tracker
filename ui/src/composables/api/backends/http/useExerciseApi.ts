import type {
    Exercise,
    ExerciseCreate,
    ExerciseUpdate,
} from '@/types/Exercise';

import { useApi } from './useApi';

export function useExerciseApi() {
    const api = useApi();

    const getExercises = async () => api.getData<Exercise[]>('exercises');

    const getExercise = async (id: number) =>
        api.getData<Exercise>(`exercises/${id}`);

    const createExercise = async (exercise: ExerciseCreate) =>
        api.post<ExerciseCreate, Exercise>('exercises', exercise);

    const updateExercise = async (id: number, exercise: ExerciseUpdate) =>
        api.put<ExerciseUpdate, Exercise>(`exercises/${id}`, exercise);

    const deleteExercise = async (id: number) => api.remove(`exercises/${id}`);

    return {
        getExercises,
        getExercise,
        createExercise,
        updateExercise,
        deleteExercise,
    };
}
