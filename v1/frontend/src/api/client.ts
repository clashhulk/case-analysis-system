import axios from 'axios';
import type {
  Case,
  CreateCaseRequest,
  UpdateCaseRequest,
  Document,
  DocumentUploadResponse,
  DocumentAnalysis,
  AnalysisCostEstimate,
  DocumentPreviewUrl,
  AnalysisUpdateRequest,
  Annotation,
  AnnotationCreate
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Cases API
export const casesApi = {
  list: async (): Promise<Case[]> => {
    const response = await api.get<Case[]>('/cases/');
    return response.data;
  },

  get: async (caseId: string): Promise<Case> => {
    const response = await api.get<Case>(`/cases/${caseId}`);
    return response.data;
  },

  create: async (data: CreateCaseRequest): Promise<Case> => {
    const response = await api.post<Case>('/cases/', data);
    return response.data;
  },

  update: async (caseId: string, data: UpdateCaseRequest): Promise<Case> => {
    const response = await api.patch<Case>(`/cases/${caseId}`, data);
    return response.data;
  },

  delete: async (caseId: string): Promise<void> => {
    await api.delete(`/cases/${caseId}`);
  },
};

// Documents API
export const documentsApi = {
  list: async (caseId: string): Promise<Document[]> => {
    const response = await api.get<Document[]>(`/cases/${caseId}/documents/`);
    return response.data;
  },

  get: async (caseId: string, documentId: string): Promise<Document> => {
    const response = await api.get<Document>(`/cases/${caseId}/documents/${documentId}`);
    return response.data;
  },

  upload: async (caseId: string, file: File): Promise<DocumentUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<DocumentUploadResponse>(
      `/cases/${caseId}/documents/`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  delete: async (caseId: string, documentId: string): Promise<void> => {
    await api.delete(`/cases/${caseId}/documents/${documentId}`);
  },

  // AI Analysis methods
  analyze: async (caseId: string, documentId: string, forceReanalyze: boolean = false): Promise<DocumentAnalysis> => {
    const response = await api.post<DocumentAnalysis>(
      `/cases/${caseId}/documents/${documentId}/analyze`,
      { force_reanalyze: forceReanalyze }
    );
    return response.data;
  },

  getAnalysis: async (caseId: string, documentId: string): Promise<DocumentAnalysis> => {
    const response = await api.get<DocumentAnalysis>(
      `/cases/${caseId}/documents/${documentId}/analysis`
    );
    return response.data;
  },

  analyzeBulk: async (caseId: string, documentIds: string[], forceReanalyze: boolean = false): Promise<any> => {
    const response = await api.post(
      `/cases/${caseId}/documents/analyze-bulk`,
      {
        document_ids: documentIds,
        force_reanalyze: forceReanalyze
      }
    );
    return response.data;
  },

  estimateCost: async (caseId: string, documentIds: string[]): Promise<AnalysisCostEstimate> => {
    const response = await api.post<AnalysisCostEstimate>(
      `/cases/${caseId}/documents/estimate-cost`,
      { document_ids: documentIds }
    );
    return response.data;
  },

  // Document Detail View methods
  getPreviewUrl: async (caseId: string, documentId: string): Promise<DocumentPreviewUrl> => {
    const response = await api.get<DocumentPreviewUrl>(
      `/cases/${caseId}/documents/${documentId}/preview-url`
    );
    return response.data;
  },

  updateAnalysis: async (caseId: string, documentId: string, data: AnalysisUpdateRequest): Promise<DocumentAnalysis> => {
    const response = await api.patch<DocumentAnalysis>(
      `/cases/${caseId}/documents/${documentId}/analysis`,
      data
    );
    return response.data;
  },

  getAnnotations: async (caseId: string, documentId: string): Promise<Annotation[]> => {
    const response = await api.get<Annotation[]>(
      `/cases/${caseId}/documents/${documentId}/annotations`
    );
    return response.data;
  },

  createAnnotation: async (caseId: string, documentId: string, data: AnnotationCreate): Promise<Annotation> => {
    const response = await api.post<Annotation>(
      `/cases/${caseId}/documents/${documentId}/annotations`,
      data
    );
    return response.data;
  },

  deleteAnnotation: async (caseId: string, documentId: string, annotationId: string): Promise<void> => {
    await api.delete(`/cases/${caseId}/documents/${documentId}/annotations/${annotationId}`);
  },

  exportDocx: async (caseId: string, documentId: string): Promise<Blob> => {
    const response = await api.get(
      `/cases/${caseId}/documents/${documentId}/export/docx`,
      { responseType: 'blob' }
    );
    return response.data;
  },

  exportMarkdown: async (caseId: string, documentId: string): Promise<Blob> => {
    const response = await api.get(
      `/cases/${caseId}/documents/${documentId}/export/markdown`,
      { responseType: 'blob' }
    );
    return response.data;
  },
};
