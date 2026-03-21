export interface Habit {
    id: number;
    name: string;
    description: string | null;
    frequency: 'daily' | 'weekdays' | 'weekly';
    frequency_days: number[] | null;
    color: string;
    archived: boolean;
    current_streak: number;
    longest_streak: number;
    completed_today: boolean;
    created_at: string;
    updated_at: string;
}

export interface HabitCreate {
    name: string;
    description?: string | null;
    frequency?: 'daily' | 'weekdays' | 'weekly';
    frequency_days?: number[] | null;
    color?: string;
}

export interface HabitUpdate {
    name?: string | null;
    description?: string | null;
    frequency?: 'daily' | 'weekdays' | 'weekly' | null;
    frequency_days?: number[] | null;
    color?: string | null;
    archived?: boolean | null;
}
