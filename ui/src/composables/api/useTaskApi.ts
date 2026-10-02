import type { ApiResponse } from '@/types/ApiResponse';
import type { Task, TaskCreate, TaskUpdate } from '@/types/Task';

import { useApi } from './useApi';

export function useTaskApi() {
    const api = useApi();

    // The API caps a page at 100 tasks; walk every page so callers see the
    // whole list rather than the 20 most recently created.
    const getTasks = async (
        params?: Record<string, string | number | boolean | undefined>,
    ): Promise<ApiResponse<Task[]>> => {
        const PAGE_SIZE = 100;
        const tasks: Task[] = [];
        let offset = 0;
        for (;;) {
            const res = await api.getPaginated<Task>('tasks', {
                ...params,
                limit: PAGE_SIZE,
                offset,
            });
            if (!res.success || !res.data) {
                return { data: null, error: res.error, success: false };
            }
            tasks.push(...res.data.data);
            if (!res.data.has_more || res.data.data.length === 0) break;
            offset += res.data.data.length;
        }
        return { data: tasks, error: null, success: true };
    };

    const getTask = async (id: number) => api.getData<Task>(`tasks/${id}`);

    const createTask = async (task: TaskCreate) =>
        api.post<TaskCreate, Task>('tasks', task);

    const updateTask = async (id: number, task: TaskUpdate) =>
        api.put<TaskUpdate, Task>(`tasks/${id}`, task);

    const deleteTask = async (id: number) => api.remove(`tasks/${id}`);

    return { getTasks, getTask, createTask, updateTask, deleteTask };
}
