import type { ApiResponse } from '@/types/ApiResponse';
import type { ImageUpload } from '@/types/Image';

export function useImageApi() {
    const uploadImage = async (
        _file: File,
    ): Promise<ApiResponse<ImageUpload>> => {
        throw new Error('Image upload is not supported in the local backend');
    };

    return { uploadImage };
}
