export type DocumentType = 'invoice' | 'contract' | 'form'

export type ProcessingStatus =
  | 'UPLOADING'
  | 'EXTRACTING_OCR'
  | 'CLASSIFYING'
  | 'AWAITING_REVIEW'
  | 'COMPLETED'
  | 'FAILED'

export interface BoundingBox {
  id: string
  fieldKey: string
  label: string
  // Normalized coordinates (0.0 - 1.0) relative to page
  x: number
  y: number
  width: number
  height: number
  confidence: number
  text: string
  page: number
}

export interface ExtractedFieldItem {
  key: string
  labelEn: string
  labelVi: string
  originalValue: string
  correctedValue: string
  confidence: number
  boundingBoxId?: string
  isModified: boolean
  category: 'header' | 'parties' | 'financials' | 'dates' | 'general'
}

export interface DocumentClassificationInfo {
  predictedType: DocumentType
  confidence: number
  threshold: number
  modelIdentifier: string
  modelVersion: string
  scores: Record<DocumentType, number>
}

export interface IDPReviewDocument {
  id: string
  filename: string
  mediaType: string
  sizeBytes: number
  createdAt: string
  status: ProcessingStatus
  classification: DocumentClassificationInfo
  fields: ExtractedFieldItem[]
  boundingBoxes: BoundingBox[]
  pageCount: number
  currentPage: number
  fileUrl?: string
  backendId?: string
  revision?: number
  reviewHistory?: {
    action: 'approved' | 'rejected' | 'modified'
    timestamp: string
    reviewer: string
    note?: string
  }[]
}

export interface QueueDocumentItem {
  id: string
  filename: string
  mediaType: string
  sizeBytes: number
  status: ProcessingStatus
  predictedType?: DocumentType
  confidence?: number
  uploadedAt: string
  processingTimeMs?: number
  pageCount: number
  fileUrl?: string
  backendId?: string
  revision?: number
}

export interface MetricKPI {
  id: string
  titleEn: string
  titleVi: string
  value: string | number
  unit?: string
  baseline: string | number
  delta: string
  isPositive: boolean
  descriptionEn: string
  descriptionVi: string
}

export interface ModelHistoryDataPoint {
  iteration: string
  date: string
  precision: number
  recall: number
  f1Score: number
  cer: number
  wer: number
}

export interface FieldAccuracyDataPoint {
  fieldName: string
  precision: number
  recall: number
  f1Score: number
  sampleCount: number
}

export interface ConfusionMatrixItem {
  actual: string
  predictedInvoice: number
  predictedContract: number
  predictedForm: number
}

export interface QualityErrorBreakdown {
  qualityCategory: string
  avgCer: number
  avgWer: number
  docCount: number
}
