import type { ApiResponse } from '@/types/ApiResponse';
import type { Task, TaskCreate, TaskUpdate } from '@/types/Task';

import { useDb } from './useDb';
import {
    boolToInt,
    intToBool,
    nowIso,
    repeatDaysFromString,
    repeatDaysToString,
} from './utils';

interface TaskRow {
    id: number;
    title: string;
    description: string | null;
    category: string | null;
    due_date: string | null;
    completed: number;
    repeat_type: string | null;
    repeat_interval: number | null;
    repeat_days: string | null;
    created_at: string;
    updated_at: string;
}

function rowToTask(row: TaskRow): Task {
    return {
        ...row,
        completed: intToBool(row.completed),
        repeat_days: repeatDaysFromString(row.repeat_days),
    };
}

function calculateNextDueDate(
    currentDue: string,
    repeatType: string,
    interval: number,
    repeatDays: number[] | null,
): string {
    const due = new Date(currentDue);

    switch (repeatType) {
        case 'daily':
            due.setDate(due.getDate() + interval);
            break;
        case 'weekly':
            if (repeatDays && repeatDays.length > 0) {
                // Skip interval-1 weeks, then find next matching day
                if (interval > 1) {
                    due.setDate(due.getDate() + (interval - 1) * 7);
                }
                for (let i = 1; i <= 7; i++) {
                    const candidate = new Date(due);
                    candidate.setDate(candidate.getDate() + i);
                    if (repeatDays.includes(candidate.getDay())) {
                        return candidate.toISOString().split('T')[0]!;
                    }
                }
                due.setDate(due.getDate() + interval * 7);
            } else {
                due.setDate(due.getDate() + interval * 7);
            }
            break;
        case 'monthly':
            due.setMonth(due.getMonth() + interval);
            break;
        default:
            return currentDue;
    }

    return due.toISOString().split('T')[0]!;
}

export function useTaskApi() {
    const { query, queryOne, run, execute } = useDb();

    const getTasks = async (
        params?: Record<string, string | number | boolean | undefined>,
    ): Promise<ApiResponse<Task[]>> => {
        const conditions: string[] = [];
        const values: unknown[] = [];

        if (params?.completed !== undefined) {
            conditions.push('completed = ?');
            values.push(
                params.completed === true || params.completed === 'true'
                    ? 1
                    : 0,
            );
        }
        if (params?.category !== undefined) {
            conditions.push('category = ?');
            values.push(params.category);
        }

        const where =
            conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
        const limit = params?.limit ? Number(params.limit) : 1000;
        const offset = params?.offset ? Number(params.offset) : 0;

        const result = await query<TaskRow>(
            `SELECT * FROM tasks ${where} ORDER BY created_at DESC LIMIT ? OFFSET ?`,
            [...values, limit, offset],
        );

        if (!result.success)
            return { data: null, error: result.error, success: false };
        return {
            data: result.data!.map(rowToTask),
            error: null,
            success: true,
        };
    };

    const getTask = async (id: number): Promise<ApiResponse<Task>> => {
        const result = await queryOne<TaskRow>(
            'SELECT * FROM tasks WHERE id = ?',
            [id],
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };
        return {
            data: rowToTask(result.data!),
            error: null,
            success: true,
        };
    };

    const createTask = async (task: TaskCreate): Promise<ApiResponse<Task>> => {
        const now = nowIso();
        const completedVal = task.completed ?? false;
        const repeatDaysVal = task.repeat_days ?? null;
        const result = await run(
            `INSERT INTO tasks (title, description, category, due_date, completed,
                                repeat_type, repeat_interval, repeat_days, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
            [
                task.title,
                task.description ?? null,
                task.category ?? null,
                task.due_date ?? null,
                boolToInt(completedVal),
                task.repeat_type ?? null,
                task.repeat_interval ?? null,
                repeatDaysToString(repeatDaysVal),
                now,
                now,
            ],
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };
        // Construct the task from known values to avoid a SELECT on iOS
        // (sql.js exec() can return columns=undefined on iOS WKWebView for non-empty results)
        const newTask: Task = {
            id: result.data!.id,
            title: task.title,
            description: task.description ?? null,
            category: task.category ?? null,
            due_date: task.due_date ?? null,
            completed: completedVal,
            repeat_type: task.repeat_type ?? null,
            repeat_interval: task.repeat_interval ?? null,
            repeat_days: repeatDaysVal,
            created_at: now,
            updated_at: now,
        };
        return { data: newTask, error: null, success: true };
    };

    const updateTask = async (
        id: number,
        task: TaskUpdate,
    ): Promise<ApiResponse<Task>> => {
        // Fetch existing for recurrence logic
        const existing = await getTask(id);
        if (!existing.success || !existing.data)
            return {
                data: null,
                error: existing.error,
                success: false,
            };

        const fields: string[] = [];
        const values: unknown[] = [];

        let completedValue = task.completed;
        let dueDateValue = task.due_date;

        // Handle recurrence: if completing a recurring task, calculate next due date
        if (
            task.completed === true &&
            existing.data.repeat_type &&
            existing.data.due_date
        ) {
            dueDateValue = calculateNextDueDate(
                existing.data.due_date,
                existing.data.repeat_type,
                existing.data.repeat_interval ?? 1,
                existing.data.repeat_days,
            );
            completedValue = false;
        }

        if (task.title !== undefined) {
            fields.push('title = ?');
            values.push(task.title);
        }
        if (task.description !== undefined) {
            fields.push('description = ?');
            values.push(task.description);
        }
        if (task.category !== undefined) {
            fields.push('category = ?');
            values.push(task.category);
        }
        if (dueDateValue !== undefined || task.due_date !== undefined) {
            fields.push('due_date = ?');
            values.push(dueDateValue ?? task.due_date ?? null);
        }
        if (completedValue !== undefined) {
            fields.push('completed = ?');
            values.push(boolToInt(completedValue ?? false));
        }
        if (task.repeat_type !== undefined) {
            fields.push('repeat_type = ?');
            values.push(task.repeat_type);
        }
        if (task.repeat_interval !== undefined) {
            fields.push('repeat_interval = ?');
            values.push(task.repeat_interval);
        }
        if (task.repeat_days !== undefined) {
            fields.push('repeat_days = ?');
            values.push(repeatDaysToString(task.repeat_days));
        }

        if (fields.length === 0) return existing;

        fields.push('updated_at = ?');
        values.push(nowIso());
        values.push(id);

        const result = await execute(
            `UPDATE tasks SET ${fields.join(', ')} WHERE id = ?`,
            values,
        );
        if (!result.success)
            return { data: null, error: result.error, success: false };
        return getTask(id);
    };

    const deleteTask = async (id: number) =>
        execute('DELETE FROM tasks WHERE id = ?', [id]);

    return { getTasks, getTask, createTask, updateTask, deleteTask };
}
