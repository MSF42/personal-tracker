import type { ApiResponse } from '@/types/ApiResponse';
import type {
    GpxImportResponse,
    GpxSegment,
    MonthlyRunStats,
    PersonalBests,
    RunningActivity,
    RunningActivityCreate,
    RunningActivityUpdate,
} from '@/types/Running';

import { useDb } from './useDb';
import { calculateRunningMetrics, intToBool, nowIso } from './utils';

interface RunningRow {
    id: number;
    date: string;
    duration_seconds: number;
    distance_km: number;
    notes: string | null;
    has_gpx: number;
    title: string | null;
    created_at: string;
    updated_at: string;
}

function rowToActivity(row: RunningRow): RunningActivity {
    const metrics = calculateRunningMetrics(
        row.duration_seconds,
        row.distance_km,
    );
    return {
        ...row,
        has_gpx: intToBool(row.has_gpx),
        ...metrics,
    };
}

export function useRunningApi() {
    const { query, queryOne, execute, run } = useDb();

    const getActivities = async (): Promise<ApiResponse<RunningActivity[]>> => {
        const result = await query<RunningRow>(
            'SELECT * FROM running_activities ORDER BY date DESC',
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };
        return {
            data: result.data!.map(rowToActivity),
            error: null,
            success: true,
        };
    };

    const getActivity = async (
        id: number,
    ): Promise<ApiResponse<RunningActivity>> => {
        const result = await queryOne<RunningRow>(
            'SELECT * FROM running_activities WHERE id = ?',
            [id],
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };
        return {
            data: rowToActivity(result.data!),
            error: null,
            success: true,
        };
    };

    const createActivity = async (
        activity: RunningActivityCreate,
    ): Promise<ApiResponse<RunningActivity>> => {
        const now = nowIso();
        const result = await run(
            `INSERT INTO running_activities (date, duration_seconds, distance_km, notes, title, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?)`,
            [
                activity.date,
                activity.duration_seconds,
                activity.distance_km,
                activity.notes ?? null,
                activity.title ?? null,
                now,
                now,
            ],
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };
        return getActivity(result.data!.id);
    };

    const updateActivity = async (
        id: number,
        activity: RunningActivityUpdate,
    ): Promise<ApiResponse<RunningActivity>> => {
        const fields: string[] = [];
        const values: unknown[] = [];

        if (activity.date !== undefined) {
            fields.push('date = ?');
            values.push(activity.date);
        }
        if (activity.duration_seconds !== undefined) {
            fields.push('duration_seconds = ?');
            values.push(activity.duration_seconds);
        }
        if (activity.distance_km !== undefined) {
            fields.push('distance_km = ?');
            values.push(activity.distance_km);
        }
        if (activity.notes !== undefined) {
            fields.push('notes = ?');
            values.push(activity.notes);
        }
        if (activity.title !== undefined) {
            fields.push('title = ?');
            values.push(activity.title);
        }

        if (fields.length === 0) {
            return getActivity(id);
        }

        fields.push('updated_at = ?');
        values.push(nowIso());
        values.push(id);

        const result = await execute(
            `UPDATE running_activities SET ${fields.join(', ')} WHERE id = ?`,
            values,
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };
        return getActivity(id);
    };

    const deleteActivity = async (id: number) =>
        execute('DELETE FROM running_activities WHERE id = ?', [id]);

    const getYearlyStats = async (
        year: number,
    ): Promise<ApiResponse<MonthlyRunStats[]>> => {
        return query<MonthlyRunStats>(
            `SELECT strftime('%Y-%m', date) as month,
                    COUNT(*) as total_runs,
                    SUM(distance_km) as total_distance,
                    SUM(duration_seconds) as total_duration,
                    AVG(distance_km) as avg_distance,
                    MAX(distance_km) as longest_run
             FROM running_activities
             WHERE strftime('%Y', date) = ?
             GROUP BY month
             ORDER BY month DESC`,
            [String(year)],
        );
    };

    const getPersonalBests = async (): Promise<ApiResponse<PersonalBests>> => {
        const longestResult = await queryOne<RunningRow>(
            'SELECT * FROM running_activities ORDER BY distance_km DESC LIMIT 1',
        );
        const fastestResult = await queryOne<RunningRow>(
            `SELECT * FROM running_activities
             WHERE distance_km > 0
             ORDER BY (CAST(duration_seconds AS REAL) / distance_km) ASC
             LIMIT 1`,
        );

        return {
            data: {
                longest_run:
                    longestResult.success && longestResult.data
                        ? rowToActivity(longestResult.data)
                        : null,
                fastest_pace:
                    fastestResult.success && fastestResult.data
                        ? rowToActivity(fastestResult.data)
                        : null,
            },
            error: null,
            success: true,
        };
    };

    const importGpx = async (
        file: File,
    ): Promise<ApiResponse<GpxImportResponse>> => {
        void file;
        return {
            data: null,
            error: {
                message: 'GPX import is not supported in local mode',
            },
            success: false,
        };
    };

    const getSegments = async (runId: number) =>
        query<GpxSegment>(
            `SELECT id, segment_name, distance_km, duration_seconds, pace, pace_formatted
             FROM gpx_segments
             WHERE running_activity_id = ?
             ORDER BY distance_km ASC`,
            [runId],
        );

    return {
        getActivities,
        getActivity,
        createActivity,
        updateActivity,
        deleteActivity,
        getYearlyStats,
        getPersonalBests,
        importGpx,
        getSegments,
    };
}
