import { useState, type ChangeEvent } from 'react'
import {
  CheckCircle2,
  XCircle,
  RotateCcw,
  Sparkles,
  AlertTriangle,
  Save,
  Tag,
  ShieldCheck,
  Check,
} from 'lucide-react'
import {
  IDPReviewDocument,
  ExtractedFieldItem,
  DocumentType,
} from '../../types/idp'
import { useI18n } from '../../lib/i18n'

interface ExtractionCorrectionFormProps {
  document: IDPReviewDocument
  selectedFieldKey: string | null
  onSelectField: (fieldKey: string) => void
  onFieldChange: (fieldKey: string, newValue: string) => void
  onRevertField: (fieldKey: string) => void
  onApprove: () => void
  onReject: (reason?: string) => void
  onSaveDraft: () => void
  onReclassify: (newType: DocumentType) => void
  isStacked?: boolean
}

export function ExtractionCorrectionForm({
  document,
  selectedFieldKey,
  onSelectField,
  onFieldChange,
  onRevertField,
  onApprove,
  onReject,
  onSaveDraft,
  onReclassify,
  isStacked = false,
}: ExtractionCorrectionFormProps) {
  const { t, formatTemplate } = useI18n()
  const [rejectModalOpen, setRejectModalOpen] = useState(false)
  const [rejectReason, setRejectReason] = useState('')

  const classification = document.classification

  // Helpers for confidence badge
  const renderConfidenceBadge = (confidence: number) => {
    const pct = (confidence * 100).toFixed(1)
    if (confidence >= 0.9) {
      return (
        <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-800 border border-emerald-200">
          <CheckCircle2 className="h-3 w-3 text-emerald-600" />
          <span>{pct}%</span>
        </span>
      )
    }
    if (confidence >= 0.7) {
      return (
        <span className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-800 border border-amber-200">
          <AlertTriangle className="h-3 w-3 text-amber-600" />
          <span>{pct}%</span>
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-0.5 text-xs font-semibold text-rose-800 border border-rose-200 animate-pulse">
        <AlertTriangle className="h-3 w-3 text-rose-600" />
        <span>{pct}%</span>
      </span>
    )
  }

  // Count modified fields
  const modifiedCount = document.fields.filter(
    (f) => f.correctedValue !== f.originalValue,
  ).length

  return (
    <div
      className={`flex flex-col rounded-2xl border border-slate-200 bg-white shadow-xs ${
        isStacked ? 'w-full' : 'h-full overflow-hidden'
      }`}
    >
      {/* Top Header / Classification Banner */}
      <div className="border-b border-slate-200 bg-slate-50/70 p-3.5 sm:p-4 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-md bg-blue-600 text-white text-xs">
              <Tag className="h-3 w-3" />
            </span>
            <h2 className="text-xs font-bold text-slate-900 sm:text-sm">
              {t.reviewWorkspace.classificationCard}
            </h2>
          </div>

          {/* Classification Confidence */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="hidden sm:inline text-slate-500 text-[11px]">
              {t.reviewWorkspace.modelConfidence}:
            </span>
            {renderConfidenceBadge(classification.confidence)}
          </div>
        </div>

        {/* Classification Detail & Selector */}
        <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white p-2.5 shadow-xs">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              {t.reviewWorkspace.predictedType}
            </p>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold capitalize text-slate-900">
                {classification.predictedType === 'invoice'
                  ? t.classification.typeInvoice
                  : classification.predictedType === 'contract'
                    ? t.classification.typeContract
                    : t.classification.typeForm}
              </span>
              <span className="text-[10px] font-mono text-slate-400">
                ({classification.predictedType})
              </span>
            </div>
            <p className="text-[10px] text-slate-500">
              {formatTemplate(t.reviewWorkspace.modelDetails, {
                model: classification.modelIdentifier,
                threshold: `${Math.round(classification.threshold * 100)}%`,
              })}
            </p>
          </div>

          {/* Quick Override Dropdown */}
          <div className="flex items-center gap-2">
            <label htmlFor="reclassify-select" className="sr-only">
              {t.reviewWorkspace.reclassifyAria}
            </label>
            <select
              id="reclassify-select"
              value={classification.predictedType}
              onChange={(e) => onReclassify(e.target.value as DocumentType)}
              className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 focus:border-blue-500 focus:outline-none"
            >
              <option value="invoice">Invoice ({t.classification.typeInvoice})</option>
              <option value="contract">Contract ({t.classification.typeContract})</option>
              <option value="form">Form ({t.classification.typeForm})</option>
            </select>
          </div>
        </div>
      </div>

      {/* Fields List Header */}
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2 bg-white text-xs text-slate-500 shrink-0">
        <div>
          <span className="font-bold text-slate-900 text-xs sm:text-sm">
            {t.reviewWorkspace.fieldsHeading}
          </span>
          <span className="ml-1.5 text-slate-400 text-[11px]">({document.fields.length} fields)</span>
        </div>
        {modifiedCount > 0 ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700 border border-blue-200">
            <Sparkles className="h-3 w-3" />
            <span>{modifiedCount} modified</span>
          </span>
        ) : (
          <span className="text-slate-400 text-[11px]">Matching AI</span>
        )}
      </div>

      {/* Scrollable Fields Extraction Form */}
      <div
        className={
          isStacked
            ? 'p-4 grid grid-cols-1 md:grid-cols-2 gap-3.5 min-w-0'
            : 'flex-1 overflow-y-auto p-3.5 space-y-3 min-w-0'
        }
      >
        {document.fields.map((field: ExtractedFieldItem) => {
          const isSelected = selectedFieldKey === field.key
          const isModified = field.correctedValue !== field.originalValue

          return (
            <div
              key={field.key}
              onClick={() => onSelectField(field.key)}
              className={`rounded-xl border p-3 transition-all duration-150 ${
                isSelected
                  ? 'border-blue-500 bg-blue-50/20 shadow-sm ring-1 ring-blue-500/20'
                  : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/40'
              }`}
            >
              {/* Field Label & Confidence Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-900">
                    {field.labelEn}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    ({field.labelVi})
                  </span>
                  {isModified ? (
                    <span className="rounded bg-blue-100 px-1.5 py-0.2 text-[10px] font-semibold text-blue-800">
                      {t.reviewWorkspace.modifiedBadge}
                    </span>
                  ) : (
                    <span className="rounded bg-slate-100 px-1.5 py-0.2 text-[10px] font-medium text-slate-600">
                      {t.reviewWorkspace.unchangedBadge}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {renderConfidenceBadge(field.confidence)}
                  {isModified && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        onRevertField(field.key)
                      }}
                      title={t.reviewWorkspace.revertTooltip}
                      className="flex h-6 w-6 items-center justify-center rounded text-slate-400 hover:bg-slate-200 hover:text-slate-800"
                    >
                      <RotateCcw className="h-3 w-3" />
                    </button>
                  )}
                </div>
              </div>

              {/* Side-by-Side / Stacked Comparison: AI Prediction vs. Human Correction */}
              <div className="mt-3 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                {/* AI Extracted Value (Read-only, preserves ground truth) */}
                <div className="rounded-lg border border-slate-200/80 bg-slate-50/80 p-2.5">
                  <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    <span>{t.reviewWorkspace.originalAiBadge}</span>
                    <Sparkles className="h-3 w-3 text-indigo-400" />
                  </div>
                  <div className="mt-1 font-mono text-xs font-medium text-slate-800 break-all select-all">
                    {field.originalValue || <span className="italic text-slate-400">Not detected</span>}
                  </div>
                </div>

                {/* Human Correction Input */}
                <div className="relative">
                  <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                    <span>{t.reviewWorkspace.humanCorrectionCol}</span>
                    {isModified && (
                      <span className="text-[10px] text-blue-600 font-semibold">Diff detected</span>
                    )}
                  </div>
                  <input
                    type="text"
                    value={field.correctedValue}
                    onFocus={() => onSelectField(field.key)}
                    onChange={(e: ChangeEvent<HTMLInputElement>) =>
                      onFieldChange(field.key, e.target.value)
                    }
                    className={`w-full rounded-lg border py-1.5 px-3 text-xs font-mono transition-colors ${
                      isModified
                        ? 'border-blue-500 bg-white font-semibold text-blue-900 ring-2 ring-blue-500/10'
                        : 'border-slate-200 bg-white text-slate-900 focus:border-blue-500 focus:outline-none'
                    }`}
                  />
                </div>
              </div>

              {/* Low confidence callout if < 70% */}
              {field.confidence < 0.7 && (
                <div className="mt-2.5 flex items-center gap-1.5 rounded-md bg-rose-50 px-2.5 py-1 text-[11px] text-rose-700">
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                  <span>
                    {formatTemplate(t.reviewWorkspace.lowConfidenceWarning, {
                      conf: (field.confidence * 100).toFixed(1),
                    })}
                  </span>
                </div>
              )}
            </div>
          )
        })}

        {/* Audit Trail Disclaimer */}
        <div
          className={`rounded-xl border border-slate-100 bg-slate-50/50 p-3 text-[11px] text-slate-500 flex items-start gap-2 ${
            isStacked ? 'col-span-full' : ''
          }`}
        >
          <ShieldCheck className="h-4 w-4 text-slate-400 mt-0.5 shrink-0" />
          <span>{t.reviewWorkspace.auditTrail}</span>
        </div>
      </div>

      {/* Sticky Bottom Action Buttons Footer */}
      <div
        className={`border-t border-slate-200 bg-white p-4 ${
          isStacked
            ? 'sticky bottom-0 z-20 backdrop-blur-md bg-white/95 shadow-md rounded-b-2xl'
            : ''
        }`}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Reject button */}
          <button
            type="button"
            onClick={() => setRejectModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-100 transition-colors"
          >
            <XCircle className="h-4 w-4" />
            <span>{t.reviewWorkspace.actions.reject}</span>
          </button>

          {/* Right actions: Save Draft & Approve */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onSaveDraft}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <Save className="h-3.5 w-3.5 text-slate-500" />
              <span>{t.reviewWorkspace.actions.saveDraft}</span>
            </button>

            <button
              type="button"
              onClick={onApprove}
              className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-5 py-2 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 transition-all hover:shadow"
            >
              <Check className="h-4 w-4" />
              <span>{t.reviewWorkspace.actions.approve}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Reject Confirmation Modal */}
      {rejectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
            <div className="flex items-center gap-3 text-rose-600">
              <XCircle className="h-6 w-6" />
              <h3 className="text-base font-bold text-slate-900">
                {t.reviewWorkspace.actions.rejectConfirm}
              </h3>
            </div>
            <p className="mt-2 text-xs text-slate-600">
              {t.reviewWorkspace.actions.rejectPrompt}
            </p>
            <textarea
              rows={3}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g., Unreadable scan quality, fraudulent vendor invoice, missing mandatory signatures..."
              className="mt-3 w-full rounded-xl border border-slate-200 p-3 text-xs focus:border-rose-500 focus:outline-none"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setRejectModalOpen(false)}
                className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
              >
                {t.reviewWorkspace.actions.cancel}
              </button>
              <button
                type="button"
                onClick={() => {
                  setRejectModalOpen(false)
                  onReject(rejectReason)
                }}
                className="rounded-xl bg-rose-600 px-4 py-2 text-xs font-bold text-white hover:bg-rose-700"
              >
                {t.reviewWorkspace.actions.reject}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
