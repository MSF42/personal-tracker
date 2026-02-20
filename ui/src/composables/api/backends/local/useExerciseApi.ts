import type {
    Exercise,
    ExerciseCreate,
    ExerciseUpdate,
} from '@/types/Exercise';

import { useDb } from './useDb';
import { nowIso } from './utils';

export function useExerciseApi() {
    const { query, queryOne, run, execute } = useDb();

    const getExercises = async () =>
        query<Exercise>('SELECT * FROM exercises ORDER BY name ASC');

    const getExercise = async (id: number) =>
        queryOne<Exercise>('SELECT * FROM exercises WHERE id = ?', [id]);

    const createExercise = async (exercise: ExerciseCreate) => {
        const now = nowIso();
        const result = await run(
            `INSERT INTO exercises (name, description, muscle_group, equipment, instructions, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?)`,
            [
                exercise.name,
                exercise.description ?? null,
                exercise.muscle_group,
                exercise.equipment ?? null,
                exercise.instructions ?? null,
                now,
                now,
            ],
        );
        if (!result.success) return { ...result, data: null };
        return queryOne<Exercise>('SELECT * FROM exercises WHERE id = ?', [
            result.data!.id,
        ]);
    };

    const updateExercise = async (id: number, exercise: ExerciseUpdate) => {
        const fields: string[] = [];
        const values: unknown[] = [];

        if (exercise.name !== undefined) {
            fields.push('name = ?');
            values.push(exercise.name);
        }
        if (exercise.description !== undefined) {
            fields.push('description = ?');
            values.push(exercise.description);
        }
        if (exercise.muscle_group !== undefined) {
            fields.push('muscle_group = ?');
            values.push(exercise.muscle_group);
        }
        if (exercise.equipment !== undefined) {
            fields.push('equipment = ?');
            values.push(exercise.equipment);
        }
        if (exercise.instructions !== undefined) {
            fields.push('instructions = ?');
            values.push(exercise.instructions);
        }

        if (fields.length === 0) {
            return queryOne<Exercise>('SELECT * FROM exercises WHERE id = ?', [
                id,
            ]);
        }

        fields.push('updated_at = ?');
        values.push(nowIso());
        values.push(id);

        const result = await execute(
            `UPDATE exercises SET ${fields.join(', ')} WHERE id = ?`,
            values,
        );
        if (!result.success) return { ...result, data: null };
        return queryOne<Exercise>('SELECT * FROM exercises WHERE id = ?', [id]);
    };

    const deleteExercise = async (id: number) =>
        execute('DELETE FROM exercises WHERE id = ?', [id]);

    return {
        getExercises,
        getExercise,
        createExercise,
        updateExercise,
        deleteExercise,
    };
}
