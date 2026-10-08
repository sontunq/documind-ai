import { useState } from 'react'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  Download,
  Calendar,
  Layers,
  Sparkles,
  Info,
} from 'lucide-react'
import {
  mockKPIs,
  mockModelHistoryData,
  mockFieldAccuracyData,
  mockConfusionMatrix,
  mockQualityBreakdown,
} from '../../data/mockIdpData'
import { useI18n } from '../../lib/i18n'

export function EvaluationDashboardView() {
  const { t, lang } = useI18n()
  const [selectedDataset, setSelectedDataset] = useState('v2.1-prod-gold')
  const [timeRange, setTimeRange] = useState('30d')

  return (
    <div className="space-y-5 p-4 sm:p-6 max-w-full min-w-0">
      {/* Top Controls & Dataset Selector */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-blue-600">
            {t.metricsDashboard.eyebrow}
          </span>
          <h2 className="text-lg font-bold tracking-tight text-slate-900 sm:text-xl truncate">
            {t.metricsDashboard.title}
          </h2>
          <p className="text-xs text-slate-500 truncate">
            {t.metricsDashboard.subtitle}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          {/* Dataset selector */}
          <div className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 shadow-xs">
            <Layers className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
              className="text-xs font-semibold text-slate-800 bg-transparent focus:outline-none"
            >
              <option value="v2.1-prod-gold">v2.1-prod-gold (910 docs)</option>
              <option value="v2.0-eval-test">v2.0-eval-test (450 docs)</option>
              <option value="v1.8-synthetic">v1.8-synthetic (1,200 docs)</option>
            </select>
          </div>

          {/* Time range */}
          <div className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 shadow-xs">
            <Calendar className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="text-xs font-medium text-slate-700 bg-transparent focus:outline-none"
            >
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
              <option value="all">Full Lifecycle</option>
            </select>
          </div>

          {/* Export Report button */}
          <button
            type="button"
            onClick={() => alert('Exporting evaluation metrics report to JSON/CSV...')}
            className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-slate-800 transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
            <span>{t.metricsDashboard.exportReport}</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid (OCR CER, OCR WER, Classification Accuracy, Macro F1, etc.) */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {mockKPIs.map((kpi) => {
          return (
            <div
              key={kpi.id}
              className="group rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs hover:border-blue-300 transition-all min-w-0"
            >
              <div className="flex items-center justify-between text-slate-500 gap-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 truncate">
                  {lang === 'vi' ? kpi.titleVi : kpi.titleEn}
                </span>
                {kpi.isPositive ? (
                  <span className="flex items-center gap-0.5 rounded-md bg-emerald-50 px-1 py-0.5 text-[10px] font-semibold text-emerald-700 border border-emerald-200/60 shrink-0">
                    <TrendingUp className="h-2.5 w-2.5" />
                    {kpi.delta}
                  </span>
                ) : (
                  <span className="flex items-center gap-0.5 rounded-md bg-rose-50 px-1 py-0.5 text-[10px] font-semibold text-rose-700 border border-rose-200/60 shrink-0">
                    <TrendingDown className="h-2.5 w-2.5" />
                    {kpi.delta}
                  </span>
                )}
              </div>

              <div className="mt-2 flex items-baseline gap-1">
                <span className="font-mono text-xl font-black text-slate-900 sm:text-2xl">
                  {kpi.value}
                </span>
                {kpi.unit && (
                  <span className="text-[10px] text-slate-400">{kpi.unit}</span>
                )}
              </div>

              <p className="mt-1 text-[10px] text-slate-500 line-clamp-2">
                {lang === 'vi' ? kpi.descriptionVi : kpi.descriptionEn}
              </p>
            </div>
          )
        })}
      </div>

      {/* Recharts Chart 1: Precision, Recall & F1-Score Over Time */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-blue-600" />
              <span>{t.metricsDashboard.trendHistoryTitle}</span>
            </h3>
            <p className="text-xs text-slate-500">
              {t.metricsDashboard.trendHistoryDesc}
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono">
            <span className="flex items-center gap-1.5 text-blue-700 font-semibold">
              <span className="h-2.5 w-2.5 rounded-full bg-blue-600" />
              F1-Score
            </span>
            <span className="flex items-center gap-1.5 text-emerald-700 font-semibold">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
              Precision
            </span>
            <span className="flex items-center gap-1.5 text-indigo-700 font-semibold">
              <span className="h-2.5 w-2.5 rounded-full bg-indigo-400" />
              Recall
            </span>
          </div>
        </div>

        <div className="mt-6 h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={mockModelHistoryData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorF1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="colorPrec" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="iteration" stroke="#64748b" tick={{ fontSize: 11 }} />
              <YAxis domain={[80, 100]} stroke="#64748b" tick={{ fontSize: 11 }} unit="%" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderColor: '#e2e8f0',
                  borderRadius: '12px',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                  fontSize: '12px',
                }}
              />
              <Area
                type="monotone"
                dataKey="f1Score"
                name="F1-Score (%)"
                stroke="#2563eb"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#colorF1)"
              />
              <Area
                type="monotone"
                dataKey="precision"
                name="Precision (%)"
                stroke="#10b981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorPrec)"
              />
              <Area
                type="monotone"
                dataKey="recall"
                name="Recall (%)"
                stroke="#818cf8"
                strokeWidth={2}
                strokeDasharray="4 4"
                fillOpacity={0}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 2: Per-Field Extraction Accuracy Bar Chart + Confusion Matrix */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 min-w-0">
        {/* Left: Per-Field Extraction Accuracy (Bar Chart) */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5 shadow-xs lg:col-span-7 min-w-0 overflow-hidden">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900 sm:text-base">
              {t.metricsDashboard.fieldAccuracyTitle}
            </h3>
            <p className="text-xs text-slate-500">
              {t.metricsDashboard.fieldAccuracyDesc}
            </p>
          </div>

          <div className="mt-4 h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={mockFieldAccuracyData}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 30, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                <XAxis type="number" domain={[80, 100]} stroke="#64748b" tick={{ fontSize: 11 }} unit="%" />
                <YAxis dataKey="fieldName" type="category" stroke="#64748b" tick={{ fontSize: 11 }} width={85} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderColor: '#e2e8f0',
                    borderRadius: '12px',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="f1Score" name="F1-Score (%)" fill="#3b82f6" radius={[0, 6, 6, 0]} barSize={12} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right: Document Classification Confusion Matrix */}
        <div className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5 shadow-xs lg:col-span-5 flex flex-col justify-between min-w-0 overflow-hidden">
          <div>
            <div className="border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900">
                {t.metricsDashboard.confusionMatrixTitle}
              </h3>
              <p className="text-xs text-slate-500">
                {t.metricsDashboard.confusionMatrixDesc}
              </p>
            </div>

            <div className="mt-5 overflow-x-auto">
              <table className="w-full text-center text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-semibold text-slate-600">
                    <th className="py-2.5 px-3 text-left">Actual Class</th>
                    <th className="py-2.5 px-2">Pred: Invoice</th>
                    <th className="py-2.5 px-2">Pred: Contract</th>
                    <th className="py-2.5 px-2">Pred: Form</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {mockConfusionMatrix.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="py-3 px-3 text-left font-sans font-medium text-slate-800">
                        {row.actual}
                      </td>
                      <td className="py-3 px-2">
                        <span
                          className={`inline-block px-2 py-1 rounded font-bold ${
                            row.predictedInvoice > 100
                              ? 'bg-blue-100 text-blue-800'
                              : 'text-slate-400'
                          }`}
                        >
                          {row.predictedInvoice}
                        </span>
                      </td>
                      <td className="py-3 px-2">
                        <span
                          className={`inline-block px-2 py-1 rounded font-bold ${
                            row.predictedContract > 100
                              ? 'bg-indigo-100 text-indigo-800'
                              : 'text-slate-400'
                          }`}
                        >
                          {row.predictedContract}
                        </span>
                      </td>
                      <td className="py-3 px-2">
                        <span
                          className={`inline-block px-2 py-1 rounded font-bold ${
                            row.predictedForm > 100
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'text-slate-400'
                          }`}
                        >
                          {row.predictedForm}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50/70 p-3 text-xs text-slate-500">
            <div className="flex items-center gap-1.5 font-semibold text-slate-700">
              <Info className="h-4 w-4 text-blue-600" />
              <span>Classification Accuracy: 98.24%</span>
            </div>
            <p className="mt-1 text-[11px]">
              Micro-average across all 910 evaluated document pages with 0.85 confidence threshold routing.
            </p>
          </div>
        </div>
      </div>

      {/* Row 3: Quality Error Distribution (CER & WER Breakdown) */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs">
        <div className="border-b border-slate-100 pb-3">
          <h3 className="text-base font-bold text-slate-900">
            {t.metricsDashboard.qualityAnalysisTitle}
          </h3>
          <p className="text-xs text-slate-500">
            {t.metricsDashboard.qualityAnalysisDesc}
          </p>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {mockQualityBreakdown.map((item, idx) => (
            <div
              key={idx}
              className="rounded-xl border border-slate-200/80 bg-slate-50/50 p-4"
            >
              <h4 className="text-xs font-bold text-slate-800">
                {item.qualityCategory}
              </h4>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {item.docCount} benchmark samples
              </p>
              <div className="mt-3 flex items-center justify-between border-t border-slate-200/60 pt-2 text-xs font-mono">
                <div>
                  <span className="text-slate-500 block text-[10px]">CER:</span>
                  <span
                    className={`font-bold ${
                      item.avgCer < 2.0 ? 'text-emerald-700' : 'text-amber-700'
                    }`}
                  >
                    {item.avgCer}%
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">WER:</span>
                  <span
                    className={`font-bold ${
                      item.avgWer < 4.0 ? 'text-emerald-700' : 'text-amber-700'
                    }`}
                  >
                    {item.avgWer}%
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
