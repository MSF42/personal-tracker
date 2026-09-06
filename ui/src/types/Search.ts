export type SearchKind = 'task' | 'habit' | 'exercise' | 'routine';

export interface SearchHit {
    kind: SearchKind;
    entity_id: number;
    title: string;
    snippet: string;
}

export interface SearchResponse {
    hits: SearchHit[];
}

export interface TodayResponse {
    date: string;
    tasks_due: Array<{
        id: number;
        title: string;
        due_date: string | null;
        priority: string;
        repeat_type: string | null;
    }>;
    tasks_overdue: Array<{
        id: number;
        title: string;
        due_date: string | null;
        priority: string;
        repeat_type: string | null;
    }>;
}
