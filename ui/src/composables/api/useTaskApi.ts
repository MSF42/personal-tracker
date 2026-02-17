import { useApi } from '@/composables/api/useApi';
import type { Task, TaskCreate, TaskUpdate } from '@/types/Task';

export function useTaskApi() {
    const api = useApi();

    const getTasks = async (
        params?: Record<string, string | number | boolean | undefined>,
    ) => api.getDataArray<Task>('tasks', params);

    const getTask = async (id: number) => api.getData<Task>(`tasks/${id}`);

    const createTask = async (task: TaskCreate) =>
        api.post<TaskCreate, Task>('tasks', task);

    const updateTask = async (id: number, task: TaskUpdate) =>
        api.put<TaskUpdate, Task>(`tasks/${id}`, task);

    const deleteTask = async (id: number) => api.remove(`tasks/${id}`);

    return { getTasks, getTask, createTask, updateTask, deleteTask };
}
