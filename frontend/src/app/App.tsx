import { useState, useEffect, useCallback } from 'react'
import {
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
  useParams,
} from 'react-router-dom'
import { Sidebar, NavView } from '../components/Sidebar'
import { Header } from '../components/Header'
import { UploadIngestionView } from '../features/upload/UploadIngestionView'
import { ReviewWorkspaceView } from '../features/review/ReviewWorkspaceView'
import { EvaluationDashboardView } from '../features/metrics/EvaluationDashboardView'
import { SettingsView } from '../features/settings/SettingsView'
import {
  mockQueueDocuments,
  mockReviewDocuments,
} from '../data/mockIdpData'
import {
  QueueDocumentItem,
  IDPReviewDocument,
} from '../types/idp'
import { synthesizeReviewDocument } from '../lib/documentSynthesis'
import { getHealth, submitReview } from '../lib/api/documents'
import { useI18n } from '../lib/i18n'

export function App() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const location = useLocation()

  // App-level state for documents
  const [queueDocs, setQueueDocs] = useState<QueueDocumentItem[]>(mockQueueDocuments)
  const [reviewDocs, setReviewDocs] = useState<Record<string, IDPReviewDocument>>(
    mockReviewDocuments,
  )
  const [activeDocId, setActiveDocId] = useState<string>('doc-inv-001')
  const [searchQuery, setSearchQuery] = useState('')
  const [isBackendConnected, setIsBackendConnected] = useState(false)

  // Determine current active navigation view based on URL pathname
  const getCurrentView = (): NavView => {
    const path = location.pathname
    if (path.startsWith('/review')) return 'review'
    if (path.startsWith('/metrics')) return 'metrics'
    if (path.startsWith('/settings')) return 'settings'
    if (path.startsWith('/upload') || path.startsWith('/documents')) return 'upload'
    return 'upload'
  }

  const currentView = getCurrentView()

  // Polling / initial check for backend health
  useEffect(() => {
    const controller = new AbortController()
    getHealth(controller.signal)
      .then((res) => {
        setIsBackendConnected(res.status === 'ok')
      })
      .catch(() => {
        setIsBackendConnected(false)
      })
    return () => controller.abort()
  }, [])

  // Navigation handler from sidebar
  const handleSelectNavView = (view: NavView) => {
    switch (view) {
      case 'upload':
        navigate('/upload')
        break
      case 'review':
        navigate(`/review/${activeDocId}`)
        break
      case 'metrics':
        navigate('/metrics')
        break
      case 'settings':
        navigate('/settings')
        break
    }
  }

  // Ensure a document exists in reviewDocs without navigation
  const ensureDocExists = useCallback((docId: string) => {
    setReviewDocs((prev) => {
      if (prev[docId]) return prev
      const qDoc = queueDocs.find((d) => d.id === docId)
      const effectiveFileUrl =
        qDoc?.fileUrl || (qDoc?.backendId ? `/api/v1/documents/${qDoc.backendId}/file` : undefined)
      const synthesizedDoc = qDoc
        ? synthesizeReviewDocument(qDoc)
        : synthesizeReviewDocument({ id: docId, filename: `Document_${docId}.pdf` })
      if (effectiveFileUrl) {
        synthesizedDoc.fileUrl = effectiveFileUrl
      }
      if (qDoc?.backendId) {
        synthesizedDoc.backendId = qDoc.backendId
      }
      return { ...prev, [docId]: synthesizedDoc }
    })
  }, [queueDocs])

  // Handle opening review workspace from queue table or upload
  const handleOpenReview = (docId: string) => {
    ensureDocExists(docId)
    setActiveDocId(docId)
    navigate(`/review/${docId}`)
  }

  // Handle adding new document to queue
  const handleAddDocumentToQueue = (item: QueueDocumentItem) => {
    setQueueDocs((prev) => {
      const existingIdx = prev.findIndex((d) => d.id === item.id)
      if (existingIdx >= 0) {
        const copy = [...prev]
        copy[existingIdx] = item
        return copy
      }
      return [item, ...prev]
    })
  }

  // Handle updating document review fields or classification
  const handleUpdateReviewDoc = (updated: IDPReviewDocument) => {
    setReviewDocs((prev) => ({ ...prev, [updated.id]: updated }))
  }

  // Handle Document Approval
  const handleDocumentApproved = async (docId: string) => {
    const doc = reviewDocs[docId]
    if (doc?.backendId) {
      const payloadFields = doc.fields.map((f) => ({
        field_name: f.key,
        original_value: f.originalValue,
        corrected_value: f.correctedValue,
        original_confidence: f.confidence,
        is_modified: f.isModified,
      }))
      const res = await submitReview(doc.backendId, {
        expected_revision: doc.revision || 1,
        status: doc.fields.some((f) => f.isModified) ? 'CORRECTED' : 'APPROVED',
        reviewer_id: 'qa_reviewer',
        document_type: doc.classification.predictedType,
        fields: payloadFields,
      })
      if (res?.revision) {
        setReviewDocs((prev) => ({
          ...prev,
          [docId]: { ...prev[docId], revision: res.revision },
        }))
      }
    }
    // Update queue document status
    setQueueDocs((prev) =>
      prev.map((d) => (d.id === docId ? { ...d, status: 'COMPLETED' } : d)),
    )
    if (reviewDocs[docId]) {
      setReviewDocs((prev) => ({
        ...prev,
        [docId]: { ...prev[docId], status: 'COMPLETED' },
      }))
    }
  }

  // Handle Document Rejection
  const handleDocumentRejected = async (docId: string, reason?: string) => {
    const doc = reviewDocs[docId]
    if (doc?.backendId) {
      const res = await submitReview(doc.backendId, {
        expected_revision: doc.revision || 1,
        status: 'REJECTED',
        reviewer_id: 'qa_reviewer',
        document_type: doc.classification.predictedType,
        rejection_reason: reason || 'Document rejected by human reviewer',
      })
      if (res?.revision) {
        setReviewDocs((prev) => ({
          ...prev,
          [docId]: { ...prev[docId], revision: res.revision },
        }))
      }
    }
    setQueueDocs((prev) =>
      prev.map((d) => (d.id === docId ? { ...d, status: 'FAILED' } : d)),
    )
    if (reviewDocs[docId]) {
      setReviewDocs((prev) => ({
        ...prev,
        [docId]: { ...prev[docId], status: 'FAILED' },
      }))
    }
  }

  // Handle Saving Draft Corrections
  const handleSaveDraft = async (docId: string) => {
    const doc = reviewDocs[docId]
    if (doc?.backendId) {
      const payloadFields = doc.fields.map((f) => ({
        field_name: f.key,
        original_value: f.originalValue,
        corrected_value: f.correctedValue,
        original_confidence: f.confidence,
        is_modified: f.isModified,
      }))
      const res = await submitReview(doc.backendId, {
        expected_revision: doc.revision || 1,
        status: 'CORRECTED',
        reviewer_id: 'qa_reviewer',
        document_type: doc.classification.predictedType,
        fields: payloadFields,
        notes: 'Draft saved by human reviewer',
      })
      if (res?.revision) {
        setReviewDocs((prev) => ({
          ...prev,
          [docId]: { ...prev[docId], revision: res.revision },
        }))
      }
    }
  }

  // Title calculation for header
  const getHeaderTitle = () => {
    switch (currentView) {
      case 'upload':
        return t.uploadView.title
      case 'review':
        return t.reviewWorkspace.title
      case 'metrics':
        return t.metricsDashboard.title
      case 'settings':
        return t.settings.title
    }
  }

  const getHeaderSubtitle = () => {
    switch (currentView) {
      case 'upload':
        return t.uploadView.subtitle
      case 'review':
        return t.reviewWorkspace.subtitle
      case 'metrics':
        return t.metricsDashboard.subtitle
      case 'settings':
        return t.settings.subtitle
    }
  }

  const pendingCount = queueDocs.filter((d) => d.status === 'AWAITING_REVIEW').length

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 text-slate-800">
      {/* Persistent Left Sidebar */}
      <Sidebar
        currentView={currentView}
        onSelectView={handleSelectNavView}
        pendingReviewCount={pendingCount}
        isBackendConnected={isBackendConnected}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col h-full min-w-0 overflow-hidden">
        <Header
          title={getHeaderTitle()}
          subtitle={getHeaderSubtitle()}
          searchValue={searchQuery}
          onSearchChange={setSearchQuery}
          showSearch={currentView === 'upload'}
        />

        <main className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden">
          <Routes>
            <Route path="/" element={<Navigate to="/upload" replace />} />
            <Route path="/documents" element={<Navigate to="/upload" replace />} />
            <Route
              path="/upload"
              element={
                <UploadIngestionView
                  queueDocuments={queueDocs}
                  onOpenReview={handleOpenReview}
                  onAddDocumentToQueue={handleAddDocumentToQueue}
                />
              }
            />
            <Route
              path="/review"
              element={
                <ReviewWorkspaceWrapper
                  documents={reviewDocs}
                  onUpdateDocument={handleUpdateReviewDoc}
                  onDocumentApproved={handleDocumentApproved}
                  onDocumentRejected={handleDocumentRejected}
                  onSaveDraft={handleSaveDraft}
                  onEnsureDocExists={ensureDocExists}
                />
              }
            />
            <Route
              path="/review/:id"
              element={
                <ReviewWorkspaceWrapper
                  documents={reviewDocs}
                  onUpdateDocument={handleUpdateReviewDoc}
                  onDocumentApproved={handleDocumentApproved}
                  onDocumentRejected={handleDocumentRejected}
                  onSaveDraft={handleSaveDraft}
                  onEnsureDocExists={ensureDocExists}
                />
              }
            />
            <Route
              path="/documents/:id"
              element={
                <ReviewWorkspaceWrapper
                  documents={reviewDocs}
                  onUpdateDocument={handleUpdateReviewDoc}
                  onDocumentApproved={handleDocumentApproved}
                  onDocumentRejected={handleDocumentRejected}
                  onSaveDraft={handleSaveDraft}
                  onEnsureDocExists={ensureDocExists}
                />
              }
            />
            <Route path="/metrics" element={<EvaluationDashboardView />} />
            <Route path="/settings" element={<SettingsView />} />
            <Route path="*" element={<Navigate to="/upload" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

function ReviewWorkspaceWrapper({
  documents,
  onUpdateDocument,
  onDocumentApproved,
  onDocumentRejected,
  onSaveDraft,
  onEnsureDocExists,
}: {
  documents: Record<string, IDPReviewDocument>
  onUpdateDocument: (doc: IDPReviewDocument) => void
  onDocumentApproved: (docId: string) => Promise<void> | void
  onDocumentRejected: (docId: string, reason?: string) => Promise<void> | void
  onSaveDraft?: (docId: string) => Promise<void> | void
  onEnsureDocExists: (docId: string) => void
}) {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()

  useEffect(() => {
    if (id && !documents[id]) {
      onEnsureDocExists(id)
    }
  }, [id, documents, onEnsureDocExists])

  const effectiveId = id && documents[id] ? id : (Object.keys(documents)[0] || 'doc-inv-001')

  const handleSelectDocId = (newId: string) => {
    navigate(`/review/${newId}`)
  }

  return (
    <ReviewWorkspaceView
      documents={documents}
      activeDocId={effectiveId}
      onSelectDocId={handleSelectDocId}
      onUpdateDocument={onUpdateDocument}
      onDocumentApproved={onDocumentApproved}
      onDocumentRejected={onDocumentRejected}
      onSaveDraft={onSaveDraft}
    />
  )
}
