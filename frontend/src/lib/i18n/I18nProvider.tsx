import { useEffect, useState, type ReactNode } from 'react'
import { I18nContext, type I18nContextValue } from './context'
import { translations, type Language } from './translations'

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(() => {
    const saved = localStorage.getItem('documind_lang')
    if (saved === 'en' || saved === 'vi') return saved
    return 'vi'
  })

  useEffect(() => {
    localStorage.setItem('documind_lang', lang)
    document.documentElement.lang = lang
  }, [lang])

  const setLang = (next: Language) => {
    setLangState(next)
  }

  const toggleLang = () => {
    setLangState((prev) => (prev === 'vi' ? 'en' : 'vi'))
  }

  const formatTemplate = (
    text: string,
    params: Record<string, string | number>,
  ) => {
    return Object.entries(params).reduce(
      (res, [key, val]) =>
        res.replace(new RegExp(`\\{${key}\\}`, 'g'), String(val)),
      text,
    )
  }

  const value: I18nContextValue = {
    lang,
    setLang,
    toggleLang,
    t: translations[lang],
    formatTemplate,
  }

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}
