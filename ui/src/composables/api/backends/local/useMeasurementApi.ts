import type {
    Measurement,
    MeasurementCreate,
    MeasurementEntry,
    MeasurementEntryCreate,
    MeasurementEntryUpdate,
    MeasurementUpdate,
} from '@/types/Measurement';

import { useDb } from './useDb';
import { nowIso } from './utils';

export function useMeasurementApi() {
    const { query, queryOne, run, execute } = useDb();

    const getMeasurements = async () =>
        query<Measurement>(
            'SELECT * FROM measurements ORDER BY sort_order ASC, name ASC',
        );

    const createMeasurement = async (data: MeasurementCreate) => {
        const now = nowIso();
        // Auto-increment sort_order
        const maxResult = await queryOne<{ max_order: number }>(
            'SELECT COALESCE(MAX(sort_order), -1) + 1 as max_order FROM measurements',
        );
        const sortOrder = maxResult.success ? maxResult.data!.max_order : 0;

        const result = await run(
            `INSERT INTO measurements (name, unit, sort_order, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?)`,
            [data.name, data.unit, sortOrder, now, now],
        );
        if (!result.success) return { ...result, data: null };
        return queryOne<Measurement>(
            'SELECT * FROM measurements WHERE id = ?',
            [result.data!.id],
        );
    };

    const updateMeasurement = async (id: number, data: MeasurementUpdate) => {
        const fields: string[] = [];
        const values: unknown[] = [];

        if (data.name !== undefined) {
            fields.push('name = ?');
            values.push(data.name);
        }
        if (data.unit !== undefined) {
            fields.push('unit = ?');
            values.push(data.unit);
        }

        if (fields.length === 0) {
            return queryOne<Measurement>(
                'SELECT * FROM measurements WHERE id = ?',
                [id],
            );
        }

        fields.push('updated_at = ?');
        values.push(nowIso());
        values.push(id);

        const result = await execute(
            `UPDATE measurements SET ${fields.join(', ')} WHERE id = ?`,
            values,
        );
        if (!result.success) return { ...result, data: null };
        return queryOne<Measurement>(
            'SELECT * FROM measurements WHERE id = ?',
            [id],
        );
    };

    const deleteMeasurement = async (id: number) =>
        execute('DELETE FROM measurements WHERE id = ?', [id]);

    const getEntries = async (measurementId: number) =>
        query<MeasurementEntry>(
            'SELECT * FROM measurement_entries WHERE measurement_id = ? ORDER BY date DESC',
            [measurementId],
        );

    const createEntry = async (
        measurementId: number,
        data: MeasurementEntryCreate,
    ) => {
        const now = nowIso();
        const result = await run(
            `INSERT INTO measurement_entries (measurement_id, date, value, notes, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?)`,
            [
                measurementId,
                data.date,
                data.value,
                data.notes ?? null,
                now,
                now,
            ],
        );
        if (!result.success) return { ...result, data: null };
        return queryOne<MeasurementEntry>(
            'SELECT * FROM measurement_entries WHERE id = ?',
            [result.data!.id],
        );
    };

    const updateEntry = async (
        entryId: number,
        data: MeasurementEntryUpdate,
    ) => {
        const fields: string[] = [];
        const values: unknown[] = [];

        if (data.date !== undefined) {
            fields.push('date = ?');
            values.push(data.date);
        }
        if (data.value !== undefined) {
            fields.push('value = ?');
            values.push(data.value);
        }
        if (data.notes !== undefined) {
            fields.push('notes = ?');
            values.push(data.notes);
        }

        if (fields.length === 0) {
            return queryOne<MeasurementEntry>(
                'SELECT * FROM measurement_entries WHERE id = ?',
                [entryId],
            );
        }

        fields.push('updated_at = ?');
        values.push(nowIso());
        values.push(entryId);

        const result = await execute(
            `UPDATE measurement_entries SET ${fields.join(', ')} WHERE id = ?`,
            values,
        );
        if (!result.success) return { ...result, data: null };
        return queryOne<MeasurementEntry>(
            'SELECT * FROM measurement_entries WHERE id = ?',
            [entryId],
        );
    };

    const deleteEntry = async (entryId: number) =>
        execute('DELETE FROM measurement_entries WHERE id = ?', [entryId]);

    return {
        getMeasurements,
        createMeasurement,
        updateMeasurement,
        deleteMeasurement,
        getEntries,
        createEntry,
        updateEntry,
        deleteEntry,
    };
}
