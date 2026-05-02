'use client';

import { useCallback, useState, useMemo } from 'react';
import { useOCRTask } from '@/hooks/useOCRTask';
import { UploadSection } from '@/components/UploadSection';
import { StatusSection } from '@/components/StatusSection';
import { MemoryGame } from '@/components/MemoryGame';
import { DebugGridGallery } from '@/components/DebugGridGallery';
import { VoterTable } from '@/components/VoterTable';

export default function Home() {
  const { status, result, isLoading, error, startTask, reset } = useOCRTask();
  const [currentPage, setCurrentPage] = useState(1);

  const totalPages = useMemo(() => {
    return result?.summary?.total_pages || 1;
  }, [result?.summary?.total_pages]);

  const handleUpload = useCallback(
    async (file: File) => {
      setCurrentPage(1);
      await startTask(file);
    },
    [startTask]
  );

  const handleReset = useCallback(() => {
    reset();
    setCurrentPage(1);
  }, [reset]);

  const isProcessing = status?.status === 'processing' && !result;
  const isCompleted = result?.status === 'completed' && result !== null;

  // Initial upload state - show upload form only
  if (!isProcessing && !isCompleted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-zinc-50 via-white to-zinc-50 dark:from-black dark:via-zinc-900 dark:to-black">
        <div className="max-w-2xl mx-auto px-4 py-12">
          <div className="text-center mb-12">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-600 mb-6 shadow-lg shadow-indigo-500/25">
              <svg
                className="w-8 h-8 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
              Bangla Voter OCR
            </h1>
            <p className="mt-3 text-zinc-500 dark:text-zinc-400 max-w-lg mx-auto">
              Upload your voter list PDF and let our AI engine extract
              structured data with high accuracy
            </p>
          </div>

          <UploadSection
            onUpload={handleUpload}
            isLoading={isLoading}
            error={error}
          />
        </div>
      </div>
    );
  }

  // Processing state - show progress and game
  if (isProcessing && status) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-zinc-50 via-white to-zinc-50 dark:from-black dark:via-zinc-900 dark:to-black">
        <div className="max-w-4xl mx-auto px-4 py-12">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-600 mb-4 shadow-lg shadow-indigo-500/25">
              <svg
                className="w-6 h-6 text-white animate-pulse"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold">Processing Your Document</h2>
            <p className="text-zinc-500 dark:text-zinc-400 mt-1">
              Please wait while we extract voter information
            </p>
          </div>

          <div className="space-y-6">
            <StatusSection status={status} />
            <MemoryGame />

            <button
              onClick={handleReset}
              className="w-full text-center text-sm text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 transition-colors py-4"
            >
              ← Cancel and Upload New File
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Completed state - show results (only DebugGridGallery and VoterTable)
  if (isCompleted && result) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-zinc-50 via-white to-zinc-50 dark:from-black dark:via-zinc-900 dark:to-black">
        <div className="max-w-7xl mx-auto px-4 py-8">
          {/* Success Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-green-500/20 mb-4">
              <svg
                className="w-6 h-6 text-green-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold">Extraction Complete</h2>
            <p className="text-zinc-500 dark:text-zinc-400 mt-1">
              Successfully extracted {result.summary?.total_voters || 0} voters
              from {result.summary?.total_pages || 0} pages
            </p>
          </div>

          {/* Only Debug Grid Gallery - Full width */}
          <div className="mb-8">
            <DebugGridGallery
              images={result.debug_grids || []}
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={setCurrentPage}
            />
          </div>

          {/* Voter Table */}
          <VoterTable voters={result.data || []} />

          {/* Reset Button */}
          <div className="flex justify-center mt-8 pt-6 border-t border-zinc-200 dark:border-zinc-800">
            <button
              onClick={handleReset}
              className="px-6 py-3 text-sm font-medium bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded-xl transition-colors"
            >
              ← Process Another Document
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
