import { useState } from 'react'
import {
  CheckCircle2,
  Zap,
  Save,
  Cpu,
  Webhook,
} from 'lucide-react'
import { useI18n } from '../../lib/i18n'

export function SettingsView() {
  const { t } = useI18n()
  const [stpThreshold, setStpThreshold] = useState<number>(90)
  const [reviewThreshold, setReviewThreshold] = useState<number>(85)
  const [activeEngine, setActiveEngine] = useState<string>('paddle')
  const [webhookUrl, setWebhookUrl] = useState<string>(
    'https://api.enterprise.corp/v1/documind/ingest-webhook',
  )
  const [savedNotification, setSavedNotification] = useState(false)

  const handleSave = () => {
    setSavedNotification(true)
    setTimeout(() => setSavedNotification(false), 3000)
  }

  return (
    <div className="max-w-4xl w-full space-y-5 p-4 sm:p-6 min-w-0">
      <div>
        <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-600">
          {t.settings.eyebrow}
        </span>
        <h2 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
          {t.settings.title}
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          {t.settings.subtitle}
        </p>
      </div>

      {savedNotification && (
        <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-semibold text-emerald-800">
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          <span>{t.settings.savedSuccess}</span>
        </div>
      )}

      {/* Model Confidence & STP Thresholds */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-6">
        <div className="flex items-center gap-2.5 border-b border-slate-100 pb-4">
          <Zap className="h-5 w-5 text-amber-500" />
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              {t.settings.thresholdTitle}
            </h3>
            <p className="text-xs text-slate-500">
              {t.settings.thresholdDesc}
            </p>
          </div>
        </div>

        <div className="space-y-5">
          <div>
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-800">
                Auto-Approval STP Threshold:
              </span>
              <span className="font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                {stpThreshold}% Confidence
              </span>
            </div>
            <input
              type="range"
              min="70"
              max="99"
              value={stpThreshold}
              onChange={(e) => setStpThreshold(Number(e.target.value))}
              className="mt-2.5 w-full accent-blue-600 cursor-pointer"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Documents where every extracted field scores ≥ {stpThreshold}% will bypass the HITL review queue and sync directly.
            </p>
          </div>

          <div className="pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-800">
                Low Confidence Warning Flag Threshold:
              </span>
              <span className="font-mono font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                {reviewThreshold}% Confidence
              </span>
            </div>
            <input
              type="range"
              min="60"
              max="90"
              value={reviewThreshold}
              onChange={(e) => setReviewThreshold(Number(e.target.value))}
              className="mt-2.5 w-full accent-amber-600 cursor-pointer"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Fields scoring below {reviewThreshold}% will be highlighted with caution badges in the reviewer workspace.
            </p>
          </div>
        </div>
      </section>

      {/* OCR Engine Selection */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2.5 border-b border-slate-100 pb-4">
          <Cpu className="h-5 w-5 text-indigo-500" />
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              {t.settings.engineTitle}
            </h3>
            <p className="text-xs text-slate-500">
              {t.settings.engineDesc}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <label
            className={`flex cursor-pointer flex-col rounded-xl border p-4 transition-colors ${
              activeEngine === 'paddle'
                ? 'border-blue-500 bg-blue-50/50 ring-1 ring-blue-500/20'
                : 'border-slate-200 hover:bg-slate-50'
            }`}
          >
            <input
              type="radio"
              name="ocr-engine"
              value="paddle"
              checked={activeEngine === 'paddle'}
              onChange={() => setActiveEngine('paddle')}
              className="sr-only"
            />
            <span className="text-xs font-bold text-slate-900">PaddleOCR v2.7 (Default)</span>
            <span className="text-[11px] text-slate-500 mt-1">
              Fast, high-accuracy multilingual recognition with normalized geometry.
            </span>
          </label>

          <label
            className={`flex cursor-pointer flex-col rounded-xl border p-4 transition-colors ${
              activeEngine === 'tesseract'
                ? 'border-blue-500 bg-blue-50/50 ring-1 ring-blue-500/20'
                : 'border-slate-200 hover:bg-slate-50'
            }`}
          >
            <input
              type="radio"
              name="ocr-engine"
              value="tesseract"
              checked={activeEngine === 'tesseract'}
              onChange={() => setActiveEngine('tesseract')}
              className="sr-only"
            />
            <span className="text-xs font-bold text-slate-900">Tesseract OCR v5.3</span>
            <span className="text-[11px] text-slate-500 mt-1">
              Open-source baseline engine with legacy layout extraction.
            </span>
          </label>

          <label
            className={`flex cursor-pointer flex-col rounded-xl border p-4 transition-colors ${
              activeEngine === 'cloud'
                ? 'border-blue-500 bg-blue-50/50 ring-1 ring-blue-500/20'
                : 'border-slate-200 hover:bg-slate-50'
            }`}
          >
            <input
              type="radio"
              name="ocr-engine"
              value="cloud"
              checked={activeEngine === 'cloud'}
              onChange={() => setActiveEngine('cloud')}
              className="sr-only"
            />
            <span className="text-xs font-bold text-slate-900">Cloud Vision API</span>
            <span className="text-[11px] text-slate-500 mt-1">
              External fallback provider for complex handwritten documents.
            </span>
          </label>
        </div>
      </section>

      {/* Downstream Webhook Sync */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
        <div className="flex items-center gap-2.5 border-b border-slate-100 pb-4">
          <Webhook className="h-5 w-5 text-emerald-600" />
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Downstream Enterprise ERP Webhook
            </h3>
            <p className="text-xs text-slate-500">
              Synchronize approved human-verified payloads into accounting or SAP/NetSuite
            </p>
          </div>
        </div>

        <div>
          <label htmlFor="webhook-url" className="text-xs font-semibold text-slate-700 block mb-1">
            Endpoint Webhook URL:
          </label>
          <input
            id="webhook-url"
            type="url"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            className="w-full rounded-xl border border-slate-200 px-3.5 py-2 font-mono text-xs text-slate-800 focus:border-blue-500 focus:outline-none"
          />
        </div>
      </section>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleSave}
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-blue-700 transition-colors"
        >
          <Save className="h-4 w-4" />
          <span>{t.settings.saveSettings}</span>
        </button>
      </div>
    </div>
  )
}
