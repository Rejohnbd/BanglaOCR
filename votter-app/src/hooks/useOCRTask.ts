import { useState, useEffect, useCallback, useRef } from 'react';
import { TaskStatus, DownloadResponse, ErrorResponse } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';

interface UseOCRTaskReturn {
  taskId: string | null;
  status: TaskStatus | null;
  result: DownloadResponse | null;
  isLoading: boolean;
  error: string | null;
  startTask: (file: File) => Promise<void>;
  reset: () => void;
}

export function useOCRTask(): UseOCRTaskReturn {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [result, setResult] = useState<DownloadResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 3;

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    retryCountRef.current = 0;
  }, []);

  const reset = useCallback(() => {
    stopPolling();
    setTaskId(null);
    setStatus(null);
    setResult(null);
    setIsLoading(false);
    setError(null);
    retryCountRef.current = 0;
  }, [stopPolling]);

  const fetchStatus = useCallback(
    async (id: string) => {
      try {
        const response = await fetch(`${API_BASE_URL}/status/${id}`);

        // 🔥 404 এরর হ্যান্ডলিং
        if (response.status === 404) {
          const errorData: ErrorResponse = await response.json();
          console.warn('Task not found:', errorData);
          retryCountRef.current += 1;

          if (retryCountRef.current >= maxRetries) {
            stopPolling();
            setError(
              errorData.message || 'Task expired. Please upload the file again.'
            );
            setIsLoading(false);
          }
          return;
        }

        if (!response.ok) {
          throw new Error(`Failed to fetch status: ${response.status}`);
        }

        // Reset retry count on successful response
        retryCountRef.current = 0;

        const data: TaskStatus = await response.json();
        setStatus(data);

        if (data.status === 'completed') {
          stopPolling();
          // Fetch complete result
          const resultResponse = await fetch(`${API_BASE_URL}/download/${id}`);
          if (resultResponse.ok) {
            const completeResult: DownloadResponse =
              await resultResponse.json();
            setResult(completeResult);
          } else {
            console.error(
              'Failed to fetch complete result:',
              resultResponse.status
            );
          }
          setIsLoading(false);
        } else if (data.status === 'failed') {
          stopPolling();
          setError(data.error || 'Task failed');
          setIsLoading(false);
        }
      } catch (err) {
        console.error('Status fetch error:', err);
        retryCountRef.current += 1;

        if (retryCountRef.current >= maxRetries) {
          stopPolling();
          setError('Network error. Please check if the server is running.');
          setIsLoading(false);
        }
      }
    },
    [stopPolling]
  );

  const startTask = useCallback(
    async (file: File) => {
      reset();
      setIsLoading(true);
      setError(null);

      try {
        const formData = new FormData();
        formData.append('file', file);

        const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
          method: 'POST',
          body: formData,
        });

        if (!uploadResponse.ok) {
          const errorText = await uploadResponse.text();
          throw new Error(errorText || 'Upload failed');
        }

        const { task_id } = await uploadResponse.json();
        console.log('Task ID:', task_id);
        setTaskId(task_id);

        // Initial status fetch
        await fetchStatus(task_id);

        // Start polling every 5 seconds
        pollingRef.current = setInterval(() => {
          fetchStatus(task_id);
        }, 5000);
      } catch (err) {
        console.error('Upload error:', err);
        setError(err instanceof Error ? err.message : 'Upload failed');
        setIsLoading(false);
      }
    },
    [fetchStatus, reset]
  );

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  return { taskId, status, result, isLoading, error, startTask, reset };
}
