export interface Measurement {
    id: number;
    name: string;
    unit: string;
    sort_order: number;
    created_at: string;
    updated_at: string;
}

export interface MeasurementCreate {
    name: string;
    unit: string;
}

export interface MeasurementUpdate {
    name?: string;
    unit?: string;
}

export interface MeasurementEntry {
    id: number;
    measurement_id: number;
    date: string;
    value: number;
    notes: string | null;
    created_at: string;
    updated_at: string;
}

export interface MeasurementEntryCreate {
    date: string;
    value: number;
    notes?: string | null;
}

export interface MeasurementEntryUpdate {
    date?: string | null;
    value?: number | null;
    notes?: string | null;
}
