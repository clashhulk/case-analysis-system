import { useState, useCallback, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import {
  ZoomIn,
  ZoomOut,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Maximize,
  Minimize,
  Highlighter,
  Trash2,
  X,
  Layers
} from 'lucide-react';
import type { Annotation, AnnotationCreate } from '@/types';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

// Import react-pdf styles
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

interface PdfViewerProps {
  url: string;
  annotations: Annotation[];
  onCreateAnnotation: (annotation: AnnotationCreate) => void;
  onDeleteAnnotation: (annotationId: string) => void;
}

const HIGHLIGHT_COLORS = [
  { name: 'yellow', color: '#FFEB3B', bgColor: 'rgba(255, 235, 59, 0.4)' },
  { name: 'green', color: '#4CAF50', bgColor: 'rgba(76, 175, 80, 0.4)' },
  { name: 'blue', color: '#2196F3', bgColor: 'rgba(33, 150, 243, 0.4)' },
  { name: 'pink', color: '#E91E63', bgColor: 'rgba(233, 30, 99, 0.4)' },
];

export default function PdfViewer({
  url,
  annotations,
  onCreateAnnotation,
  onDeleteAnnotation
}: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [scrollMode, setScrollMode] = useState<boolean>(false);

  // Highlight mode state
  const [highlightMode, setHighlightMode] = useState<boolean>(false);
  const [selectedColor, setSelectedColor] = useState<string>('yellow');
  const [showColorPicker, setShowColorPicker] = useState<boolean>(false);
  const [selectedText, setSelectedText] = useState<string>('');
  const [selectionRects, setSelectionRects] = useState<DOMRect[]>([]);
  const [showHighlightButton, setShowHighlightButton] = useState<boolean>(false);
  const [highlightButtonPos, setHighlightButtonPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);

  // Track PDF page dimensions for accurate annotation positioning
  const [pdfPageRect, setPdfPageRect] = useState<{ left: number; top: number; width: number; height: number } | null>(null);

  // Document loaded callback
  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setIsLoading(false);
    setError(null);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error);
    setError('Failed to load PDF document');
    setIsLoading(false);
  };

  // Navigation
  const goToPage = (page: number) => {
    if (page >= 1 && page <= numPages) {
      setCurrentPage(page);
    }
  };

  const prevPage = () => goToPage(currentPage - 1);
  const nextPage = () => goToPage(currentPage + 1);

  // Zoom controls
  const zoomIn = () => setScale(prev => Math.min(prev + 0.25, 3));
  const zoomOut = () => setScale(prev => Math.max(prev - 0.25, 0.5));
  const fitWidth = () => setScale(1.0);
  const fitPage = () => setScale(0.75);

  // Handle text selection for highlighting (only in single-page mode)
  const handleTextSelection = useCallback(() => {
    if (!highlightMode) return;

    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !selection.toString().trim()) {
      setShowHighlightButton(false);
      return;
    }

    const text = selection.toString().trim();
    if (!text) return;

    setSelectedText(text);
    const range = selection.getRangeAt(0);
    const rects = Array.from(range.getClientRects());

    if (rects.length > 0) {
      setSelectionRects(rects);

      // Find the PDF page element containing the selection
      let targetPage: HTMLElement | null = null;
      let pageNumber = currentPage;

      if (scrollMode) {
        // Scroll mode: traverse DOM to find page container with data-page-number
        const startContainer = range.startContainer;
        let element = startContainer instanceof Element ? startContainer : startContainer.parentElement;

        while (element) {
          if (element.hasAttribute('data-page-number')) {
            pageNumber = parseInt(element.getAttribute('data-page-number') || '1');
            targetPage = element.querySelector('.react-pdf__Page') as HTMLElement;
            break;
          }
          element = element.parentElement;
        }
      } else {
        // Single page mode: get page from ref
        if (pageRef.current) {
          targetPage = pageRef.current.querySelector('.react-pdf__Page') as HTMLElement;
        }
      }

      // Position color picker button at end of selection
      if (targetPage) {
        const pageRect = targetPage.getBoundingClientRect();
        const lastRect = rects[rects.length - 1];
        setHighlightButtonPos({
          x: lastRect.right - pageRect.left,
          y: lastRect.bottom - pageRect.top + 5
        });
        setCurrentPage(pageNumber);
        setShowHighlightButton(true);
      }
    }
  }, [highlightMode, scrollMode, currentPage]);

  // Create highlight annotation from current selection
  const createHighlight = (colorOverride?: string) => {
    if (selectionRects.length === 0) return;

    // Find the PDF page element containing the selection
    let targetPage: HTMLElement | null = null;
    let pageNumber = currentPage;

    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0 && scrollMode) {
      // Scroll mode: find page by traversing DOM
      const range = selection.getRangeAt(0);
      const startContainer = range.startContainer;
      let element = startContainer instanceof Element ? startContainer : startContainer.parentElement;

      while (element) {
        if (element.hasAttribute('data-page-number')) {
          pageNumber = parseInt(element.getAttribute('data-page-number') || '1');
          targetPage = element.querySelector('.react-pdf__Page') as HTMLElement;
          break;
        }
        element = element.parentElement;
      }
    } else if (pageRef.current) {
      // Single page mode: get page from ref
      targetPage = pageRef.current.querySelector('.react-pdf__Page') as HTMLElement;
    }

    if (!targetPage) return;

    // Convert selection rects to percentage-based coordinates (zoom-invariant)
    const pageRect = targetPage.getBoundingClientRect();
    const annotationRects = selectionRects.map(rect => ({
      x: ((rect.left - pageRect.left) / pageRect.width) * 100,
      y: ((rect.top - pageRect.top) / pageRect.height) * 100,
      width: (rect.width / pageRect.width) * 100,
      height: (rect.height / pageRect.height) * 100
    }));

    onCreateAnnotation({
      page: pageNumber,
      rects: annotationRects,
      color: colorOverride || selectedColor,
      text: selectedText
    });

    // Clear selection state
    window.getSelection()?.removeAllRanges();
    setShowHighlightButton(false);
    setSelectionRects([]);
    setSelectedText('');
  };

  // Listen for text selection
  useEffect(() => {
    const handleMouseUp = () => {
      setTimeout(handleTextSelection, 10);
    };

    document.addEventListener('mouseup', handleMouseUp);
    return () => document.removeEventListener('mouseup', handleMouseUp);
  }, [handleTextSelection]);

  // Update PDF page dimensions whenever scale changes or page changes
  useEffect(() => {
    const updatePageRect = () => {
      if (!pageRef.current) return;

      const pdfPage = pageRef.current.querySelector('.react-pdf__Page') as HTMLElement;
      if (pdfPage) {
        const rect = pdfPage.getBoundingClientRect();
        const containerRect = pageRef.current.getBoundingClientRect();
        setPdfPageRect({
          left: rect.left - containerRect.left,
          top: rect.top - containerRect.top,
          width: rect.width,
          height: rect.height
        });
      }
    };

    // Update after a short delay to ensure PDF is rendered
    const timer = setTimeout(updatePageRect, 100);

    // Also update on window resize
    window.addEventListener('resize', updatePageRect);

    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', updatePageRect);
    };
  }, [scale, currentPage, numPages, scrollMode]);

  // Get annotations for current page
  const currentPageAnnotations = annotations.filter(a => a.page === currentPage);

  // Get color config
  const getColorConfig = (colorName: string) =>
    HIGHLIGHT_COLORS.find(c => c.name === colorName) || HIGHLIGHT_COLORS[0];

  return (
    <div className="flex flex-col h-full bg-gray-100">
      {/* Toolbar */}
      <div className="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between flex-wrap gap-2">
        {/* Page Navigation - Hidden in scroll mode */}
        {!scrollMode && (
          <div className="flex items-center gap-2">
            <button
              onClick={prevPage}
              disabled={currentPage <= 1}
              className="p-1.5 hover:bg-gray-100 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              title="Previous page"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-1">
              <input
                type="number"
                min={1}
                max={numPages}
                value={currentPage}
                onChange={(e) => goToPage(parseInt(e.target.value) || 1)}
                className="w-12 text-center border border-gray-300 rounded px-1 py-0.5 text-sm"
              />
              <span className="text-sm text-gray-600">/ {numPages}</span>
            </div>

            <button
              onClick={nextPage}
              disabled={currentPage >= numPages}
              className="p-1.5 hover:bg-gray-100 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              title="Next page"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>
        )}

        {scrollMode && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 font-medium">
              All Pages ({numPages})
            </span>
          </div>
        )}

        {/* Zoom Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={zoomOut}
            disabled={scale <= 0.5}
            className="p-1.5 hover:bg-gray-100 rounded disabled:opacity-50"
            title="Zoom out"
          >
            <ZoomOut className="h-5 w-5" />
          </button>

          <span className="text-sm text-gray-600 w-14 text-center">
            {Math.round(scale * 100)}%
          </span>

          <button
            onClick={zoomIn}
            disabled={scale >= 3}
            className="p-1.5 hover:bg-gray-100 rounded disabled:opacity-50"
            title="Zoom in"
          >
            <ZoomIn className="h-5 w-5" />
          </button>

          <div className="h-6 w-px bg-gray-300 mx-1" />

          <button
            onClick={fitWidth}
            className="p-1.5 hover:bg-gray-100 rounded text-sm"
            title="Fit to width"
          >
            <Maximize className="h-5 w-5" />
          </button>

          <button
            onClick={fitPage}
            className="p-1.5 hover:bg-gray-100 rounded text-sm"
            title="Fit to page"
          >
            <Minimize className="h-5 w-5" />
          </button>

          <div className="h-6 w-px bg-gray-300 mx-1" />

          <button
            onClick={() => setScrollMode(!scrollMode)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-sm font-medium ${
              scrollMode ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-100 text-gray-700'
            }`}
            title={scrollMode ? 'Single page mode' : 'Scroll mode (all pages)'}
          >
            <Layers className="h-4 w-4" />
            <span className="text-xs">{scrollMode ? 'Single' : 'All Pages'}</span>
          </button>
        </div>

        {/* Highlight Controls - Only available in single page mode */}
        {!scrollMode && (
          <div className="flex items-center gap-2">
              <button
                onClick={() => setHighlightMode(!highlightMode)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                  highlightMode
                    ? 'bg-yellow-100 text-yellow-800 border border-yellow-300'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                title="Toggle highlight mode"
              >
                <Highlighter className="h-4 w-4" />
                {highlightMode ? 'Highlighting' : 'Highlight'}
              </button>

              {highlightMode && (
                <div className="relative">
                  <button
                    onClick={() => setShowColorPicker(!showColorPicker)}
                    className="flex items-center gap-1.5 px-2 py-1.5 rounded border border-gray-300 hover:bg-gray-50"
                  >
                    <div
                      className="w-4 h-4 rounded"
                      style={{ backgroundColor: getColorConfig(selectedColor).color }}
                    />
                    <ChevronLeft className="h-3 w-3 rotate-[-90deg]" />
                  </button>

                  {showColorPicker && (
                    <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-2 z-50">
                      <div className="flex gap-1">
                        {HIGHLIGHT_COLORS.map((c) => (
                          <button
                            key={c.name}
                            onClick={() => {
                              setSelectedColor(c.name);
                              setShowColorPicker(false);
                            }}
                            className={`w-8 h-8 rounded border-2 ${
                              selectedColor === c.name
                                ? 'border-gray-800'
                                : 'border-transparent'
                            }`}
                            style={{ backgroundColor: c.color }}
                            title={c.name}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
          </div>
        )}
      </div>

      {/* PDF Container */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto flex justify-center p-4"
      >
        {error ? (
          <div className="flex flex-col items-center justify-center text-red-500">
            <X className="h-12 w-12 mb-2" />
            <p>{error}</p>
          </div>
        ) : scrollMode ? (
          // Scroll Mode - All pages
          <div className="space-y-4">
            <Document
              file={url}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                </div>
              }
            >
              {Array.from(new Array(numPages), (_, index) => {
                const pageNum = index + 1;
                const pageAnnotations = annotations.filter(a => a.page === pageNum);

                return (
                  <div key={pageNum} className="relative mb-4" data-page-number={pageNum}>
                    <div className="relative">
                      <Page
                        pageNumber={pageNum}
                        scale={scale}
                        renderTextLayer={true}
                        renderAnnotationLayer={true}
                        loading={
                          <div className="flex items-center justify-center p-8 min-h-[600px]">
                            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                          </div>
                        }
                        className="shadow-lg"
                      />

                      {/* Page number label */}
                      <div className="absolute top-2 left-2 bg-black bg-opacity-50 text-white px-2 py-1 rounded text-sm z-10">
                        Page {pageNum}
                      </div>

                      {/* Render annotations for this page - positioned relative to the Page component */}
                      {pageAnnotations.map((annotation) => (
                        <div key={annotation.id} className="absolute inset-0 pointer-events-none">
                          {annotation.rects.map((rect, idx) => (
                            <div
                              key={idx}
                              className="absolute group"
                              style={{
                                left: `${rect.x}%`,
                                top: `${rect.y}%`,
                                width: `${rect.width}%`,
                                height: `${rect.height}%`,
                                backgroundColor: getColorConfig(annotation.color).bgColor,
                                pointerEvents: 'none'
                              }}
                              title={annotation.text || 'Highlight'}
                            >
                              {idx === 0 && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onDeleteAnnotation(annotation.id);
                                  }}
                                  className="absolute -top-6 -right-1 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition pointer-events-auto z-10"
                                  title="Delete highlight"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </button>
                              )}
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </Document>
          </div>
        ) : (
          // Single Page Mode
          <div className="relative" ref={pageRef}>
            <Document
              file={url}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                </div>
              }
            >
              <Page
                pageNumber={currentPage}
                scale={scale}
                renderTextLayer={true}
                renderAnnotationLayer={true}
                loading={
                  <div className="flex items-center justify-center p-8 min-h-[600px]">
                    <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                  </div>
                }
                className="shadow-lg"
              />
            </Document>

            {/* Render annotations: overlay positioned to match PDF page exactly */}
            {(() => {
              const pdfPage = pageRef.current?.querySelector('.react-pdf__Page') as HTMLElement;
              if (!pdfPage) return null;

              const pageRect = pdfPage.getBoundingClientRect();
              const containerRect = pageRef.current?.getBoundingClientRect();
              if (!containerRect) return null;

              return currentPageAnnotations.map((annotation) => (
                <div
                  key={annotation.id}
                  className="absolute pointer-events-none"
                  style={{
                    left: pageRect.left - containerRect.left,
                    top: pageRect.top - containerRect.top,
                    width: pageRect.width,
                    height: pageRect.height
                  }}
                >
                  {annotation.rects.map((rect, idx) => (
                    <div
                      key={idx}
                      className="absolute group"
                      style={{
                        left: `${rect.x}%`,
                        top: `${rect.y}%`,
                        width: `${rect.width}%`,
                        height: `${rect.height}%`,
                        backgroundColor: getColorConfig(annotation.color).bgColor,
                        pointerEvents: 'none'
                      }}
                      title={annotation.text || 'Highlight'}
                    >
                      {/* Delete button on hover - only show on first rect */}
                      {idx === 0 && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteAnnotation(annotation.id);
                          }}
                          className="absolute -top-6 -right-1 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition pointer-events-auto z-10"
                          title="Delete highlight"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              ));
            })()}

            {/* Highlight button that appears on text selection */}
            {showHighlightButton && highlightMode && (
              <div
                className="absolute z-50 bg-white rounded-lg shadow-lg border border-gray-200 p-1 flex gap-1"
                style={{
                  left: highlightButtonPos.x,
                  top: highlightButtonPos.y,
                }}
              >
                {HIGHLIGHT_COLORS.map((c) => (
                  <button
                    key={c.name}
                    onClick={() => {
                      setSelectedColor(c.name);
                      createHighlight(c.name);
                    }}
                    className="w-6 h-6 rounded hover:scale-110 transition"
                    style={{ backgroundColor: c.color }}
                    title={`Highlight ${c.name}`}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      )}

      {/* Highlight mode indicator - Only show in single page mode */}
      {highlightMode && !scrollMode && (
        <div className="absolute bottom-4 left-4 bg-yellow-100 text-yellow-800 px-3 py-1.5 rounded-lg text-sm font-medium shadow">
          Select text to highlight
        </div>
      )}
    </div>
  );
}
