import { useToast } from '@/composables/useToast';
import type {
    ApiError,
    ApiResponse,
    BackendError,
    FetchOptions,
    PaginatedData,
} from '@/types/ApiResponse';
import {
    getStatusMessage,
    HttpMethod,
    isNoContent,
    isSuccessStatus,
} from '@/types/ApiResponse';

function getBaseUrl(): string {
    const base = import.meta.env.VITE_API_BASE_URL ?? window.location.origin;
    return `${base}/api/v1/`;
}

function buildUrl(
    endpoint: string,
    params?: Record<string, string | number | boolean | undefined>,
): string {
    const url = new URL(endpoint, getBaseUrl());
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined) {
                url.searchParams.append(key, String(value));
            }
        });
    }
    return url.toString();
}

function handleHttpError(
    status: number,
    showApiError: (error: ApiError) => void,
    backendError?: BackendError,
    endpoint?: string,
): ApiError {
    const apiError: ApiError = {
        message: backendError?.error || getStatusMessage(status),
        statusCode: status,
        endpoint,
        code: backendError?.code,
    };
    showApiError(apiError);
    return apiError;
}

async function request<T>(
    endpoint: string,
    showApiError: (error: ApiError) => void,
    options: FetchOptions = {},
): Promise<ApiResponse<T>> {
    const { method = HttpMethod.GET, body, params } = options;
    const url = buildUrl(endpoint, params);

    const fetchOptions: RequestInit = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (body) {
        fetchOptions.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(url, fetchOptions);

        if (!isSuccessStatus(response.status)) {
            let backendError: BackendError | undefined;
            try {
                backendError = await response.json();
            } catch {
                // Response body isn't JSON
            }
            return {
                data: null,
                error: handleHttpError(
                    response.status,
                    showApiError,
                    backendError,
                    endpoint,
                ),
                success: false,
            };
        }

        if (isNoContent(response.status)) {
            return { data: null, error: null, success: true };
        }

        const data = (await response.json()) as T;
        return { data, error: null, success: true };
    } catch (err) {
        const apiError: ApiError = {
            message:
                err instanceof Error
                    ? err.message
                    : 'An unexpected error occurred',
            endpoint,
        };
        showApiError(apiError);
        return { data: null, error: apiError, success: false };
    }
}

async function requestFormData<T>(
    endpoint: string,
    showApiError: (error: ApiError) => void,
    formData: FormData,
): Promise<ApiResponse<T>> {
    const url = buildUrl(endpoint);
    try {
        const response = await fetch(url, {
            method: HttpMethod.POST,
            body: formData,
        });

        if (!isSuccessStatus(response.status)) {
            let backendError: BackendError | undefined;
            try {
                backendError = await response.json();
            } catch {
                // Response body isn't JSON
            }
            return {
                data: null,
                error: handleHttpError(
                    response.status,
                    showApiError,
                    backendError,
                    endpoint,
                ),
                success: false,
            };
        }

        if (isNoContent(response.status)) {
            return { data: null, error: null, success: true };
        }

        const data = (await response.json()) as T;
        return { data, error: null, success: true };
    } catch (err) {
        const apiError: ApiError = {
            message:
                err instanceof Error
                    ? err.message
                    : 'An unexpected error occurred',
            endpoint,
        };
        showApiError(apiError);
        return { data: null, error: apiError, success: false };
    }
}

export function useApi() {
    const { showApiError } = useToast();
    const getData = async <T>(
        endpoint: string,
        params?: Record<string, string | number | boolean | undefined>,
    ): Promise<ApiResponse<T>> => {
        return request<T>(endpoint, showApiError, { params });
    };

    const getDataArray = async <T>(
        endpoint: string,
        params?: Record<string, string | number | boolean | undefined>,
    ): Promise<ApiResponse<T[]>> => {
        const response = await request<PaginatedData<T>>(
            endpoint,
            showApiError,
            { params },
        );
        if (response.success && response.data) {
            return { data: response.data.data, error: null, success: true };
        }
        return { data: null, error: response.error, success: false };
    };

    const getPaginated = async <T>(
        endpoint: string,
        params?: Record<string, string | number | boolean | undefined>,
    ): Promise<ApiResponse<PaginatedData<T>>> => {
        return request<PaginatedData<T>>(endpoint, showApiError, { params });
    };

    const post = async <TBody, TResponse>(
        endpoint: string,
        body: TBody,
    ): Promise<ApiResponse<TResponse>> => {
        return request<TResponse>(endpoint, showApiError, {
            method: HttpMethod.POST,
            body,
        });
    };

    const put = async <TBody, TResponse>(
        endpoint: string,
        body: TBody,
    ): Promise<ApiResponse<TResponse>> => {
        return request<TResponse>(endpoint, showApiError, {
            method: HttpMethod.PUT,
            body,
        });
    };

    const postWithParams = async <T>(
        endpoint: string,
        params: Record<string, string | number | boolean | undefined>,
    ): Promise<ApiResponse<T>> => {
        return request<T>(endpoint, showApiError, {
            method: HttpMethod.POST,
            params,
        });
    };

    const remove = async (endpoint: string): Promise<ApiResponse<void>> => {
        return request<void>(endpoint, showApiError, {
            method: HttpMethod.DELETE,
        });
    };

    const postFormData = async <T>(
        endpoint: string,
        formData: FormData,
    ): Promise<ApiResponse<T>> => {
        return requestFormData<T>(endpoint, showApiError, formData);
    };

    return {
        getData,
        getDataArray,
        getPaginated,
        post,
        postWithParams,
        put,
        remove,
        postFormData,
    };
}
