import type { ApiResponse } from '@/types/ApiResponse';
import type {
    GpxSegment,
    MonthlyRunStats,
    PersonalBests,
    RunImportResponse,
    RunLap,
    RunningActivity,
    RunningActivityCreate,
    RunningActivityUpdate,
    RunSample,
} from '@/types/Running';

import { useApi } from './useApi';

export function useRunningApi() {
    const api = useApi();

    const getActivities = async () => api.getData<RunningActivity[]>('runs');

    const getActivity = async (id: number) =>
        api.getData<RunningActivity>(`runs/${id}`);

    const createActivity = async (activity: RunningActivityCreate) =>
        api.post<RunningActivityCreate, RunningActivity>('runs', activity);

    const updateActivity = async (
        id: number,
        activity: RunningActivityUpdate,
    ) =>
        api.put<RunningActivityUpdate, RunningActivity>(`runs/${id}`, activity);

    const deleteActivity = async (id: number) => api.remove(`runs/${id}`);

    const getYearlyStats = async (year: number) =>
        api.getData<MonthlyRunStats[]>(`runs/stats/${year}`);

    const getPersonalBests = async () =>
        api.getData<PersonalBests>('runs/personal-bests');

    const importGpx = async (
        file: File,
    ): Promise<ApiResponse<RunImportResponse>> => {
        const formData = new FormData();
        formData.append('file', file);
        return api.postFormData<RunImportResponse>('runs/import-gpx', formData);
    };

    const importFit = async (
        file: File,
    ): Promise<ApiResponse<RunImportResponse>> => {
        const formData = new FormData();
        formData.append('file', file);
        return api.postFormData<RunImportResponse>('runs/import-fit', formData);
    };

    const getSegments = async (runId: number) =>
        api.getData<GpxSegment[]>(`runs/${runId}/segments`);

    const getLaps = async (runId: number) =>
        api.getData<RunLap[]>(`runs/${runId}/laps`);

    const getSamples = async (runId: number, maxPoints = 600) =>
        api.getData<RunSample[]>(`runs/${runId}/samples`, {
            max_points: maxPoints,
        });

    return {
        getActivities,
        getActivity,
        createActivity,
        updateActivity,
        deleteActivity,
        getYearlyStats,
        getPersonalBests,
        importGpx,
        importFit,
        getSegments,
        getLaps,
        getSamples,
    };
}
