import { createContext, useContext } from 'react'
import { type Language, type Translations } from './translations'

export interface I18nContextValue {
  lang: Language
  setLang: (lang: Language) => void
  toggleLang: () => void
  t: Translations
  formatTemplate: (text: string, params: Record<string, string | number>) => string
}

export const I18nContext = createContext<I18nContextValue | null>(null)

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext)
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider')
  }
  return context
}
