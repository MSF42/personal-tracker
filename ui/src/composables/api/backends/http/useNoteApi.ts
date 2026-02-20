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
        try {
            const response = await fetch(
                `${window.location.origin}/api/v1/notes/images`,
                { method: 'POST', body: formData },
            );
            if (!response.ok) {
                let errorMsg = 'Upload failed';
                try {
                    const err = await response.json();
                    if (err.error) errorMsg = err.error;
                } catch {
                    /* ignore parse error */
                }
                return {
                    data: null,
                    error: { message: errorMsg },
                    success: false,
                };
            }
            const data = (await response.json()) as NoteImageUpload;
            return { data, error: null, success: true };
        } catch (err) {
            return {
                data: null,
                error: {
                    message:
                        err instanceof Error ? err.message : 'Upload failed',
                },
                success: false,
            };
        }
    };

    return {
        getNotes,
        createNote,
        updateNote,
        moveNote,
        deleteNote,
        uploadNoteImage,
    };
}
