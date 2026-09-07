export interface RunningActivity {
    id: number;
    date: string;
    duration_seconds: number;
    distance_km: number;
    notes: string | null;
    has_gpx: boolean;
    title: string | null;
    source?: 'manual' | 'gpx' | 'fit';
    start_time?: string | null;
    elapsed_seconds?: number | null;
    is_indoor?: boolean;
    avg_hr?: number | null;
    max_hr?: number | null;
    avg_cadence?: number | null;
    max_cadence?: number | null;
    calories?: number | null;
    total_ascent_m?: number | null;
    total_descent_m?: number | null;
    avg_power?: number | null;
    max_power?: number | null;
    avg_temperature_c?: number | null;
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
    start_seconds?: number | null;
    end_seconds?: number | null;
}

export interface RunLap {
    id: number;
    lap_index: number;
    start_time: string | null;
    timer_seconds: number;
    elapsed_seconds: number | null;
    distance_km: number;
    pace: number | null;
    avg_hr: number | null;
    max_hr: number | null;
    avg_cadence: number | null;
    avg_power: number | null;
    total_ascent_m: number | null;
    trigger: string | null;
}

export interface RunSample {
    t_seconds: number;
    distance_km: number | null;
    heart_rate: number | null;
    cadence: number | null;
    speed_mps: number | null;
    altitude_m: number | null;
    power: number | null;
    lat: number | null;
    lon: number | null;
}

export interface RunImportResponse {
    activity: RunningActivity;
    segments: GpxSegment[];
    laps: RunLap[];
}

export interface RunningActivityCreate {
    date: string;
    duration_seconds: number;
    distance_km: number;
    notes?: string | null;
    title?: string | null;
}

export interface RunningActivityUpdate {
    date?: string | null;
    duration_seconds?: number | null;
    distance_km?: number | null;
    notes?: string | null;
    title?: string | null;
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
