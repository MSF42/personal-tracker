import type { Habit, HabitCreate, HabitUpdate } from '@/types/Habit';

import { useApi } from './useApi';

export function useHabitApi() {
    const api = useApi();

    const getHabits = (includeArchived = false) =>
        api.getData<Habit[]>('habits', {
            include_archived: includeArchived,
        });

    const getHabit = (id: number) => api.getData<Habit>(`habits/${id}`);

    const createHabit = (data: HabitCreate) =>
        api.post<HabitCreate, Habit>('habits', data);

    const updateHabit = (id: number, data: HabitUpdate) =>
        api.put<HabitUpdate, Habit>(`habits/${id}`, data);

    const deleteHabit = (id: number) => api.remove(`habits/${id}`);

    const toggleCompletion = (id: number, date: string) =>
        api.post<{ date: string }, Habit>(`habits/${id}/complete`, { date });

    return {
        getHabits,
        getHabit,
        createHabit,
        updateHabit,
        deleteHabit,
        toggleCompletion,
    };
}
