'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { DebugImage } from '@/types';

interface DebugGridGalleryProps {
  images: DebugImage[];
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function DebugGridGallery({
  images,
  currentPage,
  totalPages,
  onPageChange,
}: DebugGridGalleryProps) {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [imgErrors, setImgErrors] = useState<Record<string, boolean>>({});
  const [zoom, setZoom] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const currentImage = images.find((img) => parseInt(img.page) === currentPage);
  const hasImages = images.length > 0;

  const handleImageError = (url: string) => {
    setImgErrors((prev) => ({ ...prev, [url]: true }));
  };

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.25, 3));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.25, 0.5));
  const handleResetZoom = () => setZoom(1);

  if (!hasImages) {
    return (
      <Card variant="glass" className="w-full">
        <div className="flex items-center justify-center min-h-[400px] text-center text-zinc-500">
          <div>
            <svg
              className="w-16 h-16 mx-auto mb-4 opacity-30"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <p className="text-lg font-medium mt-4">No Grid Images Available</p>
            <p className="text-sm mt-1">
              Grid visualization will appear after processing completes
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card variant="glass" className="w-full overflow-hidden">
        {/* Header with controls */}
        <div className="flex flex-wrap justify-between items-center gap-3 pb-4 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
              <svg
                className="w-5 h-5 text-indigo-600 dark:text-indigo-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold">Grid Visualization</h3>
              <p className="text-xs text-zinc-500">
                Detected cell layout overlay
              </p>
            </div>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleZoomOut}
              className="p-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors"
              title="Zoom Out"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M20 12H4"
                />
              </svg>
            </button>
            <span className="text-sm font-mono w-16 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={handleZoomIn}
              className="p-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors"
              title="Zoom In"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 4v16m8-8H4"
                />
              </svg>
            </button>
            <button
              onClick={handleResetZoom}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors"
            >
              Reset
            </button>
          </div>
        </div>

        {/* Page Navigation */}
        <div className="flex justify-between items-center py-4">
          <Button
            size="sm"
            variant="outline"
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage <= 1}
            className="gap-1"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Previous
          </Button>

          <div className="flex items-center gap-2">
            {images.map((img) => (
              <button
                key={img.page}
                onClick={() => onPageChange(parseInt(img.page))}
                className={`w-9 h-9 rounded-lg text-sm font-medium transition-all ${parseInt(img.page) === currentPage
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                  : 'bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700'
                  }`}
              >
                {img.page}
              </button>
            ))}
          </div>

          <Button
            size="sm"
            variant="outline"
            onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
            className="gap-1"
          >
            Next
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </Button>
        </div>

        {/* Grid Image Display */}
        <div className="relative rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900/50">
          <div
            className="overflow-auto"
            style={{ maxHeight: '70vh', minHeight: '500px' }}
          >
            {currentImage && !imgErrors[currentImage.url] ? (
              <div
                className="cursor-pointer transition-transform duration-200"
                style={{
                  transform: `scale(${zoom})`,
                  transformOrigin: 'top left',
                }}
                onClick={() => setIsFullscreen(true)}
              >
                <img
                  src={currentImage.url}
                  alt={`Grid Page ${currentImage.page} - Voter card layout with detected cells`}
                  className="w-full h-auto"
                  loading="lazy"
                  onError={() => handleImageError(currentImage.url)}
                />
              </div>
            ) : (
              <div className="flex items-center justify-center min-h-[400px] text-center text-zinc-500">
                <div>
                  <svg
                    className="w-16 h-16 mx-auto mb-4 opacity-30"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                  <p className="text-lg font-medium mt-4">
                    Unable to load grid image
                  </p>
                  <p className="text-sm mt-1">
                    The visualization for page {currentPage} could not be loaded
                  </p>
                  {currentImage?.url && (
                    <button
                      onClick={() => window.open(currentImage.url, '_blank')}
                      className="mt-4 px-4 py-2 text-sm text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 underline"
                    >
                      Try opening directly
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Page info footer */}
        <div className="mt-4 pt-3 text-center text-xs text-zinc-400 border-t border-zinc-200 dark:border-zinc-800">
          <span>
            Page {currentPage} of {totalPages}
          </span>
          <span className="mx-2">•</span>
          <span>Click image to enlarge</span>
          <span className="mx-2">•</span>
          <span>Green boxes show detected voter cells</span>
        </div>
      </Card>

      {/* Fullscreen Modal */}
      {isFullscreen && currentImage && !imgErrors[currentImage.url] && (
        <div
          className="fixed inset-0 bg-black bg-opacity-95 z-50 flex items-center justify-center p-4"
          onClick={() => setIsFullscreen(false)}
        >
          <div className="relative max-w-7xl max-h-[90vh] overflow-auto">
            <img
              src={currentImage.url}
              alt={`Grid Page ${currentImage.page} - Full size`}
              className="w-full h-auto rounded-lg"
            />
            <button
              className="absolute top-4 right-4 text-white bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
              onClick={() => setIsFullscreen(false)}
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}
