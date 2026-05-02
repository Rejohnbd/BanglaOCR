import { TaskStatus, DownloadResponse, UploadResponse } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';

class OCRService {
  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || `Request failed: ${response.status}`);
    }

    return response.json();
  }

  async uploadPDF(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return this.request<UploadResponse>('/upload', {
      method: 'POST',
      body: formData,
    });
  }

  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    return this.request<TaskStatus>(`/status/${taskId}`);
  }

  async getCompleteResult(taskId: string): Promise<DownloadResponse> {
    return this.request<DownloadResponse>(`/download/${taskId}`);
  }

  getPDFUrl(taskId: string): string {
    return `${API_BASE_URL}/download-pdf/${taskId}`;
  }

  getDebugImageUrl(taskId: string, filename: string): string {
    return `${API_BASE_URL}/output/${taskId}/debug_grids/${filename}`;
  }
}

export const ocrApi = new OCRService();
