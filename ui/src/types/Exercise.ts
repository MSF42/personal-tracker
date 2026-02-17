export interface Exercise {
    id: number;
    name: string;
    description: string | null;
    muscle_group: string;
    equipment: string | null;
    instructions: string | null;
    created_at: string;
    updated_at: string;
}

export interface ExerciseCreate {
    name: string;
    description?: string | null;
    muscle_group: string;
    equipment?: string | null;
    instructions?: string | null;
}

export interface ExerciseUpdate {
    name?: string | null;
    description?: string | null;
    muscle_group?: string | null;
    equipment?: string | null;
    instructions?: string | null;
}
