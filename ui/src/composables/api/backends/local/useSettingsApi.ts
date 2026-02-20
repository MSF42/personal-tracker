import type { ApiResponse } from '@/types/ApiResponse';

import { useDb } from './useDb';

interface SettingResponse {
    key: string;
    value: string | null;
}

export function useSettingsApi() {
    const { queryOne, execute } = useDb();

    const getSetting = async (key: string) => {
        const result = await queryOne<SettingResponse>(
            'SELECT key, value FROM user_settings WHERE key = ?',
            [key],
        );
        // If not found, return a response with null value instead of error
        if (!result.success) {
            return {
                data: { key, value: null } as SettingResponse,
                error: null,
                success: true as const,
            };
        }
        return result;
    };

    const setSetting = async (key: string, value: string) => {
        const result = await execute(
            `INSERT INTO user_settings (key, value) VALUES (?, ?)
             ON CONFLICT(key) DO UPDATE SET value = excluded.value`,
            [key, value],
        );
        if (!result.success)
            return {
                data: null,
                error: result.error,
                success: false as const,
            };
        return {
            data: { key, value } as SettingResponse,
            error: null,
            success: true as const,
        };
    };

    const deleteSetting = async (key: string) =>
        execute('DELETE FROM user_settings WHERE key = ?', [key]);

    const resetAllData = async () => {
        // Delete from all tables in dependency order
        const tables = [
            'set_logs',
            'workout_logs',
            'routine_exercises',
            'workout_routines',
            'gpx_segments',
            'running_activities',
            'exercises',
            'tasks',
            'measurement_entries',
            'measurements',
            'notes',
            'user_settings',
        ];

        for (const table of tables) {
            const result = await execute(`DELETE FROM ${table}`);
            if (!result.success) return result;
        }

        // Re-seed default measurement
        await execute(
            `INSERT INTO measurements (name, unit, sort_order, created_at, updated_at)
             VALUES ('Weight', 'lbs', 0, datetime('now'), datetime('now'))`,
        );

        return {
            data: { message: 'All data has been reset' },
            error: null,
            success: true as const,
        };
    };

    const backup = async (): Promise<void> => {
        // Local backup: export all data as JSON and trigger download
        const db = useDb();
        const tables = [
            'tasks',
            'running_activities',
            'gpx_segments',
            'exercises',
            'workout_routines',
            'routine_exercises',
            'workout_logs',
            'set_logs',
            'user_settings',
            'notes',
            'measurements',
            'measurement_entries',
        ];

        const backup: Record<string, unknown[]> = {};
        for (const table of tables) {
            const result = await db.query<Record<string, unknown>>(
                `SELECT * FROM ${table}`,
            );
            backup[table] = result.data ?? [];
        }

        const blob = new Blob([JSON.stringify(backup, null, 2)], {
            type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `personal-tracker-backup-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const restore = async (
        file: File,
    ): Promise<ApiResponse<{ message: string }>> => {
        try {
            const text = await file.text();
            const data = JSON.parse(text) as Record<
                string,
                Record<string, unknown>[]
            >;

            // Clear all tables first
            await resetAllData();

            const db = useDb();

            for (const [table, rows] of Object.entries(data)) {
                if (table === 'measurements' || !rows || rows.length === 0)
                    continue;
                for (const row of rows) {
                    const columns = Object.keys(row);
                    const placeholders = columns.map(() => '?').join(', ');
                    const values = columns.map((col) => row[col] as unknown);
                    await db.execute(
                        `INSERT OR REPLACE INTO ${table} (${columns.join(', ')}) VALUES (${placeholders})`,
                        values,
                    );
                }
            }

            // Restore measurements separately (after the reset inserted defaults)
            if (data['measurements']?.length) {
                await db.execute('DELETE FROM measurements');
                for (const row of data['measurements']) {
                    const columns = Object.keys(row);
                    const placeholders = columns.map(() => '?').join(', ');
                    const values = columns.map((col) => row[col] as unknown);
                    await db.execute(
                        `INSERT INTO measurements (${columns.join(', ')}) VALUES (${placeholders})`,
                        values,
                    );
                }
            }

            return {
                data: { message: 'Data restored successfully' },
                error: null,
                success: true,
            };
        } catch (err) {
            return {
                data: null,
                error: {
                    message:
                        err instanceof Error ? err.message : 'Restore failed',
                },
                success: false,
            };
        }
    };

    return {
        getSetting,
        setSetting,
        deleteSetting,
        resetAllData,
        backup,
        restore,
    };
}
