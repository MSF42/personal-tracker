import type { ApiResponse } from '@/types/ApiResponse';
import type { ImageUpload } from '@/types/Image';

import { useApi } from './useApi';

export function useImageApi() {
    const api = useApi();

    const uploadImage = async (
        file: File,
    ): Promise<ApiResponse<ImageUpload>> => {
        const formData = new FormData();
        formData.append('file', file);
        return api.postFormData<ImageUpload>('images', formData);
    };

    return { uploadImage };
}
