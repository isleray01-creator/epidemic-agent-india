import React, { useState } from 'react';
import { History, CheckCircle, BarChart2, TrendingUp, AlertTriangle, ArrowRight } from 'lucide-react';

interface HistoricalVariant {
  id: string;
  name: string;
  wavePeriod: string;
  actualPeakCases: string;
  predictedPeakCases: string;
  peakDayVariance: string;
  modelFitAccuracy: string;
  mapeError: string;
  r0Real: number;
  r0Predicted: number;
  status: 'Validated' | 'Historical Benchmark' | 'Active Testing';
}

export const BacktestingView: React.FC = () => {
  const [selectedVariantId, setSelectedVariantId] = useState<string>('omicron-ba5');

  const historicalVariants: HistoricalVariant[] = [
    {
      id: 'omicron-ba5',
      name: 'Omicron BA.5.2.1 (Current Wave)',
      wavePeriod: 'Jan 2026 – Present',
      actualPeakCases: '2.10M (projected)',
      predictedPeakCases: '2.18M (ensemble)',
      peakDayVariance: '+2 Days',
      modelFitAccuracy: '95.8%',
      mapeError: '4.2%',
      r0Real: 2.38,
      r0Predicted: 2.45,
      status: 'Active Testing',
    },
    {
      id: 'delta-2021',
      name: 'Delta B.1.617.2 (2021 Wave)',
      wavePeriod: 'Mar 2021 – Jun 2021',
      actualPeakCases: '3.91M',
      predictedPeakCases: '3.84M',
      peakDayVariance: '-1 Day',
      modelFitAccuracy: '97.2%',
      mapeError: '2.8%',
      r0Real: 3.20,
      r0Predicted: 3.14,
      status: 'Historical Benchmark',
    },
    {
      id: 'nipah-2024',
      name: 'Nipah Virus Clade-V (Kerala)',
      wavePeriod: 'Sep 2024 – Oct 2024',
      actualPeakCases: '48 Cases (Localized Ring)',
      predictedPeakCases: '52 Cases',
      peakDayVariance: '0 Days',
      modelFitAccuracy: '93.1%',
      mapeError: '6.9%',
      r0Real: 0.48,
      r0Predicted: 0.51,
      status: 'Validated',
    },
    {
      id: 'h5n1-2025',
      name: 'Avian H5N1 Clade 2.3.4.4b',
      wavePeriod: 'Nov 2025 – Dec 2025',
      actualPeakCases: '1.2K (Poultry/Zoonotic Sentinel)',
      predictedPeakCases: '1.4K',
      peakDayVariance: '+1 Day',
      modelFitAccuracy: '91.4%',
      mapeError: '8.6%',
      r0Real: 0.88,
      r0Predicted: 0.94,
      status: 'Validated',
    },
  ];

  const currentVariant = historicalVariants.find((v) => v.id === selectedVariantId) || historicalVariants[0];

  return (
    <div className="flex flex-col w-full gap-6">
      {/* Header */}
      <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded bg-teal-100 text-teal-800 text-xs font-mono font-bold">
              MODEL VALIDATION & HISTORICAL BACKTESTING
            </span>
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-[#0d3b36]">
            Historical Pathogen Calibration & Rigorous Backtesting
          </h1>
          <p className="text-xs text-slate-500 font-body">
            Verify PINN mathematical models against recorded genomic ground truth across prior Indian outbreaks.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono bg-emerald-50 text-emerald-800 px-3 py-2 rounded-xl border border-emerald-200">
          <CheckCircle className="w-4 h-4" />
          <span className="font-bold">ENSEMBLE RELIABILITY: 94.8%</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
            Mean Abs. Percentage Error (MAPE)
          </span>
          <span className="font-headline text-3xl font-extrabold text-[#0d3b36]">
            4.82%
          </span>
          <span className="text-[11px] text-emerald-700 font-semibold block mt-1">
            Across 14 calibrated epochs
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
            Peak Arrival Precision
          </span>
          <span className="font-headline text-3xl font-extrabold text-slate-900">
            ± 1.2 Days
          </span>
          <span className="text-[11px] text-teal-700 font-semibold block mt-1">
            Median peak day variance
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
            R₀ Elasticity Concordance
          </span>
          <span className="font-headline text-3xl font-extrabold text-[#0d3b36]">
            0.962
          </span>
          <span className="text-[11px] text-emerald-700 font-semibold block mt-1">
            Pearson correlation (r)
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-2xs">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
            ICU Overburden Prediction
          </span>
          <span className="font-headline text-3xl font-extrabold text-amber-600">
            92.1%
          </span>
          <span className="text-[11px] text-amber-700 font-semibold block mt-1">
            Early warning buffer &gt; 9 days
          </span>
        </div>
      </div>

      {/* Historical Outbreak Selector and Detailed Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Outbreak list */}
        <div className="lg:col-span-5 bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col gap-2">
          <span className="text-xs font-headline font-bold uppercase tracking-wider text-slate-400 px-2 py-1">
            Select Calibration Outbreak
          </span>

          {historicalVariants.map((v) => {
            const isSelected = v.id === selectedVariantId;
            return (
              <div
                key={v.id}
                onClick={() => setSelectedVariantId(v.id)}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col gap-1.5 ${
                  isSelected
                    ? 'bg-teal-50 border-teal-300 shadow-2xs'
                    : 'bg-white border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <h4 className="font-headline font-bold text-xs text-slate-900">
                    {v.name}
                  </h4>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    isSelected ? 'bg-[#0d3b36] text-white' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {v.status}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500 font-mono">
                  <span>Period: {v.wavePeriod}</span>
                  <span className="font-bold text-teal-800">MAPE: {v.mapeError} (Fit: {v.modelFitAccuracy})</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column: Deep Calibration Details */}
        <div className="lg:col-span-7 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <span className="text-[10px] font-mono font-bold text-teal-700 uppercase">
                CALIBRATION DOSSIER
              </span>
              <h3 className="font-headline font-bold text-lg text-slate-900">
                {currentVariant.name}
              </h3>
            </div>
            <span className="text-xs font-mono font-bold bg-slate-100 px-2.5 py-1 rounded-md text-slate-700">
              Wave: {currentVariant.wavePeriod}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-[10px] text-slate-400 font-bold block mb-1">Actual Observed Peak</span>
              <span className="font-mono text-base font-bold text-slate-900">{currentVariant.actualPeakCases}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-[10px] text-slate-400 font-bold block mb-1">PINN Model Prediction</span>
              <span className="font-mono text-base font-bold text-teal-700">{currentVariant.predictedPeakCases}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-[10px] text-slate-400 font-bold block mb-1">Peak Timing Variance</span>
              <span className="font-mono text-base font-bold text-emerald-700">{currentVariant.peakDayVariance}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-[10px] text-slate-400 font-bold block mb-1">Observed vs Modeled R₀</span>
              <span className="font-mono text-base font-bold text-[#0d3b36]">{currentVariant.r0Real} vs {currentVariant.r0Predicted}</span>
            </div>
          </div>

          {/* Graphical Representation Bar */}
          <div className="space-y-2 pt-2">
            <span className="text-xs font-bold text-slate-600 block">Concordance Ratio vs Ground Truth</span>
            <div className="w-full bg-slate-100 h-3 rounded-full overflow-hidden flex">
              <div className="bg-[#0d3b36] h-full" style={{ width: currentVariant.modelFitAccuracy }} />
              <div className="bg-slate-300 h-full flex-1" />
            </div>
            <div className="flex justify-between text-[11px] font-mono text-slate-500">
              <span>Model Fit Accuracy: {currentVariant.modelFitAccuracy}</span>
              <span>MAPE Error Rate: {currentVariant.mapeError}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
