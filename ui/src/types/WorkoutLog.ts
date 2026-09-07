export interface WorkoutLog {
    id: number;
    routine_id: number;
    routine_name: string;
    date: string;
    notes: string | null;
    created_at: string;
    completed: boolean;
}

export interface SetLog {
    id: number;
    workout_log_id: number;
    exercise_id: number;
    set_number: number;
    reps: number;
    weight: number | null;
    exercise_name: string;
}

export interface ExerciseHistoryEntry {
    workout_log_id: number;
    date: string;
    routine_name: string;
    set_number: number;
    reps: number;
    weight: number | null;
}

export interface SetLogUpdate {
    reps?: number | null;
    weight?: number | null;
}

export interface WorkoutLogUpdate {
    date?: string | null;
    notes?: string | null;
    completed?: boolean | null;
}

export interface WorkoutLogDetail {
    id: number;
    routine_id: number;
    routine_name: string | null;
    date: string;
    notes: string | null;
    created_at: string;
    completed: boolean;
    sets: SetLog[];
}

export interface RoutineLogSummary {
    id: number;
    date: string;
    notes: string | null;
    created_at: string | null;
    completed: boolean;
    total_sets: number;
    total_volume: number;
}
