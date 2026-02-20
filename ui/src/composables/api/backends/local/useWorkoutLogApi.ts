import type { ApiResponse } from '@/types/ApiResponse';
import type {
    ExerciseHistoryEntry,
    SetLog,
    WorkoutLog,
    WorkoutLogDetail,
    WorkoutLogUpdate,
} from '@/types/WorkoutLog';

import { useDb } from './useDb';
import { nowIso } from './utils';

export function useWorkoutLogApi() {
    const { query, queryOne, run, execute } = useDb();

    const getWorkoutLogs = async () =>
        query<WorkoutLog>(
            `SELECT wl.*, wr.name as routine_name
             FROM workout_logs wl
             JOIN workout_routines wr ON wl.routine_id = wr.id
             ORDER BY wl.date DESC`,
        );

    const getWorkoutLog = async (
        id: number,
    ): Promise<ApiResponse<WorkoutLogDetail>> => {
        const logResult = await queryOne<WorkoutLogDetail>(
            'SELECT * FROM workout_logs WHERE id = ?',
            [id],
        );
        if (!logResult.success || !logResult.data) return logResult;

        const setsResult = await query<SetLog>(
            `SELECT sl.*, e.name as exercise_name
             FROM set_logs sl
             JOIN exercises e ON sl.exercise_id = e.id
             WHERE sl.workout_log_id = ?
             ORDER BY sl.exercise_id, sl.set_number`,
            [id],
        );

        return {
            data: {
                ...logResult.data,
                sets: setsResult.data ?? [],
            },
            error: null,
            success: true,
        };
    };

    const createWorkoutLog = async (
        routineId: number,
        date: string,
        notes?: string | null,
    ): Promise<ApiResponse<WorkoutLog>> => {
        const now = nowIso();
        const result = await run(
            'INSERT INTO workout_logs (routine_id, date, notes, created_at) VALUES (?, ?, ?, ?)',
            [routineId, date, notes ?? null, now],
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };

        return queryOne<WorkoutLog>(
            `SELECT wl.*, wr.name as routine_name
             FROM workout_logs wl
             JOIN workout_routines wr ON wl.routine_id = wr.id
             WHERE wl.id = ?`,
            [result.data!.id],
        );
    };

    const logSet = async (
        workoutLogId: number,
        exerciseId: number,
        setNumber: number,
        reps: number,
        weight?: number | null,
    ): Promise<ApiResponse<SetLog>> => {
        const result = await run(
            'INSERT INTO set_logs (workout_log_id, exercise_id, set_number, reps, weight) VALUES (?, ?, ?, ?, ?)',
            [workoutLogId, exerciseId, setNumber, reps, weight ?? null],
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };

        return queryOne<SetLog>(
            `SELECT sl.*, e.name as exercise_name
             FROM set_logs sl
             JOIN exercises e ON sl.exercise_id = e.id
             WHERE sl.id = ?`,
            [result.data!.id],
        );
    };

    const getExerciseHistory = async (exerciseId: number) =>
        query<ExerciseHistoryEntry>(
            `SELECT sl.set_number, sl.reps, sl.weight,
                    wl.id as workout_log_id, wl.date,
                    wr.name as routine_name
             FROM set_logs sl
             JOIN workout_logs wl ON sl.workout_log_id = wl.id
             JOIN workout_routines wr ON wl.routine_id = wr.id
             WHERE sl.exercise_id = ?
             ORDER BY wl.date DESC, sl.set_number ASC`,
            [exerciseId],
        );

    const updateWorkoutLog = async (id: number, data: WorkoutLogUpdate) => {
        const fields: string[] = [];
        const values: unknown[] = [];

        if (data.date !== undefined) {
            fields.push('date = ?');
            values.push(data.date);
        }
        if (data.notes !== undefined) {
            fields.push('notes = ?');
            values.push(data.notes);
        }

        if (fields.length > 0) {
            values.push(id);
            const result = await execute(
                `UPDATE workout_logs SET ${fields.join(', ')} WHERE id = ?`,
                values,
            );
            if (!result.success) return { ...result, data: null };
        }

        return queryOne<WorkoutLog>(
            `SELECT wl.*, wr.name as routine_name
             FROM workout_logs wl
             JOIN workout_routines wr ON wl.routine_id = wr.id
             WHERE wl.id = ?`,
            [id],
        );
    };

    const deleteWorkoutLog = async (id: number) =>
        execute('DELETE FROM workout_logs WHERE id = ?', [id]);

    const getExerciseLastPerformed = async (): Promise<
        ApiResponse<Record<number, string>>
    > => {
        const result = await query<{
            exercise_id: number;
            last_date: string;
        }>(
            `SELECT sl.exercise_id, MAX(wl.date) as last_date
             FROM set_logs sl
             JOIN workout_logs wl ON sl.workout_log_id = wl.id
             GROUP BY sl.exercise_id`,
        );
        if (!result.success)
            return {
                data: null,
                error: result.error,
                success: false,
            };

        const record: Record<number, string> = {};
        for (const row of result.data!) {
            record[row.exercise_id] = row.last_date;
        }
        return { data: record, error: null, success: true };
    };

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
