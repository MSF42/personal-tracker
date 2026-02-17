export interface WorkoutRoutine {
    id: number;
    name: string;
    description: string | null;
    created_at: string;
    updated_at: string;
}

export interface WorkoutRoutineCreate {
    name: string;
    description?: string | null;
}

export interface WorkoutRoutineUpdate {
    name?: string | null;
    description?: string | null;
}

export interface RoutineExercise {
    id: number;
    name: string;
    description: string | null;
    muscle_group: string;
    equipment: string | null;
    instructions: string | null;
    sets: number;
    reps: number;
    order_index: number;
    created_at: string;
    updated_at: string;
}
