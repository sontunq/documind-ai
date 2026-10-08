import { useState } from 'react'
import {
  FileText,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Sparkles,
  Rows2,
  Columns2,
} from 'lucide-react'
import { DocumentViewer } from './DocumentViewer'
import { ExtractionCorrectionForm } from './ExtractionCorrectionForm'
import {
  IDPReviewDocument,
  DocumentType,
} from '../../types/idp'
import { useI18n } from '../../lib/i18n'

interface ReviewWorkspaceViewProps {
  documents: Record<string, IDPReviewDocument>
  activeDocId: string
  onSelectDocId: (id: string) => void
  onUpdateDocument: (doc: IDPReviewDocument) => void
  onDocumentApproved: (docId: string) => Promise<void> | void
  onDocumentRejected: (docId: string, reason?: string) => Promise<void> | void
  onSaveDraft?: (docId: string) => Promise<void> | void
}

export function ReviewWorkspaceView({
  documents,
  activeDocId,
  onSelectDocId,
  onUpdateDocument,
  onDocumentApproved,
  onDocumentRejected,
  onSaveDraft,
}: ReviewWorkspaceViewProps) {
  const { t } = useI18n()
  const [layoutMode, setLayoutMode] = useState<'stacked' | 'split'>('stacked')
  const [selectedFieldKey, setSelectedFieldKey] = useState<string | null>(null)
  const [toastMessage, setToastMessage] = useState<{
    text: string
    type: 'success' | 'danger' | 'info'
  } | null>(null)

  const docList = Object.values(documents)
  const currentDoc =
    documents[activeDocId] || docList[0] || null

  const currentIndex = docList.findIndex((d) => d.id === (currentDoc?.id || ''))

  const handlePrevDoc = () => {
    if (currentIndex > 0) {
      onSelectDocId(docList[currentIndex - 1].id)
      setSelectedFieldKey(null)
    }
  }

  const handleNextDoc = () => {
    if (currentIndex < docList.length - 1) {
      onSelectDocId(docList[currentIndex + 1].id)
      setSelectedFieldKey(null)
    }
  }

  const showToast = (text: string, type: 'success' | 'danger' | 'info') => {
    setToastMessage({ text, type })
    setTimeout(() => setToastMessage(null), 3500)
  }

  if (!currentDoc) {
    return (
      <div className="flex h-96 flex-col items-center justify-center p-8 text-center text-slate-500">
        <FileText className="h-12 w-12 text-slate-300 mb-3" />
        <h3 className="text-base font-semibold text-slate-700">No Document Selected</h3>
        <p className="text-xs text-slate-400 mt-1">Please select a document from the ingestion queue.</p>
      </div>
    )
  }

  const handleFieldChange = (fieldKey: string, newValue: string) => {
    const updatedFields = currentDoc.fields.map((f) => {
      if (f.key === fieldKey) {
        return {
          ...f,
          correctedValue: newValue,
          isModified: newValue !== f.originalValue,
        }
      }
      return f
    })
    onUpdateDocument({ ...currentDoc, fields: updatedFields })
  }

  const handleRevertField = (fieldKey: string) => {
    const updatedFields = currentDoc.fields.map((f) => {
      if (f.key === fieldKey) {
        return {
          ...f,
          correctedValue: f.originalValue,
          isModified: false,
        }
      }
      return f
    })
    onUpdateDocument({ ...currentDoc, fields: updatedFields })
    showToast(`Reverted "${fieldKey}" to original AI prediction`, 'info')
  }

  const handleReclassify = (newType: DocumentType) => {
    const updated = {
      ...currentDoc,
      classification: {
        ...currentDoc.classification,
        predictedType: newType,
      },
    }
    onUpdateDocument(updated)
    showToast(`Document re-classified as ${newType.toUpperCase()}`, 'info')
  }

  const handleApprove = async () => {
    try {
      await onDocumentApproved(currentDoc.id)
      showToast(
        t.reviewWorkspace.toasts.approved.replace('{id}', currentDoc.id),
        'success',
      )
      // Advance to next review document if available
      if (currentIndex < docList.length - 1) {
        setTimeout(() => {
          onSelectDocId(docList[currentIndex + 1].id)
        }, 700)
      }
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      if (errorMsg.includes('STALE_REVISION') || errorMsg.includes('Stale revision')) {
        showToast('Xung đột phiên bản: Tài liệu đã được người khác chỉnh sửa! Vui lòng tải lại trang.', 'danger')
      } else {
        showToast('Lỗi khi phê duyệt tài liệu: ' + errorMsg, 'danger')
      }
    }
  }

  const handleReject = async (reason?: string) => {
    try {
      await onDocumentRejected(currentDoc.id, reason)
      showToast(
        t.reviewWorkspace.toasts.rejected.replace('{id}', currentDoc.id),
        'danger',
      )
      if (currentIndex < docList.length - 1) {
        setTimeout(() => {
          onSelectDocId(docList[currentIndex + 1].id)
        }, 700)
      }
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      if (errorMsg.includes('STALE_REVISION') || errorMsg.includes('Stale revision')) {
        showToast('Xung đột phiên bản: Tài liệu đã được người khác chỉnh sửa! Vui lòng tải lại trang.', 'danger')
      } else {
        showToast('Lỗi khi từ chối tài liệu: ' + errorMsg, 'danger')
      }
    }
  }

  const handleSaveDraft = async () => {
    try {
      if (onSaveDraft) {
        await onSaveDraft(currentDoc.id)
      }
      showToast(t.reviewWorkspace.toasts.saved, 'info')
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      if (errorMsg.includes('STALE_REVISION') || errorMsg.includes('Stale revision')) {
        showToast('Xung đột phiên bản: Tài liệu đã được người khác chỉnh sửa! Vui lòng tải lại trang.', 'danger')
      } else {
        showToast('Lỗi khi lưu nháp: ' + errorMsg, 'danger')
      }
    }
  }

  return (
    <div
      className={`flex h-full w-full flex-col bg-slate-50 p-3 sm:p-4.5 min-w-0 ${
        layoutMode === 'stacked' ? 'overflow-y-auto' : 'overflow-hidden'
      }`}
    >
      {/* Toast Notification Alert */}
      {toastMessage && (
        <div
          role="status"
          className={`fixed top-20 right-8 z-50 flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-semibold shadow-lg backdrop-blur-md transition-all ${
            toastMessage.type === 'success'
              ? 'border border-emerald-200 bg-emerald-50/95 text-emerald-800'
              : toastMessage.type === 'danger'
                ? 'border border-rose-200 bg-rose-50/95 text-rose-800'
                : 'border border-blue-200 bg-blue-50/95 text-blue-800'
          }`}
        >
          {toastMessage.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0" />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Top Document Header Bar */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-2 shadow-xs min-w-0 shrink-0">
        {/* Left: Document Switcher Tabs & Title */}
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="flex items-center gap-1 border-r border-slate-200 pr-2.5">
            <button
              type="button"
              disabled={currentIndex <= 0}
              onClick={handlePrevDoc}
              title={t.reviewWorkspace.prevDoc}
              className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-xs font-mono font-medium text-slate-500 px-1">
              {currentIndex + 1}/{docList.length}
            </span>
            <button
              type="button"
              disabled={currentIndex >= docList.length - 1}
              onClick={handleNextDoc}
              title={t.reviewWorkspace.nextDoc}
              className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* Active Document Selector */}
          <div className="flex items-center gap-2 min-w-0">
            <FileText className="h-4 w-4 text-blue-600 shrink-0" />
            <select
              value={currentDoc.id}
              onChange={(e) => {
                onSelectDocId(e.target.value)
                setSelectedFieldKey(null)
              }}
              className="max-w-xs sm:max-w-sm truncate rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-800 hover:bg-slate-100 focus:border-blue-500 focus:outline-none"
            >
              {docList.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename} ({doc.classification.predictedType.toUpperCase()})
                </option>
              ))}
            </select>
          </div>

          {/* Status badge */}
          <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-800 border border-amber-200/80">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-ping" />
            <span>{t.uploadView.pipelineStage.awaiting_review}</span>
          </span>
        </div>

        {/* Right Info & Layout Mode Toggle */}
        <div className="flex items-center gap-2.5 text-xs text-slate-500">
          <div className="hidden lg:flex items-center gap-1.5">
            <Clock className="h-3 w-3 text-slate-400" />
            <span>Uploaded {new Date(currentDoc.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          </div>

          <div className="hidden sm:flex items-center gap-1 rounded-md bg-blue-50 px-2 py-0.5 text-blue-700 font-mono text-[11px] font-semibold border border-blue-200/60">
            <Sparkles className="h-3 w-3" />
            <span>{currentDoc.fields.length} Fields</span>
          </div>

          {/* Layout Mode Segmented Control: Stacked (Top-Bottom) vs Split (Side-by-Side) */}
          <div className="flex items-center rounded-lg border border-slate-200 bg-slate-100 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setLayoutMode('stacked')}
              title={t.reviewWorkspace.layoutStacked}
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold transition-all ${
                layoutMode === 'stacked'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Rows2 className="h-3.5 w-3.5" />
              <span className="hidden md:inline">{t.reviewWorkspace.layoutStacked}</span>
            </button>
            <button
              type="button"
              onClick={() => setLayoutMode('split')}
              title={t.reviewWorkspace.layoutSplit}
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold transition-all ${
                layoutMode === 'split'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Columns2 className="h-3.5 w-3.5" />
              <span className="hidden md:inline">{t.reviewWorkspace.layoutSplit}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Review Workspace Area */}
      {layoutMode === 'stacked' ? (
        /* STACKED LAYOUT (1 Trên - 1 Dưới): Document Viewer on Top, Form below */
        <div className="flex flex-col space-y-4 min-w-0 pb-8">
          {/* TOP PANE: Document Visualizer with generous height and full width */}
          <div className="w-full h-[620px] sm:h-[680px] shrink-0 min-w-0">
            <DocumentViewer
              document={currentDoc}
              selectedFieldKey={selectedFieldKey}
              onSelectField={(key) => setSelectedFieldKey(key)}
            />
          </div>

          {/* BOTTOM PANE: Full-Width Structured Extraction & Human Correction Form */}
          <div className="w-full min-w-0">
            <ExtractionCorrectionForm
              document={currentDoc}
              selectedFieldKey={selectedFieldKey}
              onSelectField={(key) => setSelectedFieldKey(key)}
              onFieldChange={handleFieldChange}
              onRevertField={handleRevertField}
              onApprove={handleApprove}
              onReject={handleReject}
              onSaveDraft={handleSaveDraft}
              onReclassify={handleReclassify}
              isStacked={true}
            />
          </div>
        </div>
      ) : (
        /* SPLIT SCREEN LAYOUT: Side-by-side 2 halves */
        <div className="grid flex-1 grid-cols-1 gap-3.5 lg:grid-cols-12 overflow-hidden min-h-0 min-w-0">
          {/* LEFT PANE: Document Visualizer with Bounding Boxes */}
          <div className="lg:col-span-7 h-full overflow-hidden flex flex-col min-w-0">
            <DocumentViewer
              document={currentDoc}
              selectedFieldKey={selectedFieldKey}
              onSelectField={(key) => setSelectedFieldKey(key)}
            />
          </div>

          {/* RIGHT PANE: Structured Extraction & Human Correction Form */}
          <div className="lg:col-span-5 h-full overflow-hidden flex flex-col min-w-0">
            <ExtractionCorrectionForm
              document={currentDoc}
              selectedFieldKey={selectedFieldKey}
              onSelectField={(key) => setSelectedFieldKey(key)}
              onFieldChange={handleFieldChange}
              onRevertField={handleRevertField}
              onApprove={handleApprove}
              onReject={handleReject}
              onSaveDraft={handleSaveDraft}
              onReclassify={handleReclassify}
              isStacked={false}
            />
          </div>
        </div>
      )}
    </div>
  )
}
