import { useState, useEffect, useRef } from 'react'
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Eye,
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  FileText,
  Layers,
  ExternalLink,
} from 'lucide-react'
import { BoundingBox, IDPReviewDocument } from '../../types/idp'
import { useI18n } from '../../lib/i18n'

interface DocumentViewerProps {
  document: IDPReviewDocument
  selectedFieldKey: string | null
  onSelectField: (fieldKey: string) => void
}

export function DocumentViewer({
  document,
  selectedFieldKey,
  onSelectField,
}: DocumentViewerProps) {
  const { t } = useI18n()
  const [zoom, setZoom] = useState<number>(100)
  const [showBoxes, setShowBoxes] = useState<boolean>(true)
  const [showLabels, setShowLabels] = useState<boolean>(true)
  const [filterLowConfOnly, setFilterLowConfOnly] = useState<boolean>(false)
  const [hoveredBoxId, setHoveredBoxId] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'original' | 'ocr'>('original')
  const containerRef = useRef<HTMLDivElement>(null)

  const isPdf =
    document.mediaType === 'application/pdf' ||
    document.filename.toLowerCase().endsWith('.pdf')
  const isImage =
    document.mediaType?.startsWith('image/') ||
    /\.(png|jpe?g|webp)$/i.test(document.filename)
  const lowerName = document.filename.toLowerCase()
  const isEmployeeForm =
    lowerName.includes('employee') ||
    lowerName.includes('hr') ||
    lowerName.includes('staff') ||
    lowerName.includes('personnel') ||
    lowerName.includes('thong-tin') ||
    lowerName.includes('nv') ||
    document.id === 'doc-frm-004'

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 10, 160))
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 10, 50))
  const handleResetZoom = () => setZoom(100)
  const handleFitWidth = () => {
    if (containerRef.current) {
      const available = containerRef.current.clientWidth - 32
      if (available > 0) {
        const target = Math.min(130, Math.max(50, Math.round((available / 500) * 100)))
        setZoom(target)
      }
    }
  }
  const handleFitPage = () => {
    if (containerRef.current) {
      const availableW = containerRef.current.clientWidth - 32
      const availableH = containerRef.current.clientHeight - 32
      if (availableW > 0 && availableH > 0) {
        const zoomW = (availableW / 500) * 100
        const zoomH = (availableH / 750) * 100
        const target = Math.min(zoomW, zoomH)
        setZoom(Math.min(130, Math.max(40, Math.round(target))))
      }
    }
  }

  // Auto fit page on mount or document change
  useEffect(() => {
    const timer = setTimeout(() => {
      handleFitPage()
    }, 60)
    return () => clearTimeout(timer)
  }, [document.id])

  // Filter boxes if requested
  const visibleBoxes = document.boundingBoxes.filter((box) => {
    if (box.page !== document.currentPage) return false
    if (filterLowConfOnly) return box.confidence < 0.9
    return true
  })

  // Color-coding based on confidence score
  const getBoxColorClasses = (confidence: number, isSelected: boolean) => {
    if (isSelected) {
      return {
        border: 'border-blue-600 ring-2 ring-blue-500/50 shadow-md',
        bg: 'bg-blue-500/25',
        badge: 'bg-blue-600 text-white',
      }
    }
    if (confidence >= 0.9) {
      return {
        border: 'border-emerald-500 hover:border-emerald-600',
        bg: 'bg-emerald-500/15 hover:bg-emerald-500/25',
        badge: 'bg-emerald-700 text-white',
      }
    }
    if (confidence >= 0.7) {
      return {
        border: 'border-amber-500 hover:border-amber-600',
        bg: 'bg-amber-500/20 hover:bg-amber-500/30',
        badge: 'bg-amber-700 text-white',
      }
    }
    // Low confidence < 70% (Red)
    return {
      border: 'border-rose-500 hover:border-rose-600 animate-pulse',
      bg: 'bg-rose-500/25 hover:bg-rose-500/35',
      badge: 'bg-rose-700 text-white',
    }
  }

  const getField = (key: string) => document.fields.find((f) => f.key === key)
  const getVal = (key: string, fallback: string = '') => {
    const f = getField(key)
    return f ? (f.correctedValue || f.originalValue || fallback) : fallback
  }

  const isTaxForm =
    lowerName.includes('w9') ||
    lowerName.includes('w4') ||
    lowerName.includes('tax') ||
    lowerName.includes('thue') ||
    document.id === 'doc-frm-003'

  return (
    <div className="flex h-full flex-col rounded-2xl border border-slate-200 bg-slate-900/5 shadow-xs overflow-hidden">
      {/* Top Document Viewer Toolbar */}
      <div className="flex flex-wrap items-center justify-between border-b border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-700 select-none shrink-0 gap-y-1.5">
        {/* Left: View Controls */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleZoomOut}
            title={t.reviewWorkspace.zoomOut}
            className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </button>
          <span className="min-w-9 text-center font-mono font-medium text-slate-700 text-[11px]">
            {zoom}%
          </span>
          <button
            type="button"
            onClick={handleZoomIn}
            title={t.reviewWorkspace.zoomIn}
            className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={handleResetZoom}
            title={t.reviewWorkspace.resetZoom}
            className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={handleFitPage}
            title={t.reviewWorkspace.fitPage}
            className="inline-flex items-center px-2 py-1 rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100 text-[11px] font-medium"
          >
            {t.reviewWorkspace.fitPage}
          </button>
          <button
            type="button"
            onClick={handleFitWidth}
            title={t.reviewWorkspace.fitWidth}
            className="hidden sm:inline-flex items-center px-2 py-1 rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100 text-[11px] font-medium"
          >
            {t.reviewWorkspace.fitWidth}
          </button>
        </div>

        {/* Center: Overlays Toggle & Real File View Toggle */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* File View Switcher if fileUrl is available */}
          {document.fileUrl && (
            <div className="flex items-center rounded-lg border border-slate-200 bg-slate-100 p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setViewMode('original')}
                title="Xem file gốc đã tải lên"
                className={`flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold transition-all ${
                  viewMode === 'original'
                    ? 'bg-white text-blue-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <FileText className="h-3 w-3" />
                <span>File gốc ({isPdf ? 'PDF' : isImage ? 'Ảnh' : 'Tập tin'})</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('ocr')}
                title="Xem bản phân tích OCR & Bounding Box"
                className={`flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold transition-all ${
                  viewMode === 'ocr'
                    ? 'bg-white text-blue-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Layers className="h-3 w-3" />
                <span>Lớp phủ OCR</span>
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={() => setShowBoxes(!showBoxes)}
            className={`inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-[11px] font-medium transition-colors ${
              showBoxes
                ? 'border-blue-200 bg-blue-50 text-blue-700'
                : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50'
            }`}
          >
            <Eye className="h-3 w-3" />
            <span className="hidden sm:inline">{t.reviewWorkspace.toggleBoxes}</span>
          </button>

          <button
            type="button"
            onClick={() => setShowLabels(!showLabels)}
            className={`inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-[11px] font-medium transition-colors ${
              showLabels
                ? 'border-blue-200 bg-blue-50 text-blue-700'
                : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50'
            }`}
          >
            <SlidersHorizontal className="h-3 w-3" />
            <span className="hidden sm:inline">{t.reviewWorkspace.toggleLabels}</span>
          </button>

          <button
            type="button"
            onClick={() => setFilterLowConfOnly(!filterLowConfOnly)}
            className={`inline-flex items-center gap-1 rounded-lg border px-1.5 py-1 text-[11px] font-medium transition-colors ${
              filterLowConfOnly
                ? 'border-amber-300 bg-amber-50 text-amber-800 font-semibold'
                : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50'
            }`}
          >
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            <span>&lt;90%</span>
          </button>
        </div>

        {/* Right: Page Navigation and Open in new tab */}
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          {document.fileUrl && (
            <a
              href={document.fileUrl}
              target="_blank"
              rel="noopener noreferrer"
              title="Mở file gốc trong tab mới"
              className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
          <button
            type="button"
            disabled={document.currentPage <= 1}
            className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-200 text-slate-600 disabled:opacity-40"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <span className="font-medium text-slate-700 text-[11px]">
            {document.currentPage}/{document.pageCount}
          </span>
          <button
            type="button"
            disabled={document.currentPage >= document.pageCount}
            className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-200 text-slate-600 disabled:opacity-40"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Main Scanned Document Canvas Area with Scroll */}
      <div
        ref={containerRef}
        className="relative flex-1 overflow-auto bg-slate-200/60 p-4 flex justify-center items-start min-h-[540px]"
      >
        {/* CASE 1: REAL UPLOADED FILE PREVIEW (Native Vector PDF or Real Image) */}
        {document.fileUrl && viewMode === 'original' ? (
          isPdf ? (
            <div className="w-full h-full min-h-[640px] flex flex-col bg-white rounded-lg shadow-md border border-slate-300 overflow-hidden">
              <iframe
                src={`${document.fileUrl}#view=FitH&toolbar=0`}
                title={document.filename}
                className="w-full flex-1 min-h-[640px] border-0 bg-white"
              />
            </div>
          ) : isImage ? (
            <div
              className="relative transition-transform duration-150 origin-top bg-white shadow-xl rounded-sm border border-slate-300 max-w-full"
              style={{
                width: `${Math.round(500 * (zoom / 100))}px`,
              }}
            >
              <img
                src={document.fileUrl}
                alt={document.filename}
                className="w-full h-auto object-contain block select-none pointer-events-none rounded-sm"
              />
              {/* Overlaid Bounding Boxes on Real Image */}
              {showBoxes &&
                visibleBoxes.map((box: BoundingBox) => {
                  const isSelected = selectedFieldKey === box.fieldKey
                  const isHovered = hoveredBoxId === box.id
                  const colors = getBoxColorClasses(box.confidence, isSelected)

                  return (
                    <div
                      key={box.id}
                      onClick={() => onSelectField(box.fieldKey)}
                      onMouseEnter={() => setHoveredBoxId(box.id)}
                      onMouseLeave={() => setHoveredBoxId(null)}
                      style={{
                        left: `${box.x * 100}%`,
                        top: `${box.y * 100}%`,
                        width: `${box.width * 100}%`,
                        height: `${box.height * 100}%`,
                      }}
                      className={`absolute cursor-pointer border-2 transition-all duration-150 z-10 ${
                        colors.border
                      } ${colors.bg}`}
                    >
                      {showLabels && (
                        <div
                          className={`absolute -top-5 left-0 z-20 flex items-center gap-1 whitespace-nowrap rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold tracking-wide shadow-sm transition-opacity ${
                            colors.badge
                          } ${isSelected || isHovered ? 'opacity-100 scale-105' : 'opacity-85'}`}
                        >
                          <span>{box.label}</span>
                          <span className="opacity-90">
                            {Math.round(box.confidence * 100)}%
                          </span>
                        </div>
                      )}
                    </div>
                  )
                })}
            </div>
          ) : (
            <div className="w-full h-full min-h-[640px] flex flex-col bg-white rounded-lg shadow-md border border-slate-300 overflow-hidden">
              <iframe
                src={document.fileUrl}
                title={document.filename}
                className="w-full flex-1 min-h-[640px] border-0 bg-white"
              />
            </div>
          )
        ) : (
          /* CASE 2: UNIVERSAL DYNAMIC DOCUMENT & OCR CANVAS */
          <div
            className="relative transition-transform duration-150 origin-top bg-white shadow-xl rounded-sm border border-slate-300 max-w-full"
            style={{
              width: `${Math.round(500 * (zoom / 100))}px`,
              minHeight: `${Math.round(700 * (zoom / 100))}px`,
            }}
          >
            {/* Scanned Document Visual Content */}
            <div className="p-6 font-sans text-slate-800 select-none pointer-events-none">
              {document.classification.predictedType === 'invoice' && (
                <div className="space-y-6">
                  {/* Header */}
                  <div className="flex items-start justify-between border-b-2 border-slate-800 pb-4">
                    <div>
                      <h2 className="text-xl font-black tracking-tight text-slate-900 uppercase">
                        {getVal('supplier', 'Apex Global Logistics Inc.')}
                      </h2>
                      <p className="text-[11px] text-slate-500 mt-1">
                        450 Maritime Boulevard, Suite 800 · San Francisco, CA 94105
                      </p>
                      <p className="text-[11px] text-slate-500">
                        Phone: (415) 892-0199 · Tax ID: US-88291039-X
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="text-2xl font-black text-slate-900 tracking-wider">
                        INVOICE
                      </span>
                      <p className="text-xs font-mono font-bold text-slate-700 mt-1">
                        {getVal('invoice_number', 'INV-2024-0089')}
                      </p>
                    </div>
                  </div>

                  {/* Metadata Row */}
                  <div className="grid grid-cols-2 gap-4 text-xs pt-1">
                    <div className="rounded border border-slate-200 p-3 bg-slate-50/50">
                      <p className="font-bold text-slate-600 text-[10px] uppercase">BILLED TO:</p>
                      <p className="font-bold text-slate-900 mt-1">
                        {getVal('customer', 'OmniTech Solutions Corp.')}
                      </p>
                      <p className="text-slate-500 text-[11px]">742 Innovation Way, Floor 14</p>
                      <p className="text-slate-500 text-[11px]">Austin, TX 78701 · USA</p>
                    </div>
                    <div className="rounded border border-slate-200 p-3 bg-slate-50/50 space-y-1">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Invoice Date:</span>
                        <span className="font-mono font-semibold text-slate-900">
                          {getVal('issue_date', '2024-10-15')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Payment Due:</span>
                        <span className="font-mono font-semibold text-slate-900">
                          {getVal('due_date', '2024-11-15')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Currency:</span>
                        <span className="text-slate-700 font-mono font-bold">
                          {getVal('currency', 'USD')}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Line Items Table */}
                  <div className="pt-2">
                    <table className="w-full text-left text-[11px]">
                      <thead>
                        <tr className="border-b border-slate-300 bg-slate-100 text-slate-600 font-bold uppercase">
                          <th className="py-2 px-3">Item Description</th>
                          <th className="py-2 px-2 text-right">Qty</th>
                          <th className="py-2 px-2 text-right">Unit Rate</th>
                          <th className="py-2 px-3 text-right">Amount</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200">
                        <tr>
                          <td className="py-2.5 px-3 font-medium">Standard Processing & Operations Services</td>
                          <td className="py-2.5 px-2 text-right font-mono">1</td>
                          <td className="py-2.5 px-2 text-right font-mono">{getVal('subtotal', '$14,250.00')}</td>
                          <td className="py-2.5 px-3 text-right font-mono font-semibold">{getVal('subtotal', '$14,250.00')}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* Totals Section */}
                  <div className="flex justify-end pt-4">
                    <div className="w-64 space-y-2 border-t-2 border-slate-800 pt-3 text-xs">
                      <div className="flex justify-between text-slate-600">
                        <span>Subtotal:</span>
                        <span className="font-mono font-semibold text-slate-800">
                          {getVal('subtotal', '$14,250.00')}
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Tax / VAT (8.0%):</span>
                        <span className="font-mono font-semibold text-slate-800">
                          {getVal('tax', '$1,140.00')}
                        </span>
                      </div>
                      <div className="flex justify-between border-t border-slate-300 pt-2 text-sm font-bold text-slate-900">
                        <span>Total Net Due:</span>
                        <span className="font-mono text-base font-black">
                          {getVal('total', '$15,390.00')}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Footer notes */}
                  <div className="pt-8 border-t border-slate-200 flex items-center justify-between text-[10px] text-slate-400">
                    <div>
                      <p>DocuMind Automated IDP Recognition Engine.</p>
                      <p>Electronic invoice record generated for review.</p>
                    </div>
                    <div className="flex items-center gap-1 font-mono text-[9px] bg-slate-100 px-2 py-1 rounded">
                      |||||| | |||||||| |||| | ||||| {getVal('invoice_number', 'INV-0089')}
                    </div>
                  </div>
                </div>
              )}

              {document.classification.predictedType === 'contract' && (
                <div className="space-y-6">
                  <div className="text-center border-b pb-4">
                    <p className="text-xs tracking-widest uppercase text-slate-400 font-bold">Confidential Legal Document</p>
                    <h2 className="text-lg font-black tracking-tight text-slate-900 mt-1 uppercase">
                      {getVal('title', 'MASTER SERVICES AGREEMENT')}
                    </h2>
                    <p className="font-mono text-xs text-slate-600 mt-1">
                      REF: {getVal('contract_number', 'CTR-2024-8812-MSA')}
                    </p>
                  </div>
                  <div className="text-xs leading-relaxed space-y-3 text-slate-700">
                    <p>
                      This Master Services Agreement is executed by and between:
                    </p>
                    <div className="border p-3 rounded bg-slate-50">
                      <p className="font-bold text-slate-900">PARTY A: {getVal('party_a', 'Synthetix AI Laboratories, Inc.')}</p>
                      <p className="text-slate-500 text-[11px]">Authorized Service Provider</p>
                    </div>
                    <div className="border p-3 rounded bg-slate-50">
                      <p className="font-bold text-slate-900">PARTY B: {getVal('party_b', 'Nexus Enterprise Holdings LLC')}</p>
                      <p className="text-slate-500 text-[11px]">Authorized Enterprise Client</p>
                    </div>
                    <p>
                      1. <strong>Term & Expiry:</strong> Effective as of <strong>{getVal('effective_date', '2024-11-01')}</strong> until <strong>{getVal('expiry_date', '2026-10-31')}</strong>.
                    </p>
                    <p>
                      2. <strong>Contract Value:</strong> Total contract ceiling value is <strong>{getVal('contract_value', '$480,000.00 USD')}</strong>.
                    </p>
                    <p>
                      3. <strong>Governing Law:</strong> Governed in accordance with the laws of <strong>{getVal('governing_law', 'State of Delaware, USA')}</strong>.
                    </p>
                  </div>
                </div>
              )}

              {document.classification.predictedType === 'form' && isEmployeeForm && (
                <div className="space-y-4">
                  {/* Header */}
                  <div className="text-center border-b-2 border-slate-900 pb-2.5">
                    <h2 className="text-lg font-black tracking-wider text-slate-900 uppercase">
                      {getVal('form_title', 'EMPLOYEE INFORMATION FORM')}
                    </h2>
                    <p className="text-[10px] italic text-slate-500 mt-0.5">
                      Please fill out this form completely in block letters or clear handwriting.
                    </p>
                  </div>

                  {/* Section I: PERSONAL INFORMATION */}
                  <div className="border border-slate-300 rounded p-3 bg-slate-50/50 space-y-2">
                    <div className="border-b border-slate-200 pb-1">
                      <span className="text-[10px] font-bold text-blue-900 uppercase tracking-wider bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200">
                        I. PERSONAL INFORMATION
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div className="col-span-2">
                        <span className="text-slate-500 text-[10px] block">Full Name:</span>
                        <span className="font-bold text-slate-900">{getVal('full_name', 'Nguyễn Văn An')}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Gender:</span>
                        <span className="font-semibold text-slate-800">[✓] {getVal('gender', 'Male')}</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-500 text-[10px] block">Date of Birth (DD/MM/YYYY):</span>
                        <span className="font-mono font-medium text-slate-900">{getVal('date_of_birth', '15/08/1994')}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Place of Birth:</span>
                        <span className="font-medium text-slate-800">{getVal('place_of_birth', 'Hà Nội')}</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-500 text-[10px] block">ID/Passport No.:</span>
                        <span className="font-mono font-bold text-slate-900">{getVal('id_number', '001094002819')}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Marital Status:</span>
                        <span className="text-slate-700 font-medium">[✓] {getVal('marital_status', 'Single')}</span>
                      </div>
                    </div>
                  </div>

                  {/* Section II: CONTACT INFORMATION */}
                  <div className="border border-slate-300 rounded p-3 bg-slate-50/50 space-y-2">
                    <div className="border-b border-slate-200 pb-1">
                      <span className="text-[10px] font-bold text-blue-900 uppercase tracking-wider bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200">
                        II. CONTACT INFORMATION
                      </span>
                    </div>
                    <div className="text-xs">
                      <span className="text-slate-500 text-[10px] block">Permanent Address:</span>
                      <span className="font-medium text-slate-800">{getVal('permanent_address', '128 Cầu Giấy, P. Dịch Vọng, Q. Cầu Giấy, Hà Nội')}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-500 text-[10px] block">Mobile Phone:</span>
                        <span className="font-mono font-bold text-slate-900">{getVal('mobile_phone', '+84 912 345 678')}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Personal Email:</span>
                        <span className="font-mono text-slate-800">{getVal('personal_email', 'an.nguyen@example.com')}</span>
                      </div>
                    </div>
                  </div>

                  {/* Section III: EDUCATION & EMPLOYMENT */}
                  <div className="border border-slate-300 rounded p-3 bg-slate-50/50 space-y-2">
                    <div className="border-b border-slate-200 pb-1">
                      <span className="text-[10px] font-bold text-blue-900 uppercase tracking-wider bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200">
                        III. EDUCATION & EMPLOYMENT
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-500 text-[10px] block">Applied/Appointed Position:</span>
                        <span className="font-bold text-slate-900">{getVal('position', 'Senior AI Engineer')}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Department:</span>
                        <span className="font-semibold text-slate-800">{getVal('department', 'AI Solutions & IDP Lab')}</span>
                      </div>
                    </div>
                    <div className="text-xs">
                      <span className="text-slate-500 text-[10px] block">Available Start Date:</span>
                      <span className="font-mono font-semibold text-slate-900">{getVal('start_date', '2026-11-01')}</span>
                    </div>
                  </div>
                </div>
              )}

              {document.classification.predictedType === 'form' && isTaxForm && !isEmployeeForm && (
                <div className="space-y-4">
                  <div className="border-b-2 border-slate-900 pb-2">
                    <div className="flex justify-between items-baseline">
                      <h2 className="text-lg font-black text-slate-900">
                        {getVal('form_title', 'Form W-9 (Rev. 2024)')}
                      </h2>
                      <span className="text-xs text-slate-500 font-bold">Department of the Treasury · IRS</span>
                    </div>
                    <p className="text-xs font-semibold text-slate-700 mt-1">
                      Request for Taxpayer Identification Number and Certification
                    </p>
                  </div>
                  <div className="space-y-3 text-xs">
                    <div className="border p-2.5 rounded bg-slate-50">
                      <span className="text-slate-500 text-[10px] block">1. Name of entity:</span>
                      <span className="font-bold text-slate-900">{getVal('entity_name', 'Starlight Technologies LLC')}</span>
                    </div>
                    <div className="border p-2.5 rounded bg-slate-50">
                      <span className="text-slate-500 text-[10px] block">2. Business / DBA name:</span>
                      <span className="font-semibold text-slate-800">{getVal('business_name', 'Starlight Cloud Solutions')}</span>
                    </div>
                    <div className="border p-2.5 rounded bg-slate-50">
                      <span className="text-slate-500 text-[10px] block">3. Federal Tax Classification:</span>
                      <span className="font-medium text-slate-800">{getVal('tax_classification', 'Limited Liability Company (LLC)')}</span>
                    </div>
                    <div className="border p-2.5 rounded bg-slate-50 flex justify-between">
                      <div>
                        <span className="text-slate-500 text-[10px] block">Employer Identification No. (EIN):</span>
                        <span className="font-mono font-bold text-slate-900">{getVal('ein_number', '84-9128374')}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-[10px] block">Exemption Payee Code:</span>
                        <span className="font-mono text-slate-700">{getVal('exemption_code', 'Code 4 (Exempt)')}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* DYNAMIC GENERAL FORM (For Any Other Form) */}
              {document.classification.predictedType === 'form' && !isEmployeeForm && !isTaxForm && (
                <div className="space-y-4">
                  <div className="border-b-2 border-slate-900 pb-2">
                    <h2 className="text-lg font-black text-slate-900 uppercase">
                      {getVal('form_title', document.filename.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' '))}
                    </h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Intelligent Document Processing - Automated Form Field Detection
                    </p>
                  </div>

                  <div className="space-y-3 text-xs">
                    {document.fields
                      .filter((f) => f.key !== 'form_title')
                      .map((field) => (
                        <div
                          key={field.key}
                          onClick={() => onSelectField(field.key)}
                          className={`cursor-pointer rounded border p-2.5 transition-all ${
                            selectedFieldKey === field.key
                              ? 'border-blue-500 bg-blue-50/70 ring-1 ring-blue-400'
                              : 'border-slate-200 bg-slate-50 hover:bg-slate-100/80'
                          }`}
                        >
                          <span className="text-[10px] font-semibold text-slate-500 block uppercase tracking-wide">
                            {field.labelVi} ({field.labelEn})
                          </span>
                          <span className="font-medium text-slate-900 mt-0.5 block text-sm">
                            {field.correctedValue || field.originalValue || '[Chưa có giá trị]'}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>

            {/* Overlaid Bounding Boxes (Normalized Coordinates scaled to Container) */}
            {showBoxes &&
              visibleBoxes.map((box: BoundingBox) => {
                const isSelected = selectedFieldKey === box.fieldKey
                const isHovered = hoveredBoxId === box.id
                const colors = getBoxColorClasses(box.confidence, isSelected)

                return (
                  <div
                    key={box.id}
                    onClick={() => onSelectField(box.fieldKey)}
                    onMouseEnter={() => setHoveredBoxId(box.id)}
                    onMouseLeave={() => setHoveredBoxId(null)}
                    style={{
                      left: `${box.x * 100}%`,
                      top: `${box.y * 100}%`,
                      width: `${box.width * 100}%`,
                      height: `${box.height * 100}%`,
                    }}
                    className={`absolute cursor-pointer border-2 transition-all duration-150 z-10 ${
                      colors.border
                    } ${colors.bg}`}
                  >
                    {/* Floating Label Chip */}
                    {showLabels && (
                      <div
                        className={`absolute -top-5 left-0 z-20 flex items-center gap-1 whitespace-nowrap rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold tracking-wide shadow-sm transition-opacity ${
                          colors.badge
                        } ${isSelected || isHovered ? 'opacity-100 scale-105' : 'opacity-85'}`}
                      >
                        <span>{box.label}</span>
                        <span className="opacity-90">
                          {Math.round(box.confidence * 100)}%
                        </span>
                      </div>
                    )}

                    {/* High confidence or low confidence indicator icon on box corner */}
                    {box.confidence < 0.7 && (
                      <div className="absolute -bottom-2 -right-2 flex h-4 w-4 items-center justify-center rounded-full bg-rose-600 text-[9px] font-bold text-white shadow-xs">
                        !
                      </div>
                    )}
                  </div>
                )
              })}
          </div>
        )}
      </div>

      {/* Viewer Footer: BBox Legend & Normalized Info */}
      <div className="flex flex-wrap items-center justify-between border-t border-slate-200 bg-white px-4 py-2 text-[11px] text-slate-500">
        <div className="flex items-center gap-3">
          <span className="font-medium text-slate-700">Confidence Scale:</span>
          <span className="flex items-center gap-1 text-emerald-700 font-medium">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            &gt;90% High
          </span>
          <span className="flex items-center gap-1 text-amber-700 font-medium">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            70–90% Medium
          </span>
          <span className="flex items-center gap-1 text-rose-700 font-medium">
            <span className="h-2 w-2 rounded-full bg-rose-500" />
            &lt;70% Low
          </span>
        </div>

        <div className="flex items-center gap-2 font-mono text-[10px] text-slate-400">
          <Sparkles className="h-3 w-3 text-indigo-500" />
          <span>Normalized Coordinates [x, y, w, h] · PaddleOCR</span>
        </div>
      </div>
    </div>
  )
}
