import type {
    Measurement,
    MeasurementCreate,
    MeasurementEntry,
    MeasurementEntryCreate,
    MeasurementEntryUpdate,
    MeasurementUpdate,
} from '@/types/Measurement';

import { useApi } from './useApi';

export function useMeasurementApi() {
    const api = useApi();

    const getMeasurements = async () =>
        api.getData<Measurement[]>('measurements');

    const createMeasurement = async (data: MeasurementCreate) =>
        api.post<MeasurementCreate, Measurement>('measurements', data);

    const updateMeasurement = async (id: number, data: MeasurementUpdate) =>
        api.put<MeasurementUpdate, Measurement>(`measurements/${id}`, data);

    const deleteMeasurement = async (id: number) =>
        api.remove(`measurements/${id}`);

    const getEntries = async (measurementId: number) =>
        api.getData<MeasurementEntry[]>(
            `measurements/${measurementId}/entries`,
        );

    const createEntry = async (
        measurementId: number,
        data: MeasurementEntryCreate,
    ) =>
        api.post<MeasurementEntryCreate, MeasurementEntry>(
            `measurements/${measurementId}/entries`,
            data,
        );

    const updateEntry = async (entryId: number, data: MeasurementEntryUpdate) =>
        api.put<MeasurementEntryUpdate, MeasurementEntry>(
            `measurements/entries/${entryId}`,
            data,
        );

    const deleteEntry = async (entryId: number) =>
        api.remove(`measurements/entries/${entryId}`);

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
