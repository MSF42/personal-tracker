import type {
    Countdown,
    CountdownCreate,
    CountdownUpdate,
} from '@/types/Countdown';

import { useDb } from './useDb';
import { nowIso } from './utils';

export function useCountdownApi() {
    const { query, queryOne, run, execute } = useDb();

    const getCountdowns = async () =>
        query<Countdown>('SELECT * FROM countdowns ORDER BY date ASC, id ASC');

    const createCountdown = async (data: CountdownCreate) => {
        const now = nowIso();
        const result = await run(
            `INSERT INTO countdowns (title, date, created_at, updated_at)
             VALUES (?, ?, ?, ?)`,
            [data.title, data.date, now, now],
        );
        if (!result.success) return { ...result, data: null };
        return queryOne<Countdown>('SELECT * FROM countdowns WHERE id = ?', [
            result.data!.id,
        ]);
    };

    const updateCountdown = async (id: number, data: CountdownUpdate) => {
        const fields: string[] = [];
        const values: unknown[] = [];
        if (data.title !== undefined) {
            fields.push('title = ?');
            values.push(data.title);
        }
        if (data.date !== undefined) {
            fields.push('date = ?');
            values.push(data.date);
        }
        if (fields.length > 0) {
            fields.push('updated_at = ?');
            values.push(nowIso());
            values.push(id);
            const result = await execute(
                `UPDATE countdowns SET ${fields.join(', ')} WHERE id = ?`,
                values,
            );
            if (!result.success) return { ...result, data: null };
        }
        return queryOne<Countdown>('SELECT * FROM countdowns WHERE id = ?', [
            id,
        ]);
    };

    const deleteCountdown = async (id: number) =>
        execute('DELETE FROM countdowns WHERE id = ?', [id]);

    return { getCountdowns, createCountdown, updateCountdown, deleteCountdown };
}
