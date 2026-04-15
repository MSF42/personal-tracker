export type RecurrenceType = 'daily' | 'weekly' | 'monthly';

export interface Note {
    id: number;
    parent_id: number | null;
    content: string;
    sort_order: number;
    collapsed: boolean;
    created_at: string;
    updated_at: string;
    due_date?: string | null;
    recurrence_type?: RecurrenceType | null;
    recurrence_interval?: number | null;
    repeat_days?: number[] | null;
    archived?: boolean;
}

export interface NoteTreeNode extends Note {
    children: NoteTreeNode[];
}

export interface NoteCreate {
    parent_id?: number | null;
    content?: string;
    sort_order?: number;
}

export interface NoteUpdate {
    content?: string;
    collapsed?: boolean;
    due_date?: string | null;
    recurrence_type?: RecurrenceType | null;
    recurrence_interval?: number | null;
    repeat_days?: number[] | null;
    archived?: boolean;
}

export interface NoteMove {
    parent_id: number | null;
    sort_order: number;
}

export interface NoteImageUpload {
    url: string;
    filename: string;
}
