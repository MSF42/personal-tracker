export interface RunningActivity {
    id: number;
    date: string;
    duration_seconds: number;
    distance_km: number;
    notes: string | null;
    has_gpx: boolean;
    created_at: string;
    updated_at: string;
    pace: number;
    speed: number;
    pace_formatted: string;
}

export interface GpxSegment {
    id: number;
    segment_name: string;
    distance_km: number;
    duration_seconds: number;
    pace: number;
    pace_formatted: string;
}

export interface GpxImportResponse {
    activity: RunningActivity;
    segments: GpxSegment[];
}

export interface RunningActivityCreate {
    date: string;
    duration_seconds: number;
    distance_km: number;
    notes?: string | null;
}

export interface RunningActivityUpdate {
    date?: string | null;
    duration_seconds?: number | null;
    distance_km?: number | null;
    notes?: string | null;
}

export interface MonthlyRunStats {
    month: string;
    total_runs: number;
    total_distance: number;
    total_duration: number;
    avg_distance: number;
    longest_run: number;
}

export interface PersonalBests {
    longest_run: RunningActivity | null;
    fastest_pace: RunningActivity | null;
}
