import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { documentsApi, casesApi } from '@/api/client';
import type { AnalysisCostEstimate } from '@/types';
import {
  FileText,
  Upload,
  Trash2,
  File as FileIcon,
  Image as ImageIcon,
  FileType,
  AlertCircle,
  CheckCircle,
  Clock,
  ArrowLeft,
  Sparkles
} from 'lucide-react';

const FILE_ICONS: Record<string, any> = {
  'application/pdf': FileText,
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileType,
  'application/msword': FileType,
  'image/jpeg': ImageIcon,
  'image/png': ImageIcon,
  'text/plain': FileIcon,
};

const FILE_TYPE_LABELS: Record<string, string> = {
  'application/pdf': 'PDF',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word',
  'application/msword': 'Word',
  'image/jpeg': 'Image',
  'image/png': 'Image',
  'text/plain': 'Text',
};

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
};

interface FileUploadState {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

export default function Documents() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadQueue, setUploadQueue] = useState<FileUploadState[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<Set<string>>(new Set());
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // AI Analysis state
  const [analyzingDocs, setAnalyzingDocs] = useState<Set<string>>(new Set());
  const [showCostEstimate, setShowCostEstimate] = useState(false);
  const [costEstimate, setCostEstimate] = useState<AnalysisCostEstimate | null>(null);

  // Fetch case data
  const { data: caseData, isLoading: caseLoading } = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => casesApi.get(caseId!),
    enabled: !!caseId,
  });

  // Fetch documents
  const { data: documents, isLoading: documentsLoading } = useQuery({
    queryKey: ['documents', caseId],
    queryFn: () => documentsApi.list(caseId!),
    enabled: !!caseId,
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => documentsApi.delete(caseId!, documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', caseId] });
      setDeleteConfirmId(null);
      setSelectedDocIds(new Set());
    },
  });

  // Bulk delete mutation
  const bulkDeleteMutation = useMutation({
    mutationFn: async (documentIds: string[]) => {
      await Promise.all(documentIds.map(id => documentsApi.delete(caseId!, id)));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', caseId] });
      setBulkDeleteConfirm(false);
      setSelectedDocIds(new Set());
    },
  });

  // Analysis mutation
  const analyzeMutation = useMutation({
    mutationFn: ({ documentId, forceReanalyze }: { documentId: string; forceReanalyze: boolean }) =>
      documentsApi.analyze(caseId!, documentId, forceReanalyze),
    onSuccess: (data, variables) => {
      setAnalyzingDocs(prev => new Set(prev).add(variables.documentId));
      pollForAnalysis(variables.documentId);
    },
  });

  // Poll for analysis results
  const pollForAnalysis = (documentId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const analysis = await documentsApi.getAnalysis(caseId!, documentId);
        if (analysis.status !== 'processing') {
          clearInterval(pollInterval);
          setAnalyzingDocs(prev => {
            const newSet = new Set(prev);
            newSet.delete(documentId);
            return newSet;
          });
          queryClient.invalidateQueries({ queryKey: ['documents', caseId] });
        }
      } catch (error) {
        console.error('Failed to poll analysis:', error);
        clearInterval(pollInterval);
        setAnalyzingDocs(prev => {
          const newSet = new Set(prev);
          newSet.delete(documentId);
          return newSet;
        });
      }
    }, 3000); // Poll every 3 seconds
  };

  // Handle bulk analyze
  const handleBulkAnalyze = async () => {
    try {
      const estimate = await documentsApi.estimateCost(caseId!, Array.from(selectedDocIds));
      setCostEstimate(estimate);
      setShowCostEstimate(true);
    } catch (error) {
      console.error('Failed to estimate cost:', error);
      alert('Failed to estimate cost. Please try again.');
    }
  };

  // Confirm bulk analyze
  const confirmBulkAnalyze = async () => {
    setShowCostEstimate(false);
    try {
      await documentsApi.analyzeBulk(caseId!, Array.from(selectedDocIds));
      setSelectedDocIds(new Set());
      // Start polling for all documents
      Array.from(selectedDocIds).forEach(id => {
        setAnalyzingDocs(prev => new Set(prev).add(id));
        pollForAnalysis(id);
      });
    } catch (error) {
      console.error('Failed to start bulk analysis:', error);
      alert('Failed to start analysis. Please try again.');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setSelectedFiles(files);
      setUploadError(null);
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    // Initialize queue
    const initialQueue: FileUploadState[] = selectedFiles.map(file => ({
      file,
      status: 'pending',
      progress: 0
    }));
    setUploadQueue(initialQueue);

    // Upload files sequentially
    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];

      // Update status to uploading
      setUploadQueue(prev => prev.map((item, idx) =>
        idx === i ? { ...item, status: 'uploading', progress: 10 } : item
      ));

      try {
        await documentsApi.upload(caseId!, file);

        // Success
        setUploadQueue(prev => prev.map((item, idx) =>
          idx === i ? { ...item, status: 'success', progress: 100 } : item
        ));
      } catch (error: any) {
        // Error
        const errorMsg = error.response?.data?.detail || 'Upload failed';
        setUploadQueue(prev => prev.map((item, idx) =>
          idx === i ? { ...item, status: 'error', progress: 0, error: errorMsg } : item
        ));
      }
    }

    // Refresh documents list
    queryClient.invalidateQueries({ queryKey: ['documents', caseId] });

    // Clear after completion
    setTimeout(() => {
      setSelectedFiles([]);
      setUploadQueue([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }, 2000);
  };

  const handleDelete = (documentId: string) => {
    deleteMutation.mutate(documentId);
  };

  const handleBulkDelete = () => {
    bulkDeleteMutation.mutate(Array.from(selectedDocIds));
  };

  const toggleSelectAll = () => {
    if (selectedDocIds.size === documents?.length) {
      setSelectedDocIds(new Set());
    } else {
      setSelectedDocIds(new Set(documents?.map(d => d.document_id)));
    }
  };

  const toggleSelect = (documentId: string) => {
    const newSelected = new Set(selectedDocIds);
    if (newSelected.has(documentId)) {
      newSelected.delete(documentId);
    } else {
      newSelected.add(documentId);
    }
    setSelectedDocIds(newSelected);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'uploaded':
      case 'extracted':
      case 'analysis_complete':
      case 'approved':
        return <CheckCircle className="h-4 w-4" />;
      case 'pending':
      case 'processing':
      case 'pending_review':
        return <Clock className="h-4 w-4" />;
      case 'failed':
      case 'extraction_failed':
      case 'rejected':
      case 'poor_quality':
        return <AlertCircle className="h-4 w-4" />;
      default:
        return <CheckCircle className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'uploaded':
      case 'extracted':
      case 'analysis_complete':
      case 'approved':
        return 'bg-green-100 text-green-800';
      case 'pending':
      case 'processing':
      case 'pending_review':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
      case 'extraction_failed':
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'poor_quality':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      'uploaded': 'Uploaded',
      'pending': 'Pending',
      'processing': 'Processing',
      'failed': 'Failed',
      'extracted': 'Extracted',
      'analysis_complete': 'Analyzed',
      'extraction_failed': 'Extraction Failed',
      'poor_quality': 'Poor Quality',
      'pending_review': 'Pending Review',
      'approved': 'Approved',
      'rejected': 'Rejected'
    };
    return labels[status] || status.charAt(0).toUpperCase() + status.slice(1);
  };

  if (caseLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Case not found</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <button
            onClick={() => navigate(`/cases/${caseId}`)}
            className="flex items-center gap-2 text-blue-600 hover:text-blue-800 mb-2 text-sm"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Case Dashboard
          </button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Documents ({documents?.length || 0})
              </h1>
              <p className="text-gray-500 mt-1">{caseData.title}</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Upload Section */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Documents</h2>
          <div className="flex items-center gap-4">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFileSelect}
              accept=".pdf,.docx,.doc,.jpg,.jpeg,.png,.txt"
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-lg file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100"
            />
            <button
              onClick={handleUpload}
              disabled={selectedFiles.length === 0 || uploadQueue.some(q => q.status === 'uploading')}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
            >
              <Upload className="h-4 w-4" />
              {uploadQueue.some(q => q.status === 'uploading')
                ? 'Uploading...'
                : selectedFiles.length > 0
                ? `Upload (${selectedFiles.length})`
                : 'Upload'
              }
            </button>
          </div>

          {/* Selected Files Preview */}
          {selectedFiles.length > 0 && uploadQueue.length === 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-sm font-medium text-gray-700">
                Selected files ({selectedFiles.length}):
              </p>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {selectedFiles.map((file, idx) => (
                  <div key={idx} className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded text-sm">
                    <span className="truncate">{file.name}</span>
                    <span className="text-gray-500 ml-2">{formatFileSize(file.size)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upload Progress */}
          {uploadQueue.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-sm font-medium text-gray-700">Upload Progress:</p>
              {uploadQueue.map((item, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="truncate flex-1">{item.file.name}</span>
                    {item.status === 'uploading' && <span className="text-blue-600">Uploading...</span>}
                    {item.status === 'success' && (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    )}
                    {item.status === 'error' && (
                      <AlertCircle className="h-4 w-4 text-red-600" />
                    )}
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        item.status === 'success' ? 'bg-green-600' :
                        item.status === 'error' ? 'bg-red-600' : 'bg-blue-600'
                      }`}
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                  {item.error && (
                    <p className="text-xs text-red-600">{item.error}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {uploadError && (
            <div className="mt-3 flex items-center gap-2 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" />
              {uploadError}
            </div>
          )}

          <p className="mt-3 text-xs text-gray-500">
            Supported formats: PDF, DOCX, DOC, JPG, PNG, TXT (Max 50MB per file)
          </p>
        </div>

        {/* Documents List */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-4">
              {documents && documents.length > 0 && (
                <input
                  type="checkbox"
                  checked={selectedDocIds.size === documents.length}
                  onChange={toggleSelectAll}
                  className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                />
              )}
              <h2 className="text-lg font-semibold text-gray-900">
                {selectedDocIds.size > 0
                  ? `${selectedDocIds.size} selected`
                  : `All Documents`}
              </h2>
            </div>

            {selectedDocIds.size > 0 && (
              <div className="flex gap-2">
                <button
                  onClick={handleBulkAnalyze}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition text-sm"
                >
                  <Sparkles className="h-4 w-4" />
                  Analyze Selected
                </button>
                <button
                  onClick={() => setBulkDeleteConfirm(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition text-sm"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete Selected
                </button>
              </div>
            )}
          </div>

          {documentsLoading ? (
            <div className="px-6 py-12 text-center text-gray-500">
              Loading documents...
            </div>
          ) : documents && documents.length > 0 ? (
            <div className="divide-y divide-gray-200">
              {documents.map((doc) => {
                const IconComponent = FILE_ICONS[doc.file_type] || FileIcon;
                const fileTypeLabel = FILE_TYPE_LABELS[doc.file_type] || 'File';
                const isSelected = selectedDocIds.has(doc.document_id);

                return (
                  <div
                    key={doc.document_id}
                    className={`px-6 py-4 hover:bg-gray-50 transition ${
                      isSelected ? 'bg-blue-50' : ''
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(doc.document_id)}
                        className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                      />
                      <div className="p-2 bg-blue-50 rounded-lg">
                        <IconComponent className="h-6 w-6 text-blue-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-gray-900 truncate">
                          {doc.filename}
                        </h3>
                        <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                          <span className="font-medium text-gray-700">{fileTypeLabel}</span>
                          <span>•</span>
                          <span>{formatFileSize(doc.file_size)}</span>
                          <span>•</span>
                          <span>{new Date(doc.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span
                          className={`px-3 py-1.5 rounded-full text-sm font-semibold flex items-center gap-2 ${getStatusColor(
                            doc.status
                          )}`}
                        >
                          {getStatusIcon(doc.status)}
                          {getStatusLabel(doc.status)}
                        </span>

                        {/* Analyze button for uploaded documents */}
                        {doc.status === 'uploaded' && !analyzingDocs.has(doc.document_id) && (
                          <button
                            onClick={() => analyzeMutation.mutate({ documentId: doc.document_id, forceReanalyze: false })}
                            disabled={analyzeMutation.isPending}
                            className="px-3 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition text-sm disabled:opacity-50"
                          >
                            Analyze
                          </button>
                        )}

                        {/* Retry button for failed documents */}
                        {['failed', 'extraction_failed', 'poor_quality'].includes(doc.status) && !analyzingDocs.has(doc.document_id) && (
                          <button
                            onClick={() => analyzeMutation.mutate({ documentId: doc.document_id, forceReanalyze: true })}
                            disabled={analyzeMutation.isPending}
                            className="px-3 py-1.5 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition text-sm disabled:opacity-50 flex items-center gap-1"
                            title="Retry analysis"
                          >
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                            Retry Analysis
                          </button>
                        )}

                        {/* Analyzing status */}
                        {analyzingDocs.has(doc.document_id) && (
                          <span className="px-3 py-1.5 bg-yellow-100 text-yellow-800 rounded-lg text-sm font-medium">
                            Analyzing...
                          </span>
                        )}

                        {/* View Analysis button for completed */}
                        {doc.status === 'analysis_complete' && (
                          <button
                            onClick={() => navigate(`/cases/${caseId}/documents/${doc.document_id}`)}
                            className="px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm"
                          >
                            View Analysis
                          </button>
                        )}

                        <button
                          onClick={() => setDeleteConfirmId(doc.document_id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                          title="Delete document"
                        >
                          <Trash2 className="h-5 w-5" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="px-6 py-12 text-center text-gray-500">
              <FileIcon className="h-12 w-12 mx-auto text-gray-400 mb-3" />
              <p className="font-medium">No documents uploaded yet</p>
              <p className="text-sm mt-1">Upload your first document to get started</p>
            </div>
          )}
        </div>
      </main>

      {/* Single Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Delete Document</h2>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete this document? This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="flex-1 border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirmId)}
                disabled={deleteMutation.isPending}
                className="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Delete Confirmation Modal */}
      {bulkDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Delete Multiple Documents</h2>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete {selectedDocIds.size} document(s)? This action cannot
              be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setBulkDeleteConfirm(false)}
                className="flex-1 border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleBulkDelete}
                disabled={bulkDeleteMutation.isPending}
                className="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition disabled:opacity-50"
              >
                {bulkDeleteMutation.isPending ? 'Deleting...' : 'Delete All'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cost Estimation Modal */}
      {showCostEstimate && costEstimate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Analyze {costEstimate.total_documents} Documents?</h2>

            <div className="space-y-3 mb-6">
              <div className="flex justify-between">
                <span className="text-gray-600">Estimated Cost:</span>
                <span className="font-semibold">${costEstimate.estimated_cost_usd.toFixed(3)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Estimated Time:</span>
                <span className="font-semibold">{Math.ceil(costEstimate.estimated_time_seconds / 60)} minutes</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Remaining Budget:</span>
                <span className={`font-semibold ${costEstimate.within_budget ? 'text-green-600' : 'text-red-600'}`}>
                  ${costEstimate.remaining_budget_usd.toFixed(2)}
                </span>
              </div>
            </div>

            {!costEstimate.within_budget && (
              <div className="mb-4 p-3 bg-red-50 text-red-800 rounded text-sm">
                ⚠️ This operation exceeds your daily budget. Please reduce the number of documents or try again tomorrow.
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => setShowCostEstimate(false)}
                className="flex-1 border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={confirmBulkAnalyze}
                disabled={!costEstimate.within_budget}
                className="flex-1 bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Proceed
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
