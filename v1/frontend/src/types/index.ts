// Core data types matching backend schemas

export interface Case {
  case_id: string;
  title: string;
  case_number: string;
  status: 'draft' | 'active' | 'archived';
  case_metadata: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface CreateCaseRequest {
  title: string;
  case_number: string;
  metadata?: Record<string, any>;
}

export interface UpdateCaseRequest {
  title?: string;
  status?: 'draft' | 'active' | 'archived';
  metadata?: Record<string, any>;
}

export interface Document {
  document_id: string;
  case_id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  s3_key: string;
  s3_bucket: string;
  status: 'uploaded' | 'processing' | 'failed' | 'analysis_complete' | 'extraction_failed' | 'poor_quality';
  document_metadata: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  document: Document;
  message: string;
}

// AI Analysis Types

export interface DocumentAnalysis {
  document_id: string;
  status: string;
  extraction?: {
    text: string;
    text_length: number;
    quality_score: number;
    extracted_at: string;
    extraction_method: string;
    metadata?: Record<string, any>;
  };
  analysis?: {
    summary: string;
    classification: string;
    confidence: number;
    key_points: string[];
    model: string;
  };
  entities?: {
    people: Array<{
      name: string;
      role: string;
      confidence: number;
    }>;
    dates: string[];
    locations: string[];
    case_numbers: string[];
    organizations?: string[];
    model: string;
  };
  processing?: {
    started_at: string;
    completed_at?: string;
    duration_ms?: number;
    total_cost_usd?: number;
    error?: string;
  };
}

export interface AnalyzeDocumentRequest {
  force_reanalyze?: boolean;
}

export interface BulkAnalyzeRequest {
  document_ids: string[];
  force_reanalyze?: boolean;
}

export interface AnalysisCostEstimate {
  total_documents: number;
  estimated_cost_usd: number;
  estimated_time_seconds: number;
  within_budget: boolean;
  remaining_budget_usd: number;
}

// Document Detail View Types

export interface DocumentPreviewUrl {
  url: string;
  expires_at: string;
  file_type: string;
  filename: string;
}

export interface PersonEntity {
  name: string;
  role: string;
  confidence: number;
}

export interface EntitiesUpdate {
  people?: PersonEntity[];
  dates?: string[];
  locations?: string[];
  case_numbers?: string[];
  organizations?: string[];
}

export interface AnalysisUpdateRequest {
  summary?: string;
  classification?: string;
  key_points?: string[];
  entities?: EntitiesUpdate;
}

export interface AnnotationRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Annotation {
  id: string;
  page: number;
  rects: AnnotationRect[];
  color: string;
  text?: string;
  created_at: string;
}

export interface AnnotationCreate {
  page: number;
  rects: AnnotationRect[];
  color: string;
  text?: string;
}

// Edit state for document analysis
export interface AnalysisEditState {
  isEditing: boolean;
  isDirty: boolean;
  editedValues: Partial<AnalysisUpdateRequest>;
}
