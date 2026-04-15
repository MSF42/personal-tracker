import type {
    BacklinksResponse,
    SearchResponse,
    TagsResponse,
    TodayResponse,
} from '@/types/Search';

import { useApi } from './backends/http/useApi';

// Bespoke http-backend API client for the unified search / today / tags /
// backlinks endpoints. These features don't (yet) have a local-backend
// implementation — local-mode users will see empty results until the in-browser
// SQLite backend catches up.
export function useSearchApi() {
    const api = useApi();

    const search = (q: string) => api.getData<SearchResponse>('search', { q });

    const getToday = () => api.getData<TodayResponse>('today');

    const getTags = () => api.getData<TagsResponse>('tags');

    const getBacklinks = (target: string, excludeNoteId?: number) =>
        api.getData<BacklinksResponse>('backlinks', {
            target,
            exclude_note_id: excludeNoteId,
        });

    return { search, getToday, getTags, getBacklinks };
}
