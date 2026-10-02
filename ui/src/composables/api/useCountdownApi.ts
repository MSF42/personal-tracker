import type {
    Countdown,
    CountdownCreate,
    CountdownUpdate,
} from '@/types/Countdown';

import { useApi } from './useApi';

export function useCountdownApi() {
    const api = useApi();

    const getCountdowns = async () => api.getData<Countdown[]>('countdowns');

    const createCountdown = async (data: CountdownCreate) =>
        api.post<CountdownCreate, Countdown>('countdowns', data);

    const updateCountdown = async (id: number, data: CountdownUpdate) =>
        api.put<CountdownUpdate, Countdown>(`countdowns/${id}`, data);

    const deleteCountdown = async (id: number) =>
        api.remove(`countdowns/${id}`);

    return { getCountdowns, createCountdown, updateCountdown, deleteCountdown };
}
