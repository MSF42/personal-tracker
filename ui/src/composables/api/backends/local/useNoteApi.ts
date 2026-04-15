import type { ApiError, ApiResponse } from '@/types/ApiResponse';
import type {
    Note,
    NoteCreate,
    NoteImageUpload,
    NoteMove,
    NoteTreeNode,
    NoteUpdate,
} from '@/types/Note';

import { useDb } from './useDb';
import { boolToInt, intToBool, nowIso } from './utils';

interface NoteRow {
    id: number;
    parent_id: number | null;
    content: string;
    sort_order: number;
    collapsed: number;
    created_at: string;
    updated_at: string;
}

function rowToNote(row: NoteRow): Note {
    return {
        ...row,
        collapsed: intToBool(row.collapsed),
    };
}

export function useNoteApi() {
    const { query, queryOne, run, execute } = useDb();

    const getNotes = async (): Promise<ApiResponse<NoteTreeNode[]>> => {
        const result = await query<NoteRow>(
            'SELECT * FROM notes ORDER BY sort_order ASC, id ASC',
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };

        const nodes = new Map<number, NoteTreeNode>();
        const roots: NoteTreeNode[] = [];

        for (const row of result.data!) {
            const note = rowToNote(row);
            nodes.set(note.id, { ...note, children: [] });
        }

        for (const node of nodes.values()) {
            if (node.parent_id && nodes.has(node.parent_id)) {
                nodes.get(node.parent_id)!.children.push(node);
            } else {
                roots.push(node);
            }
        }

        return { data: roots, error: null, success: true };
    };

    const createNote = async (data: NoteCreate): Promise<ApiResponse<Note>> => {
        const now = nowIso();

        let sortOrder = data.sort_order ?? 0;
        if (sortOrder === 0) {
            const maxResult = await queryOne<{
                next_order: number;
            }>(
                'SELECT COALESCE(MAX(sort_order), -1) + 1 as next_order FROM notes WHERE parent_id IS ?',
                [data.parent_id ?? null],
            );
            if (maxResult.success) {
                sortOrder = maxResult.data!.next_order;
            }
        }

        const result = await run(
            `INSERT INTO notes (parent_id, content, sort_order, collapsed, created_at, updated_at)
             VALUES (?, ?, ?, 0, ?, ?)`,
            [data.parent_id ?? null, data.content ?? '', sortOrder, now, now],
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };

        const noteResult = await queryOne<NoteRow>(
            'SELECT * FROM notes WHERE id = ?',
            [result.data!.id],
        );
        if (!noteResult.success)
            return {
                data: null,
                error: noteResult.error,
                success: false,
            };
        return {
            data: rowToNote(noteResult.data!),
            error: null,
            success: true,
        };
    };

    const updateNote = async (
        id: number,
        data: NoteUpdate,
    ): Promise<ApiResponse<Note>> => {
        const fields: string[] = [];
        const values: unknown[] = [];

        if (data.content !== undefined) {
            fields.push('content = ?');
            values.push(data.content);
        }
        if (data.collapsed !== undefined) {
            fields.push('collapsed = ?');
            values.push(boolToInt(data.collapsed));
        }

        if (fields.length === 0) {
            const existing = await queryOne<NoteRow>(
                'SELECT * FROM notes WHERE id = ?',
                [id],
            );
            if (!existing.success)
                return {
                    data: null,
                    error: existing.error,
                    success: false,
                };
            return {
                data: rowToNote(existing.data!),
                error: null,
                success: true,
            };
        }

        fields.push('updated_at = ?');
        values.push(nowIso());
        values.push(id);

        const result = await execute(
            `UPDATE notes SET ${fields.join(', ')} WHERE id = ?`,
            values,
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };

        const noteResult = await queryOne<NoteRow>(
            'SELECT * FROM notes WHERE id = ?',
            [id],
        );
        if (!noteResult.success)
            return {
                data: null,
                error: noteResult.error,
                success: false,
            };
        return {
            data: rowToNote(noteResult.data!),
            error: null,
            success: true,
        };
    };

    const moveNote = async (
        id: number,
        data: NoteMove,
    ): Promise<ApiResponse<Note>> => {
        const now = nowIso();
        const result = await execute(
            'UPDATE notes SET parent_id = ?, sort_order = ?, updated_at = ? WHERE id = ?',
            [data.parent_id, data.sort_order, now, id],
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };

        const noteResult = await queryOne<NoteRow>(
            'SELECT * FROM notes WHERE id = ?',
            [id],
        );
        if (!noteResult.success)
            return {
                data: null,
                error: noteResult.error,
                success: false,
            };
        return {
            data: rowToNote(noteResult.data!),
            error: null,
            success: true,
        };
    };

    const deleteNote = async (id: number) => {
        // Foreign keys with CASCADE should handle children
        await execute('PRAGMA foreign_keys = ON');
        return execute('DELETE FROM notes WHERE id = ?', [id]);
    };

    const uploadNoteImage = async (
        _file: File,
    ): Promise<ApiResponse<NoteImageUpload>> => {
        throw new Error('Image upload is not supported in the local backend');
    };

    // Stubs so the interface matches the http backend. Features layered on top
    // of these (global search, complete-due, markdown export) are not yet
    // implemented for the in-browser SQLite backend — callers in local mode
    // get an empty / unsupported response and should degrade gracefully.
    const searchNotes = async (_q: string): Promise<ApiResponse<Note[]>> => {
        return { data: [], error: null, success: true };
    };

    const completeDueNote = async (_id: number): Promise<ApiResponse<Note>> => {
        const error: ApiError = {
            message: 'complete-due is not supported in the local backend',
        };
        return { data: null, error, success: false };
    };

    const exportNoteMarkdown = async (_id: number): Promise<string | null> => {
        return null;
    };

    return {
        getNotes,
        createNote,
        updateNote,
        moveNote,
        deleteNote,
        uploadNoteImage,
        searchNotes,
        completeDueNote,
        exportNoteMarkdown,
    };
}
