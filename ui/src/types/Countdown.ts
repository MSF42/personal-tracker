export interface Countdown {
    id: number;
    title: string;
    date: string;
    created_at: string;
    updated_at: string;
}

export interface CountdownCreate {
    title: string;
    date: string;
}

export interface CountdownUpdate {
    title?: string;
    date?: string;
}
