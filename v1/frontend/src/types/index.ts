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
  status: 'uploaded' | 'processing' | 'failed';
  document_metadata: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  document: Document;
  message: string;
}
