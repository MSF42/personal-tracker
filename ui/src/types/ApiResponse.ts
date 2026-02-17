export interface ApiResponse<T> {
    data: T | null;
    error: ApiError | null;
    success: boolean;
}

export interface PaginatedData<T> {
    data: T[];
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
}

export interface ApiError {
    message: string;
    statusCode?: number;
    endpoint?: string;
    code?: string;
}

export const HttpStatus = {
    OK: 200,
    CREATED: 201,
    NO_CONTENT: 204,
    BAD_REQUEST: 400,
    NOT_FOUND: 404,
    CONFLICT: 409,
    UNPROCESSABLE_ENTITY: 422,
    INTERNAL_SERVER_ERROR: 500,
} as const;

export const HttpMethod = {
    GET: 'GET',
    POST: 'POST',
    PUT: 'PUT',
    DELETE: 'DELETE',
} as const;

export type HttpStatusCode = (typeof HttpStatus)[keyof typeof HttpStatus];
export type HttpMethodType = (typeof HttpMethod)[keyof typeof HttpMethod];

export function isSuccessStatus(status: number): boolean {
    return status >= 200 && status < 300;
}

export function isNoContent(status: number): boolean {
    return status === HttpStatus.NO_CONTENT;
}

export function getStatusMessage(status: number): string {
    switch (status) {
        case HttpStatus.BAD_REQUEST:
            return 'Bad request';
        case HttpStatus.NOT_FOUND:
            return 'Resource not found';
        case HttpStatus.CONFLICT:
            return 'Resource conflict';
        case HttpStatus.UNPROCESSABLE_ENTITY:
            return 'Validation error';
        case HttpStatus.INTERNAL_SERVER_ERROR:
            return 'Internal server error';
        default:
            return `Unexpected error (${status})`;
    }
}

export interface FetchOptions {
    method?: HttpMethodType;
    body?: unknown;
    params?: Record<string, string | number | boolean | undefined>;
}

export interface BackendError {
    error: string;
    code: string;
}
