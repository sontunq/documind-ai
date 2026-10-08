import { Globe } from 'lucide-react'
import { useI18n, type Language } from '../lib/i18n'

interface LanguageSwitcherProps {
  compact?: boolean
}

export function LanguageSwitcher({ compact = false }: LanguageSwitcherProps) {
  const { lang, setLang, t } = useI18n()

  const languages: { code: Language; label: string; full: string }[] = [
    { code: 'en', label: 'EN', full: t.langSwitcher.enFull },
    { code: 'vi', label: 'VN', full: t.langSwitcher.viFull },
  ]

  return (
    <div
      role="group"
      aria-label={t.langSwitcher.switchAria}
      className={`inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-100/90 p-1 text-xs shadow-xs transition-colors dark:border-slate-700/60 dark:bg-slate-800/90 ${
        compact ? 'p-0.5' : 'p-1'
      }`}
    >
      <Globe className="h-3.5 w-3.5 text-slate-500 ml-1 shrink-0" aria-hidden="true" />
      <span className="sr-only">{t.langSwitcher.switchAria}</span>
      <div className="flex items-center gap-0.5">
        {languages.map((item) => {
          const isActive = lang === item.code
          return (
            <button
              key={item.code}
              type="button"
              onClick={() => setLang(item.code)}
              title={item.full}
              aria-pressed={isActive}
              className={`flex items-center justify-center rounded-md px-2.5 py-1 font-medium text-xs tracking-wider transition-all duration-150 ${
                isActive
                  ? 'bg-white text-blue-700 font-semibold shadow-xs ring-1 ring-slate-200/50 dark:bg-slate-700 dark:text-blue-400 dark:ring-slate-600'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/50 dark:text-slate-400 dark:hover:text-slate-100'
              }`}
            >
              <span>{item.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
