import type { ApiResponse } from '@/types/ApiResponse';
import type {
    RoutineExercise,
    WorkoutRoutine,
    WorkoutRoutineCreate,
    WorkoutRoutineUpdate,
} from '@/types/WorkoutRoutine';

import { useDb } from './useDb';
import { nowIso } from './utils';

export function useWorkoutRoutineApi() {
    const { query, queryOne, run, execute } = useDb();

    const getWorkoutRoutines = async () =>
        query<WorkoutRoutine>(
            'SELECT * FROM workout_routines ORDER BY name ASC',
        );

    const createWorkoutRoutine = async (routine: WorkoutRoutineCreate) => {
        const now = nowIso();
        const result = await run(
            `INSERT INTO workout_routines (name, description, created_at, updated_at)
             VALUES (?, ?, ?, ?)`,
            [routine.name, routine.description ?? null, now, now],
        );
        if (!result.success) return { ...result, data: null };
        return queryOne<WorkoutRoutine>(
            'SELECT * FROM workout_routines WHERE id = ?',
            [result.data!.id],
        );
    };

    const updateWorkoutRoutine = async (
        id: number,
        routine: WorkoutRoutineUpdate,
    ) => {
        const fields: string[] = [];
        const values: unknown[] = [];

        if (routine.name !== undefined) {
            fields.push('name = ?');
            values.push(routine.name);
        }
        if (routine.description !== undefined) {
            fields.push('description = ?');
            values.push(routine.description);
        }

        if (fields.length === 0) {
            return queryOne<WorkoutRoutine>(
                'SELECT * FROM workout_routines WHERE id = ?',
                [id],
            );
        }

        fields.push('updated_at = ?');
        values.push(nowIso());
        values.push(id);

        const result = await execute(
            `UPDATE workout_routines SET ${fields.join(', ')} WHERE id = ?`,
            values,
        );
        if (!result.success) return { ...result, data: null };
        return queryOne<WorkoutRoutine>(
            'SELECT * FROM workout_routines WHERE id = ?',
            [id],
        );
    };

    const deleteWorkoutRoutine = async (id: number) =>
        execute('DELETE FROM workout_routines WHERE id = ?', [id]);

    const getRoutineExercises = async (
        routineId: number,
    ): Promise<ApiResponse<RoutineExercise[]>> => {
        return query<RoutineExercise>(
            `SELECT e.id, e.name, e.description, e.muscle_group, e.equipment,
                    e.instructions, re.sets, re.reps, re.order_index,
                    e.created_at, e.updated_at
             FROM routine_exercises re
             JOIN exercises e ON re.exercise_id = e.id
             WHERE re.routine_id = ?
             ORDER BY re.order_index ASC`,
            [routineId],
        );
    };

    const addRoutineExercise = async (
        routineId: number,
        exerciseId: number,
        sets: number,
        reps: number,
    ) => {
        // Get next order_index
        const maxResult = await queryOne<{ next_idx: number }>(
            'SELECT COALESCE(MAX(order_index), -1) + 1 as next_idx FROM routine_exercises WHERE routine_id = ?',
            [routineId],
        );
        const orderIndex = maxResult.success ? maxResult.data!.next_idx : 0;

        const result = await run(
            `INSERT INTO routine_exercises (routine_id, exercise_id, sets, reps, order_index)
             VALUES (?, ?, ?, ?, ?)`,
            [routineId, exerciseId, sets, reps, orderIndex],
        );
        if (!result.success) return { ...result, data: null };

        return queryOne<RoutineExercise>(
            `SELECT e.id, e.name, e.description, e.muscle_group, e.equipment,
                    e.instructions, re.sets, re.reps, re.order_index,
                    e.created_at, e.updated_at
             FROM routine_exercises re
             JOIN exercises e ON re.exercise_id = e.id
             WHERE re.routine_id = ? AND re.exercise_id = ?`,
            [routineId, exerciseId],
        );
    };

    const removeRoutineExercise = async (
        routineId: number,
        exerciseId: number,
    ) =>
        execute(
            'DELETE FROM routine_exercises WHERE routine_id = ? AND exercise_id = ?',
            [routineId, exerciseId],
        );

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
