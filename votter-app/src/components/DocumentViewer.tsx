'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface DocumentViewerProps {
  pdfUrl: string;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function DocumentViewer({
  pdfUrl,
  currentPage,
  totalPages,
  onPageChange,
}: DocumentViewerProps) {
  const [iframeHeight, setIframeHeight] = useState('500px');

  useEffect(() => {
    const handleResize = () => {
      setIframeHeight(`${window.innerHeight - 300}px`);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (!pdfUrl) {
    return (
      <Card variant="glass" className="h-full" key="no-pdf">
        <div className="flex items-center justify-center min-h-[400px] text-center text-zinc-500">
          <div>
            <svg
              className="w-12 h-12 mx-auto mb-4 opacity-50"
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
            <p>No PDF loaded</p>
            <p className="text-sm mt-2">Upload a document to preview</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card variant="glass" className="h-full" key={`pdf-viewer-${currentPage}`}>
      <div className="flex justify-between items-center mb-4 flex-wrap gap-2">
        <h3 className="text-lg font-semibold">Document Preview</h3>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage <= 1}
          >
            ← Previous
          </Button>
          <span className="text-sm text-zinc-600 dark:text-zinc-400 px-2">
            Page {currentPage} of {totalPages}
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
          >
            Next →
          </Button>
        </div>
      </div>

      <div className="rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-700 bg-white">
        <iframe
          src={`${pdfUrl}#page=${currentPage}&toolbar=0&navpanes=0`}
          className="w-full"
          style={{ height: iframeHeight, minHeight: '400px' }}
          title="PDF Viewer"
        />
      </div>
    </Card>
  );
}
