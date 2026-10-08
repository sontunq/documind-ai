import { useState, useRef, type DragEvent, type ChangeEvent } from 'react'
import {
  UploadCloud,
  FileText,
  FileCheck2,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  Search,
  Filter,
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import { QueueDocumentItem, ProcessingStatus } from '../../types/idp'
import { useI18n } from '../../lib/i18n'
import { uploadDocument } from '../../lib/api/documents'

interface UploadIngestionViewProps {
  queueDocuments: QueueDocumentItem[]
  onOpenReview: (docId: string) => void
  onAddDocumentToQueue: (item: QueueDocumentItem) => void
}

export function UploadIngestionView({
  queueDocuments,
  onOpenReview,
  onAddDocumentToQueue,
}: UploadIngestionViewProps) {
  const { t } = useI18n()
  const [isDragging, setIsDragging] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [currentStage, setCurrentStage] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Drag & drop handlers
  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processSelectedFile(e.dataTransfer.files[0])
    }
  }

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processSelectedFile(e.target.files[0])
      e.target.value = ''
    }
  }

  // Simulated & Live ingestion progression
  const processSelectedFile = async (file: File) => {
    setErrorMessage(null)
    const validExtensions = /\.(pdf|png|jpe?g)$/i
    if (!validExtensions.test(file.name)) {
      setErrorMessage(t.uploadPage.errFormat)
      return
    }

    if (file.size > 25 * 1024 * 1024) {
      setErrorMessage('File size exceeds the 25 MB limit.')
      return
    }

    const fileUrl = URL.createObjectURL(file)
    const docId = `doc-usr-${Date.now().toString().slice(-4)}`
    const isPdf = file.name.toLowerCase().endsWith('.pdf')
    const lowerName = file.name.toLowerCase()
    const predictedType = lowerName.includes('ctr') || lowerName.includes('contract') || lowerName.includes('agreement')
      ? 'contract'
      : lowerName.includes('form') || lowerName.includes('w9') || lowerName.includes('employee') || lowerName.includes('application')
        ? 'form'
        : 'invoice'

    const newDoc: QueueDocumentItem = {
      id: docId,
      filename: file.name,
      mediaType: file.type || (isPdf ? 'application/pdf' : 'image/png'),
      sizeBytes: file.size,
      status: 'UPLOADING',
      predictedType,
      confidence: 0.94,
      uploadedAt: new Date().toISOString(),
      processingTimeMs: 0,
      pageCount: isPdf ? 2 : 1,
      fileUrl,
    }

    onAddDocumentToQueue(newDoc)
    setUploadProgress(15)
    setCurrentStage(t.uploadView.pipelineStage.uploading)

    // Attempt live backend upload in background if server available
    try {
      uploadDocument(file)
        .then((backendDoc) => {
          newDoc.backendId = backendDoc.id
          onAddDocumentToQueue({ ...newDoc })
        })
        .catch(() => {
          // Fallback to local demo workflow
        })
    } catch {
      // Ignored for frontend demo fidelity
    }

    // Step 2: Extracting OCR
    setTimeout(() => {
      setUploadProgress(45)
      setCurrentStage(t.uploadView.pipelineStage.extracting_ocr)
      newDoc.status = 'EXTRACTING_OCR'
      onAddDocumentToQueue({ ...newDoc })
    }, 900)

    // Step 3: Classifying
    setTimeout(() => {
      setUploadProgress(75)
      setCurrentStage(t.uploadView.pipelineStage.classifying)
      newDoc.status = 'CLASSIFYING'
      onAddDocumentToQueue({ ...newDoc })
    }, 1800)

    // Step 4: Finished Ingestion -> Ready for Review
    setTimeout(() => {
      setUploadProgress(100)
      setCurrentStage(t.uploadView.pipelineStage.awaiting_review)
      newDoc.status = 'AWAITING_REVIEW'
      newDoc.processingTimeMs = 1420
      onAddDocumentToQueue({ ...newDoc })

      setTimeout(() => {
        setUploadProgress(null)
        setCurrentStage(null)
      }, 1200)
    }, 2800)
  }

  // Filter documents
  const filteredDocs = queueDocuments.filter((doc) => {
    const matchesSearch =
      doc.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.predictedType && doc.predictedType.toLowerCase().includes(searchQuery.toLowerCase()))

    if (!matchesSearch) return false

    if (filterStatus === 'ALL') return true
    if (filterStatus === 'REVIEW') return doc.status === 'AWAITING_REVIEW'
    if (filterStatus === 'PROCESSING')
      return (
        doc.status === 'UPLOADING' ||
        doc.status === 'EXTRACTING_OCR' ||
        doc.status === 'CLASSIFYING'
      )
    if (filterStatus === 'COMPLETED') return doc.status === 'COMPLETED'
    return true
  })

  // Format helpers
  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  const formatTime = (isoString: string) => {
    const d = new Date(isoString)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  // Helper for status badges
  const renderStatusBadge = (status: ProcessingStatus) => {
    switch (status) {
      case 'UPLOADING':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 border border-blue-200/60">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>{t.uploadView.pipelineStage.uploading}</span>
          </span>
        )
      case 'EXTRACTING_OCR':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-50 px-2.5 py-1 text-xs font-medium text-purple-700 border border-purple-200/60">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>{t.uploadView.pipelineStage.extracting_ocr}</span>
          </span>
        )
      case 'CLASSIFYING':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700 border border-indigo-200/60">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>{t.uploadView.pipelineStage.classifying}</span>
          </span>
        )
      case 'AWAITING_REVIEW':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800 border border-amber-200/80">
            <AlertTriangle className="h-3 w-3 text-amber-600" />
            <span>{t.uploadView.pipelineStage.awaiting_review}</span>
          </span>
        )
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800 border border-emerald-200/60">
            <CheckCircle2 className="h-3 w-3 text-emerald-600" />
            <span>{t.uploadView.pipelineStage.completed}</span>
          </span>
        )
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-700 border border-rose-200/60">
            <XCircle className="h-3 w-3 text-rose-600" />
            <span>{t.uploadView.pipelineStage.failed}</span>
          </span>
        )
      default:
        return null
    }
  }

  // Document type badge
  const renderTypeBadge = (type?: string) => {
    if (!type) return <span className="text-slate-400 italic text-xs">-</span>
    const map: Record<string, { label: string; color: string }> = {
      invoice: {
        label: t.classification.typeInvoice,
        color: 'bg-sky-50 text-sky-800 border-sky-200/60',
      },
      contract: {
        label: t.classification.typeContract,
        color: 'bg-indigo-50 text-indigo-800 border-indigo-200/60',
      },
      form: {
        label: t.classification.typeForm,
        color: 'bg-emerald-50 text-emerald-800 border-emerald-200/60',
      },
    }
    const item = map[type.toLowerCase()] || {
      label: type.toUpperCase(),
      color: 'bg-slate-50 text-slate-700 border-slate-200',
    }
    return (
      <span
        className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${item.color}`}
      >
        {item.label}
      </span>
    )
  }

  // Quick stats summary
  const pendingCount = queueDocuments.filter((d) => d.status === 'AWAITING_REVIEW').length
  const processingCount = queueDocuments.filter((d) =>
    ['UPLOADING', 'EXTRACTING_OCR', 'CLASSIFYING'].includes(d.status),
  ).length
  const completedCount = queueDocuments.filter((d) => d.status === 'COMPLETED').length

  return (
    <div className="space-y-5 p-4 sm:p-6 max-w-full min-w-0">
      {/* Top Banner / Ingestion Stats */}
      <div className="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Total Ingested</span>
            <FileText className="h-4 w-4 text-slate-400" />
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-xl font-bold text-slate-900 sm:text-2xl">{queueDocuments.length}</span>
            <span className="text-[11px] text-slate-500">documents</span>
          </div>
        </div>

        <div className="rounded-xl border border-amber-200/80 bg-amber-50/40 p-4 shadow-xs">
          <div className="flex items-center justify-between text-amber-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider">{t.sidebar.pendingReview}</span>
            <AlertTriangle className="h-4 w-4 text-amber-600" />
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-xl font-bold text-amber-900 sm:text-2xl">{pendingCount}</span>
            <span className="text-[11px] text-amber-700 font-medium truncate">requires verification</span>
          </div>
        </div>

        <div className="rounded-xl border border-blue-200/80 bg-blue-50/40 p-4 shadow-xs">
          <div className="flex items-center justify-between text-blue-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider">In Pipeline</span>
            <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-xl font-bold text-blue-900 sm:text-2xl">{processingCount}</span>
            <span className="text-[11px] text-blue-700 font-medium truncate">OCR & Extraction</span>
          </div>
        </div>

        <div className="rounded-xl border border-emerald-200/80 bg-emerald-50/40 p-4 shadow-xs">
          <div className="flex items-center justify-between text-emerald-800">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Straight-Through (STP)</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="mt-1.5 flex items-baseline gap-2">
            <span className="text-xl font-bold text-emerald-900 sm:text-2xl">{completedCount}</span>
            <span className="text-[11px] text-emerald-700 font-medium truncate">auto-approved</span>
          </div>
        </div>
      </div>

      {/* Large Drag-and-Drop Ingestion Zone */}
      <section aria-labelledby="upload-zone-heading">
        <h2 id="upload-zone-heading" className="sr-only">
          {t.uploadView.title}
        </h2>
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`group relative flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 sm:p-8 text-center transition-all duration-200 ${
            isDragging
              ? 'border-blue-600 bg-blue-50/70 scale-[1.005]'
              : 'border-slate-300 bg-white hover:border-blue-500 hover:bg-slate-50/60 shadow-xs'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={handleFileInputChange}
            className="hidden"
          />

          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600 group-hover:scale-105 group-hover:bg-blue-100 transition-all">
            <UploadCloud className="h-6 w-6" />
          </div>

          <h3 className="mt-4 text-base font-semibold text-slate-800 sm:text-lg">
            {isDragging ? t.uploadView.dropActive : t.uploadView.dropTitle}
          </h3>

          <p className="mt-1 text-xs text-slate-500 sm:text-sm">
            {t.uploadView.dropSubtitle}
          </p>

          <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
            <span className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-[11px] font-medium text-slate-600">
              PDF (Multi-page)
            </span>
            <span className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-[11px] font-medium text-slate-600">
              PNG / JPG (Scans)
            </span>
            <span className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-[11px] font-medium text-slate-600">
              Max 25 MB
            </span>
          </div>

          <button
            type="button"
            className="mt-5 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 transition-colors"
          >
            <Sparkles className="h-4 w-4" />
            <span>{t.uploadView.browseBtn}</span>
          </button>

          {/* Active upload progress bar */}
          {uploadProgress !== null && (
            <div className="mt-6 w-full max-w-md rounded-xl border border-blue-200 bg-blue-50/90 p-4 text-left">
              <div className="flex items-center justify-between text-xs font-semibold text-blue-900">
                <span className="flex items-center gap-2">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {currentStage}
                </span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-blue-200/60">
                <div
                  className="h-full bg-blue-600 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {errorMessage && (
            <div className="mt-4 flex items-center gap-2 rounded-lg bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700 border border-rose-200">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}
        </div>
      </section>

      {/* Processing Queue Table */}
      <section className="rounded-2xl border border-slate-200 bg-white shadow-xs" aria-labelledby="queue-table-heading">
        <div className="flex flex-col gap-4 border-b border-slate-200/80 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 id="queue-table-heading" className="text-base font-bold text-slate-900">
              {t.uploadView.recentQueueTitle}
            </h2>
            <p className="text-xs text-slate-500">
              {t.uploadView.recentQueueSubtitle}
            </p>
          </div>

          {/* Search & Filter pills */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="relative w-48 sm:w-56">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t.uploadView.searchPlaceholder}
                className="w-full rounded-lg border border-slate-200 bg-slate-50/80 py-1.5 pl-8 pr-3 text-xs text-slate-800 placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none"
              />
            </div>

            <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setFilterStatus('ALL')}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                  filterStatus === 'ALL'
                    ? 'bg-white font-semibold text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {t.uploadView.filterAll}
              </button>
              <button
                type="button"
                onClick={() => setFilterStatus('REVIEW')}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                  filterStatus === 'REVIEW'
                    ? 'bg-white font-semibold text-amber-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {t.uploadView.filterReview}
              </button>
              <button
                type="button"
                onClick={() => setFilterStatus('PROCESSING')}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                  filterStatus === 'PROCESSING'
                    ? 'bg-white font-semibold text-blue-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {t.uploadView.filterProcessing}
              </button>
              <button
                type="button"
                onClick={() => setFilterStatus('COMPLETED')}
                className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                  filterStatus === 'COMPLETED'
                    ? 'bg-white font-semibold text-emerald-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {t.uploadView.filterCompleted}
              </button>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th scope="col" className="px-5 py-3.5">
                  {t.uploadView.colDocument}
                </th>
                <th scope="col" className="px-4 py-3.5">
                  {t.uploadView.colType}
                </th>
                <th scope="col" className="px-4 py-3.5">
                  {t.uploadView.colStatus}
                </th>
                <th scope="col" className="px-4 py-3.5">
                  {t.uploadView.colConfidence}
                </th>
                <th scope="col" className="px-4 py-3.5">
                  {t.uploadView.colSize}
                </th>
                <th scope="col" className="px-4 py-3.5">
                  {t.uploadView.colUploaded}
                </th>
                <th scope="col" className="px-5 py-3.5 text-right">
                  {t.uploadView.colActions}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredDocs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <Filter className="mx-auto mb-2 h-6 w-6 text-slate-300" />
                    No documents found matching the filter criteria.
                  </td>
                </tr>
              ) : (
                filteredDocs.map((doc) => (
                  <tr
                    key={doc.id}
                    onClick={() => {
                      if (doc.status === 'AWAITING_REVIEW' || doc.status === 'COMPLETED') {
                        onOpenReview(doc.id)
                      }
                    }}
                    className={`cursor-pointer transition-colors ${
                      doc.status === 'AWAITING_REVIEW' ? 'hover:bg-amber-50/30' : 'hover:bg-slate-50'
                    }`}
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600 shrink-0">
                          <FileText className="h-4.5 w-4.5" />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate font-medium text-slate-900 hover:text-blue-600 transition-colors">
                            {doc.filename}
                          </p>
                          <p className="text-[11px] text-slate-400">
                            {doc.id} · {doc.pageCount} page(s)
                          </p>
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-4 whitespace-nowrap">
                      {renderTypeBadge(doc.predictedType)}
                    </td>

                    <td className="px-4 py-4 whitespace-nowrap">
                      {renderStatusBadge(doc.status)}
                    </td>

                    <td className="px-4 py-4 whitespace-nowrap">
                      {doc.confidence !== undefined ? (
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-12 overflow-hidden rounded-full bg-slate-100">
                            <div
                              className={`h-full ${
                                doc.confidence >= 0.9
                                  ? 'bg-emerald-500'
                                  : doc.confidence >= 0.7
                                    ? 'bg-amber-500'
                                    : 'bg-rose-500'
                              }`}
                              style={{ width: `${Math.round(doc.confidence * 100)}%` }}
                            />
                          </div>
                          <span
                            className={`font-mono text-xs font-semibold ${
                              doc.confidence >= 0.9
                                ? 'text-emerald-700'
                                : doc.confidence >= 0.7
                                  ? 'text-amber-700'
                                  : 'text-rose-700'
                            }`}
                          >
                            {(doc.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-400">-</span>
                      )}
                    </td>

                    <td className="px-4 py-4 whitespace-nowrap text-slate-500">
                      {formatBytes(doc.sizeBytes)}
                    </td>

                    <td className="px-4 py-4 whitespace-nowrap text-slate-500">
                      <div className="flex items-center gap-1.5">
                        <Clock className="h-3 w-3 text-slate-400" />
                        <span>{formatTime(doc.uploadedAt)}</span>
                      </div>
                    </td>

                    <td className="px-5 py-4 whitespace-nowrap text-right">
                      {doc.status === 'AWAITING_REVIEW' ? (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            onOpenReview(doc.id)
                          }}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-amber-700 transition-colors"
                        >
                          <span>{t.uploadView.actionReview}</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </button>
                      ) : doc.status === 'COMPLETED' ? (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            onOpenReview(doc.id)
                          }}
                          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                        >
                          <FileCheck2 className="h-3.5 w-3.5 text-emerald-600" />
                          <span>View Review</span>
                        </button>
                      ) : (
                        <span className="text-slate-400 text-xs italic">Processing…</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
