import {
  UploadCloud,
  FileCheck,
  BarChart3,
  Sliders,
  Sparkles,
  Layers,
  CheckCircle2,
} from 'lucide-react'
import { LanguageSwitcher } from './LanguageSwitcher'
import { useI18n } from '../lib/i18n'

export type NavView = 'upload' | 'review' | 'metrics' | 'settings'

interface SidebarProps {
  currentView: NavView
  onSelectView: (view: NavView) => void
  pendingReviewCount?: number
  isBackendConnected?: boolean
}

export function Sidebar({
  currentView,
  onSelectView,
  pendingReviewCount = 3,
  isBackendConnected = true,
}: SidebarProps) {
  const { t } = useI18n()

  const navItems = [
    {
      id: 'upload' as NavView,
      label: t.sidebar.uploadIngestion,
      icon: UploadCloud,
      badge: null,
    },
    {
      id: 'review' as NavView,
      label: t.sidebar.reviewWorkspace,
      icon: FileCheck,
      badge: pendingReviewCount > 0 ? pendingReviewCount : null,
      badgeColor: 'bg-amber-100 text-amber-800 border border-amber-200/80',
    },
    {
      id: 'metrics' as NavView,
      label: t.sidebar.evalMetrics,
      icon: BarChart3,
      badge: null,
    },
    {
      id: 'settings' as NavView,
      label: t.sidebar.settings,
      icon: Sliders,
      badge: null,
    },
  ]

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-slate-200 bg-white text-slate-800 select-none z-20">
      {/* Brand & Header */}
      <div className="flex h-16 items-center gap-3 border-b border-slate-100 px-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-700 via-indigo-600 to-sky-500 shadow-sm shadow-blue-500/20 text-white">
          <Layers className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="font-bold tracking-tight text-slate-900 text-base">
              {t.brand}
            </span>
            <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200/60">
              IDP
            </span>
          </div>
          <p className="truncate text-xs text-slate-500">
            {t.subBrand}
          </p>
        </div>
      </div>

      {/* Main Navigation */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        <div>
          <p className="px-3 pb-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
            Platform Workflow
          </p>
          <nav className="space-y-1" aria-label="Sidebar Navigation">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = currentView === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onSelectView(item.id)}
                  className={`group flex w-full items-center justify-between rounded-xl px-3 py-2 text-xs sm:text-[13px] font-medium transition-all ${
                    isActive
                      ? 'bg-blue-50/80 text-blue-700 font-semibold shadow-xs border border-blue-100'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <Icon
                      className={`h-4 w-4 shrink-0 transition-colors ${
                        isActive ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-600'
                      }`}
                    />
                    <span className="truncate">{item.label}</span>
                  </div>
                  {item.badge !== null && (
                    <span
                      className={`ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${
                        item.badgeColor || 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              )
            })}
          </nav>
        </div>

        {/* AI Engine Status Card */}
        <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-3.5 text-xs">
          <div className="flex items-center gap-2 font-semibold text-slate-700">
            <Sparkles className="h-4 w-4 text-indigo-500" />
            <span>AI Pipeline Stack</span>
          </div>
          <div className="mt-2.5 space-y-2 text-slate-600">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">OCR Engine:</span>
              <span className="font-mono text-[11px] font-medium text-slate-800">
                PaddleOCR v2.7
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Classifier:</span>
              <span className="font-mono text-[11px] font-medium text-slate-800">
                TF-IDF + LR v2.1
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Extractor:</span>
              <span className="font-mono text-[11px] font-medium text-slate-800">
                LayoutLM + Rules
              </span>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-1.5 pt-2 border-t border-slate-200/60 text-[11px]">
            <span
              className={`h-2 w-2 rounded-full ${
                isBackendConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
              }`}
            />
            <span className="font-medium text-slate-600">
              {isBackendConnected ? 'FastAPI Service Ready' : 'Backend Standalone'}
            </span>
          </div>
        </div>
      </div>

      {/* Footer & Language Switcher */}
      <div className="border-t border-slate-200 bg-white p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-500">Language:</span>
          <LanguageSwitcher />
        </div>

        <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-100">
          <span>{t.sidebar.version}</span>
          <span className="flex items-center gap-1 text-emerald-700 font-medium">
            <CheckCircle2 className="h-3 w-3" /> Healthy
          </span>
        </div>
      </div>
    </aside>
  )
}
