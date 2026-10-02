import type { ApiResponse } from '@/types/ApiResponse';
import type {
    BestEffort,
    GpxSegment,
    RunBadge,
    RunBadgeSet,
    RunImportResponse,
    RunLap,
    RunningActivity,
    RunningActivityCreate,
    RunningActivityUpdate,
    RunningDateRange,
    RunSample,
} from '@/types/Running';

import { useApi } from './useApi';

export function useRunningApi() {
    const api = useApi();

    const getActivities = async (range?: RunningDateRange) =>
        api.getData<RunningActivity[]>('runs', { ...range });

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

    const getBadges = async (range?: RunningDateRange) =>
        api.getData<RunBadgeSet[]>('runs/badges', { ...range });

    const getRunBadges = async (runId: number) =>
        api.getData<RunBadge[]>(`runs/${runId}/badges`);

    const getBestEfforts = async () =>
        api.getData<BestEffort[]>('runs/best-efforts');

    return {
        getActivities,
        getActivity,
        createActivity,
        updateActivity,
        deleteActivity,
        importGpx,
        importFit,
        getSegments,
        getLaps,
        getSamples,
        getBadges,
        getRunBadges,
        getBestEfforts,
    };
}
