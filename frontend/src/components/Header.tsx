import { Search, Terminal, HelpCircle, ShieldCheck } from 'lucide-react'
import { useI18n } from '../lib/i18n'
import { LanguageSwitcher } from './LanguageSwitcher'

interface HeaderProps {
  title: string
  subtitle?: string
  searchValue?: string
  onSearchChange?: (val: string) => void
  showSearch?: boolean
}

export function Header({
  title,
  subtitle,
  searchValue = '',
  onSearchChange,
  showSearch = true,
}: HeaderProps) {
  const { t } = useI18n()

  return (
    <header className="shrink-0 z-20 flex h-16 w-full items-center justify-between border-b border-slate-200/90 bg-white px-4 sm:px-6">
      {/* Title & Context */}
      <div className="flex items-center gap-3 min-w-0 pr-3">
        <div className="min-w-0">
          <h1 className="text-base font-bold text-slate-900 tracking-tight sm:text-lg truncate">
            {title}
          </h1>
          {subtitle && (
            <p className="hidden text-xs text-slate-500 sm:block truncate">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-2.5 shrink-0">
        {showSearch && onSearchChange && (
          <div className="relative hidden md:block w-44 lg:w-60">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchValue}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={t.header.searchPlaceholder}
              className="w-full rounded-xl border border-slate-200 bg-slate-50/80 py-1.5 pl-8 pr-3 text-xs text-slate-800 placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/10 transition-all"
            />
          </div>
        )}

        {/* Environment badge */}
        <div className="hidden lg:flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-slate-50 px-2.5 py-1 text-xs text-slate-600">
          <ShieldCheck className="h-3.5 w-3.5 text-blue-600" />
          <span className="font-medium text-slate-700">{t.header.environment}</span>
          <span className="text-slate-300">·</span>
          <span className="text-slate-500 font-mono text-[11px]">{t.header.batch}</span>
        </div>

        {/* Language switcher in header */}
        <div className="flex items-center">
          <LanguageSwitcher compact />
        </div>

        <button
          type="button"
          title="Terminal logs & API"
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors"
        >
          <Terminal className="h-4 w-4" />
        </button>

        <button
          type="button"
          title="Help & Documentation"
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors"
        >
          <HelpCircle className="h-4 w-4" />
        </button>
      </div>
    </header>
  )
}
