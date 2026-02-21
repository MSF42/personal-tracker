import type { ApiResponse } from '@/types/ApiResponse';
import type {
    GpxImportResponse,
    GpxSegment,
    MonthlyRunStats,
    PersonalBests,
    RunningActivity,
    RunningActivityCreate,
    RunningActivityUpdate,
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
    ): Promise<ApiResponse<GpxImportResponse>> => {
        const formData = new FormData();
        formData.append('file', file);
        return api.postFormData<GpxImportResponse>('runs/import-gpx', formData);
    };

    const getSegments = async (runId: number) =>
        api.getData<GpxSegment[]>(`runs/${runId}/segments`);

    return {
        getActivities,
        getActivity,
        createActivity,
        updateActivity,
        deleteActivity,
        getYearlyStats,
        getPersonalBests,
        importGpx,
        getSegments,
    };
}
