import type { ApiResponse } from '@/types/ApiResponse';
import type {
    ExerciseHistoryEntry,
    RoutineLogSummary,
    SetLog,
    SetLogUpdate,
    WorkoutLog,
    WorkoutLogDetail,
    WorkoutLogUpdate,
} from '@/types/WorkoutLog';

import { useDb } from './useDb';
import { intToBool, nowIso } from './utils';

// sql.js returns `completed` as a raw 0/1 integer (SQLite has no boolean
// type); the response types declare it as `boolean`, so every row carrying
// it needs converting, same as tasks.completed/habits.archived elsewhere in
// this backend.
function withCompletedBool<T extends { completed: unknown }>(row: T): T {
    return { ...row, completed: intToBool(row.completed as number) };
}

export function useWorkoutLogApi() {
    const { query, queryOne, run, execute } = useDb();

    const getWorkoutLogs = async (): Promise<ApiResponse<WorkoutLog[]>> => {
        const result = await query<WorkoutLog>(
            `SELECT wl.*, wr.name as routine_name
             FROM workout_logs wl
             JOIN workout_routines wr ON wl.routine_id = wr.id
             ORDER BY wl.date DESC`,
        );
        if (!result.success || !result.data) return result;
        return {
            ...result,
            data: result.data.map(withCompletedBool),
        };
    };

    const getWorkoutLog = async (
        id: number,
    ): Promise<ApiResponse<WorkoutLogDetail>> => {
        const logResult = await queryOne<WorkoutLogDetail>(
            `SELECT wl.*, wr.name as routine_name
             FROM workout_logs wl
             JOIN workout_routines wr ON wl.routine_id = wr.id
             WHERE wl.id = ?`,
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
                ...withCompletedBool(logResult.data),
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
            'INSERT INTO workout_logs (routine_id, date, notes, created_at, completed) VALUES (?, ?, ?, ?, 0)',
            [routineId, date, notes ?? null, now],
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };

        const created = await queryOne<WorkoutLog>(
            `SELECT wl.*, wr.name as routine_name
             FROM workout_logs wl
             JOIN workout_routines wr ON wl.routine_id = wr.id
             WHERE wl.id = ?`,
            [result.data!.id],
        );
        if (!created.success || !created.data) return created;
        return { ...created, data: withCompletedBool(created.data) };
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

    const updateSet = async (
        workoutLogId: number,
        setId: number,
        data: SetLogUpdate,
    ): Promise<ApiResponse<SetLog>> => {
        const fields: string[] = [];
        const values: unknown[] = [];

        if (data.reps !== undefined && data.reps !== null) {
            fields.push('reps = ?');
            values.push(data.reps);
        }
        if (data.weight !== undefined) {
            fields.push('weight = ?');
            values.push(data.weight);
        }

        if (fields.length > 0) {
            values.push(setId);
            const result = await execute(
                `UPDATE set_logs SET ${fields.join(', ')} WHERE id = ? AND workout_log_id = ${workoutLogId}`,
                values,
            );
            if (!result.success)
                return { data: null, error: result.error, success: false };
        }

        return queryOne<SetLog>(
            `SELECT sl.*, e.name as exercise_name
             FROM set_logs sl
             JOIN exercises e ON sl.exercise_id = e.id
             WHERE sl.id = ?`,
            [setId],
        );
    };

    const updateWorkoutLog = async (
        id: number,
        data: WorkoutLogUpdate,
    ): Promise<ApiResponse<WorkoutLog>> => {
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
        if (data.completed !== undefined && data.completed !== null) {
            fields.push('completed = ?');
            values.push(data.completed ? 1 : 0);
        }

        if (fields.length > 0) {
            values.push(id);
            const result = await execute(
                `UPDATE workout_logs SET ${fields.join(', ')} WHERE id = ?`,
                values,
            );
            if (!result.success) return { ...result, data: null };
        }

        const updated = await queryOne<WorkoutLog>(
            `SELECT wl.*, wr.name as routine_name
             FROM workout_logs wl
             JOIN workout_routines wr ON wl.routine_id = wr.id
             WHERE wl.id = ?`,
            [id],
        );
        if (!updated.success || !updated.data) return updated;
        return { ...updated, data: withCompletedBool(updated.data) };
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

    const getLogsByRoutine = async (
        routineId: number,
    ): Promise<ApiResponse<RoutineLogSummary[]>> => {
        const result = await query<RoutineLogSummary>(
            `SELECT wl.id, wl.date, wl.notes, wl.created_at, wl.completed,
                    COUNT(sl.id) as total_sets,
                    COALESCE(SUM(sl.reps * COALESCE(sl.weight, 0)), 0) as total_volume
             FROM workout_logs wl
             LEFT JOIN set_logs sl ON sl.workout_log_id = wl.id
             WHERE wl.routine_id = ?
             GROUP BY wl.id
             ORDER BY wl.date DESC`,
            [routineId],
        );
        if (!result.success || !result.data) return result;
        return { ...result, data: result.data.map(withCompletedBool) };
    };

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
        getLogsByRoutine,
    };
}
