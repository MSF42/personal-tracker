import type { ApiResponse } from '@/types/ApiResponse';
import type {
    Note,
    NoteCreate,
    NoteImageUpload,
    NoteMove,
    NoteTreeNode,
    NoteUpdate,
} from '@/types/Note';

import { useApi } from './useApi';

export function useNoteApi() {
    const api = useApi();

    const getNotes = async () => api.getData<NoteTreeNode[]>('notes');

    const createNote = async (data: NoteCreate) =>
        api.post<NoteCreate, Note>('notes', data);

    const updateNote = async (id: number, data: NoteUpdate) =>
        api.put<NoteUpdate, Note>(`notes/${id}`, data);

    const moveNote = async (id: number, data: NoteMove) =>
        api.put<NoteMove, Note>(`notes/${id}/move`, data);

    const deleteNote = async (id: number) => api.remove(`notes/${id}`);

    const uploadNoteImage = async (
        file: File,
    ): Promise<ApiResponse<NoteImageUpload>> => {
        const formData = new FormData();
        formData.append('file', file);
        return api.postFormData<NoteImageUpload>('notes/images', formData);
    };

    const searchNotes = (q: string) =>
        api.getData<Note[]>('notes/search', { q });

    return {
        getNotes,
        createNote,
        updateNote,
        moveNote,
        deleteNote,
        uploadNoteImage,
        searchNotes,
    };
}
