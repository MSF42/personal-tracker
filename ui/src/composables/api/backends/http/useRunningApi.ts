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
        try {
            const response = await fetch(
                `${window.location.origin}/api/v1/runs/import-gpx`,
                { method: 'POST', body: formData },
            );
            if (!response.ok) {
                let errorMsg = 'Import failed';
                try {
                    const err = await response.json();
                    errorMsg = err.error || err.detail || errorMsg;
                } catch {
                    // ignore parse error
                }
                return {
                    data: null,
                    error: { message: errorMsg, statusCode: response.status },
                    success: false,
                };
            }
            const data = (await response.json()) as GpxImportResponse;
            return { data, error: null, success: true };
        } catch (err) {
            return {
                data: null,
                error: {
                    message:
                        err instanceof Error
                            ? err.message
                            : 'An unexpected error occurred',
                },
                success: false,
            };
        }
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
