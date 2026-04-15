export type SearchKind = 'note' | 'task' | 'habit' | 'exercise' | 'routine';

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
    notes_due: Array<{
        id: number;
        content: string;
        due_date: string | null;
        recurrence_type: string | null;
    }>;
}

export interface TagCount {
    name: string;
    count: number;
}

export interface TagsResponse {
    tags: TagCount[];
    mentions: TagCount[];
}

export interface BacklinkRow {
    id: number;
    parent_id: number | null;
    content: string;
    updated_at: string;
}

export interface BacklinksResponse {
    links: BacklinkRow[];
}
