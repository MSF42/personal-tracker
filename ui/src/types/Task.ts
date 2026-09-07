export type TaskLinkType = 'workout_routine' | 'run';

export interface Task {
    id: number;
    title: string;
    description: string | null;
    category: string | null;
    due_date: string | null;
    completed: boolean;
    repeat_type: string | null;
    repeat_interval: number | null;
    repeat_days: number[] | null;
    priority: 'high' | 'medium' | 'low';
    link_type: TaskLinkType | null;
    link_routine_id: number | null;
    created_at: string;
    updated_at: string;
}

export interface TaskCreate {
    title: string;
    description?: string | null;
    category?: string | null;
    due_date?: string | null;
    completed?: boolean;
    repeat_type?: 'daily' | 'weekly' | 'monthly' | null;
    repeat_interval?: number | null;
    repeat_days?: number[] | null;
    priority?: 'high' | 'medium' | 'low';
    link_type?: TaskLinkType | null;
    link_routine_id?: number | null;
}

export interface TaskUpdate {
    title?: string | null;
    description?: string | null;
    category?: string | null;
    due_date?: string | null;
    completed?: boolean | null;
    repeat_type?: 'daily' | 'weekly' | 'monthly' | null;
    repeat_interval?: number | null;
    repeat_days?: number[] | null;
    priority?: 'high' | 'medium' | 'low' | null;
    link_type?: TaskLinkType | null;
    link_routine_id?: number | null;
}
