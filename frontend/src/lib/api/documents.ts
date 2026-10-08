import { request } from './client'

// Aligned with backend/app/api/schemas.py and the canonical domain enum.
export interface DocumentMetadata {
  id: string
  original_filename: string
  media_type: string
  size_bytes: number
  checksum: string
  status: 'UPLOADED' | 'QUEUED' | 'PROCESSING' | 'NEEDS_REVIEW' | 'COMPLETED' | 'FAILED'
  page_count: number | null
  revision: number
  created_at: string
  updated_at: string
}

export const isProcessing = (document: { status: DocumentMetadata['status'] }) =>
  document.status === 'QUEUED' || document.status === 'PROCESSING'
export const hasProcessingDocuments = (documents: DocumentMetadata[]) =>
  documents.some(isProcessing)

export const getHealth = (signal: AbortSignal) =>
  request<{ status: 'ok' }>('/health', { signal })
export const listDocuments = (
  limit: number,
  offset: number,
  signal: AbortSignal,
) =>
  request<DocumentMetadata[]>(
    `/api/v1/documents?limit=${limit}&offset=${offset}`,
    { signal },
  )
export const getDocument = (id: string, signal: AbortSignal) =>
  request<DocumentMetadata>(`/api/v1/documents/${encodeURIComponent(id)}`, {
    signal,
  })
export function uploadDocument(file: File): Promise<DocumentMetadata> {
  const body = new FormData()
  body.append('file', file)
  return request('/api/v1/documents', { method: 'POST', body })
}

export type DocumentType = 'invoice' | 'contract' | 'form'
export interface ClassificationResult {
  document_id: string
  run_id: string
  predicted_type: DocumentType
  scores: Record<DocumentType, number>
  confidence: number
  threshold: number
  needs_review: boolean
  model_identifier: string
  model_version: string
  dataset_version: string
  config_version: string
  created_at: string
}

export interface ExtractedField {
  name: string
  value: string | number | boolean | null
  raw_value: string | null
  confidence: number
  page: number | null
  box: {
    x: number
    y: number
    width: number
    height: number
  } | null
  is_derived: boolean
}

export interface InvoiceExtraction {
  invoice_number?: ExtractedField | null
  issue_date?: ExtractedField | null
  due_date?: ExtractedField | null
  supplier?: ExtractedField | null
  customer?: ExtractedField | null
  subtotal?: ExtractedField | null
  tax?: ExtractedField | null
  total?: ExtractedField | null
  currency?: ExtractedField | null
}

export interface ContractExtraction {
  contract_number?: ExtractedField | null
  title?: ExtractedField | null
  party_a?: ExtractedField | null
  party_b?: ExtractedField | null
  effective_date?: ExtractedField | null
  expiry_date?: ExtractedField | null
  contract_value?: ExtractedField | null
  governing_law?: ExtractedField | null
}

export interface FormExtraction {
  form_title?: ExtractedField | null
  fields: ExtractedField[]
}

export interface ExtractionResult {
  document_id: string
  run_id: string
  document_type: DocumentType
  invoice?: InvoiceExtraction | null
  contract?: ContractExtraction | null
  form?: FormExtraction | null
  extractor_name: string
  extractor_version: string
  created_at: string
}

// Fields consumed by this view; the result endpoint also supplies OCR payloads.
export interface ProcessingRunSummary {
  id: string
  status: DocumentMetadata['status']
  error_code: string | null
  error_message: string | null
  classification: ClassificationResult | null
  classification_seconds: number | null
  extraction: ExtractionResult | null
  extraction_seconds: number | null
}
export interface DocumentResults {
  document_id: string
  status: DocumentMetadata['status']
  latest_run: ProcessingRunSummary | null
  current_run: ProcessingRunSummary | null
}
export const getDocumentResults = (id: string, signal: AbortSignal) =>
  request<DocumentResults>(`/api/v1/documents/${encodeURIComponent(id)}/results`, { signal })

export type ReviewStatus = 'APPROVED' | 'CORRECTED' | 'REJECTED'

export interface ReviewedFieldPayload {
  field_name: string
  original_value?: string | number | boolean | null
  corrected_value?: string | number | boolean | null
  original_confidence?: number | null
  is_modified: boolean
}

export interface SubmitReviewPayload {
  expected_revision: number
  status: ReviewStatus
  reviewer_id?: string
  document_type?: DocumentType | null
  fields?: ReviewedFieldPayload[]
  rejection_reason?: string | null
  notes?: string | null
}

export interface ReviewResponse {
  id: string
  document_id: string
  revision: number
  status: ReviewStatus
  reviewer_id: string
  document_type?: DocumentType | null
  fields: ReviewedFieldPayload[]
  rejection_reason?: string | null
  notes?: string | null
  created_at: string
}

export function submitReview(
  documentId: string,
  payload: SubmitReviewPayload,
): Promise<ReviewResponse> {
  return request(`/api/v1/documents/${encodeURIComponent(documentId)}/review`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function getLatestReview(
  documentId: string,
  signal?: AbortSignal,
): Promise<ReviewResponse> {
  return request(`/api/v1/documents/${encodeURIComponent(documentId)}/review`, {
    signal,
  })
}

export function getReviewHistory(
  documentId: string,
  signal?: AbortSignal,
): Promise<ReviewResponse[]> {
  return request(`/api/v1/documents/${encodeURIComponent(documentId)}/reviews`, {
    signal,
  })
}

export function getPageImageUrl(documentId: string, pageNumber: number = 1): string {
  return `/api/v1/documents/${encodeURIComponent(documentId)}/pages/${pageNumber}/image`
}
