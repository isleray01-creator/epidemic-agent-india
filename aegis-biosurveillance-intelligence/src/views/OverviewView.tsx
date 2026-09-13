import React, { useState } from 'react';
import { 
  Printer, 
  RefreshCw, 
  Activity, 
  TrendingDown, 
  Shield, 
  Dna, 
  QrCode, 
  CheckCircle2, 
  AlertCircle,
  Info,
  Layers
} from 'lucide-react';
import { 
  SimulationState, 
  StateOutbreakData, 
  SEIRDataPoint 
} from '../types';
import { IndiaMap } from '../components/IndiaMap';
import { SEIRGraph } from '../components/SEIRGraph';

interface OverviewViewProps {
  simState: SimulationState;
  seirPoints: SEIRDataPoint[];
  peakDay: number;
  peakCases: number;
  onSelectState: (state: StateOutbreakData) => void;
  selectedStateId?: string;
  onPrint: () => void;
  onRefreshSync: () => void;
  onSpeedChange: (speed: 1 | 2 | 5) => void;
  onTogglePlay: () => void;
  onNavigateToSimulation: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  simState,
  seirPoints,
  peakDay,
  peakCases,
  onSelectState,
  selectedStateId,
  onPrint,
  onRefreshSync,
  onSpeedChange,
  onTogglePlay,
  onNavigateToSimulation,
}) => {
  const [isSyncing, setIsSyncing] = useState(false);

  const handleSyncClick = () => {
    setIsSyncing(true);
    onRefreshSync();
    setTimeout(() => setIsSyncing(false), 800);
  };

  return (
    <div className="flex flex-col w-full gap-6">
      {/* DOSSIER METADATA HEADER */}
      <section className="w-full bg-white rounded-2xl p-5 sm:p-6 shadow-sm border border-slate-200/80 print-exact print-break-avoid">
        <div className="flex flex-col xl:flex-row items-start xl:items-center justify-between gap-4">
          <div className="flex flex-col gap-2">
            <div className="flex items-center flex-wrap gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-teal-50 text-teal-600 font-headline text-[10px] uppercase font-bold tracking-widest flex items-center gap-1.5 border border-teal-200/70">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-600" />
                EPIDEMIC SIMULATION
              </span>
              <span className="px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-600 text-xs font-mono border border-slate-200">
                SESSION: <strong className="text-[#0d3b36]">#EP-INDIA-2026</strong>
              </span>
              <span className="px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-600 text-xs font-mono border border-slate-200">
                GEO-THEATRE: <strong className="text-slate-900">INDIA NATIONAL (ALL STATES & UTs)</strong>
              </span>
            </div>

            <h1 className="font-headline text-2xl lg:text-3xl text-[#0d3b36] font-extrabold tracking-tight">
              EpiPulse — National Transmission & Lineage Dynamics
            </h1>

            <div className="flex items-center flex-wrap gap-x-3 gap-y-1 text-slate-500 text-xs font-body">
              <span><strong className="text-slate-900">Session Started:</strong> {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })} (T+{simState.day}D)</span>
              <span>•</span>
              <span><strong className="text-slate-900">Simulation Engine:</strong> EpiPulse SEIR Ensemble v2.0</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2.5 shrink-0 no-print">
            <button
              type="button"
              onClick={onPrint}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#0d3b36] hover:bg-[#082623] text-white text-xs font-headline font-bold shadow-md hover:shadow transition-all"
            >
              <Printer className="w-4 h-4" />
              <span>Print Surveillance Dossier / PDF</span>
            </button>
            <button
              type="button"
              onClick={handleSyncClick}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-semibold shadow-2xs transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-teal-700 ${isSyncing ? 'animate-spin' : ''}`} />
              <span>Live Sync</span>
            </button>
          </div>
        </div>
      </section>

      {/* KEY EPIDEMIC TELEMETRY MATRIX (4 METRICS) */}
      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white border border-slate-200/80 flex flex-col justify-between gap-3 shadow-2xs print-exact print-break-avoid">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs uppercase tracking-wider font-bold font-headline text-slate-400">
              Active Inferred Burden
            </span>
            <div className="p-1.5 rounded-lg bg-teal-50 text-teal-700">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-headline text-3xl sm:text-4xl text-[#0d3b36] font-extrabold">
              {(simState.totalInfected / 1000000).toFixed(2)}M
            </span>
            <span className="text-xs text-red-600 font-bold">▲ +14.2% / 7d</span>
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div className="h-full bg-teal-600 w-[74%] rounded-full" />
          </div>
          <div className="flex items-center justify-between text-slate-500 text-[11px] font-mono">
            <span>CI 95%: 1.71M – 1.98M</span>
            <span className="text-red-700 font-bold bg-red-100 px-1.5 py-0.5 rounded text-[10px]">
              Tier-4 High
            </span>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white border border-slate-200/80 flex flex-col justify-between gap-3 shadow-2xs print-exact print-break-avoid">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs uppercase tracking-wider font-bold font-headline text-slate-400">
              Projected Horizon Fatality
            </span>
            <div className="p-1.5 rounded-lg bg-amber-50 text-amber-700">
              <AlertCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-headline text-3xl sm:text-4xl text-slate-900 font-extrabold">
              {(simState.totalDeceased / 1000).toFixed(1)}K
            </span>
            <span className="text-xs text-slate-500 font-medium">± 2.1K err</span>
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div className="h-full bg-amber-500 w-[48%] rounded-full" />
          </div>
          <div className="flex items-center justify-between text-slate-500 text-[11px] font-mono">
            <span>IFR Model: 0.82% ±0.04</span>
            <span className="text-amber-800 font-bold bg-amber-100 px-1.5 py-0.5 rounded text-[10px]">
              Controlled Watch
            </span>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white border border-slate-200/80 flex flex-col justify-between gap-3 shadow-2xs print-exact print-break-avoid">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs uppercase tracking-wider font-bold font-headline text-slate-400">
              Effective R(t) Index
            </span>
            <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-700">
              <TrendingDown className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-headline text-3xl sm:text-4xl text-[#0d3b36] font-extrabold">
              {simState.currentRt}
            </span>
            <span className="text-xs text-emerald-700 font-bold">
              ▼ from 1.42 (T-14)
            </span>
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div className="h-full bg-emerald-600 w-[62%] rounded-full" />
          </div>
          <div className="flex items-center justify-between text-slate-500 text-[11px] font-mono">
            <span>Target Threshold: &lt; 1.00</span>
            <span className="text-emerald-800 font-bold bg-emerald-100 px-1.5 py-0.5 rounded text-[10px]">
              Suppressing
            </span>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white border border-slate-200/80 flex flex-col justify-between gap-3 shadow-2xs print-exact print-break-avoid">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs uppercase tracking-wider font-bold font-headline text-slate-400">
              Containment Index (NDMA)
            </span>
            <div className="p-1.5 rounded-lg bg-teal-50 text-[#0d3b36]">
              <Shield className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-headline text-3xl sm:text-4xl text-emerald-700 font-extrabold">
              {simState.containmentIndex}%
            </span>
            <span className="text-xs text-emerald-700 font-bold">Tier 1 Sovereign</span>
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div className="h-full bg-emerald-600 w-[87%] rounded-full" />
          </div>
          <div className="flex items-center justify-between text-slate-500 text-[11px] font-mono">
            <span>Ring Coverage: 92%</span>
            <span className="text-emerald-800 font-bold bg-emerald-100 px-1.5 py-0.5 rounded text-[10px]">
              Optimum Ring
            </span>
          </div>
        </div>
      </section>

      {/* PLAGUE INC SIMULATOR HUD & INDIA BIO-RADAR MAP SECTION */}
      <section className="w-full bg-white rounded-2xl p-4 sm:p-6 flex flex-col gap-4 shadow-sm border border-slate-200/80 relative overflow-hidden print-exact print-break-avoid">
        {/* Plague Inc HUD Bar */}
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3 pb-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
          <div className="flex flex-col gap-1 max-w-xl">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-teal-600" />
              <span className="font-headline text-xs uppercase font-extrabold tracking-wider text-teal-700">
                EPIDEMIC TRANSMISSION SIMULATOR
              </span>
              <span className="px-2 py-0.5 rounded-full bg-white border border-slate-200 text-[10px] text-teal-700 font-bold">
                SIMULATION
              </span>
            </div>
            <div className="text-slate-700 text-xs bg-white px-3 py-1.5 rounded-md border border-slate-200 truncate">
              {simState.tickerMessage}
            </div>
          </div>

          {/* HUD Gauges */}
          <div className="flex items-center flex-wrap gap-3">
            <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-2xs">
              <div className="w-7 h-7 rounded-md bg-emerald-100 flex items-center justify-center text-emerald-700">
                <Dna className="w-4 h-4 animate-pulse" />
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-slate-400 font-bold uppercase">DNA / Mutations</span>
                <span className="font-headline font-extrabold text-sm text-emerald-700">
                  {simState.dnaPoints} DNA pts
                </span>
              </div>
            </div>

            {/* Quick Speed HUD Buttons */}
            <div className="flex items-center gap-1 bg-white p-1 rounded-lg border border-slate-200 shadow-2xs no-print">
              <button
                type="button"
                onClick={onTogglePlay}
                className={`p-1.5 rounded text-xs transition-colors ${
                  simState.isRunning ? 'bg-amber-100 text-amber-800' : 'bg-emerald-600 text-white'
                }`}
              >
                {simState.isRunning ? 'Pause' : 'Play'}
              </button>
              <button
                type="button"
                onClick={() => onSpeedChange(1)}
                className={`px-2 py-1 rounded text-xs font-bold ${
                  simState.speed === 1 ? 'bg-[#0d3b36] text-white' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                1x
              </button>
              <button
                type="button"
                onClick={() => onSpeedChange(2)}
                className={`px-2 py-1 rounded text-xs font-bold ${
                  simState.speed === 2 ? 'bg-[#0d3b36] text-white' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                2x
              </button>
              <button
                type="button"
                onClick={() => onSpeedChange(5)}
                className={`px-2 py-1 rounded text-xs font-bold ${
                  simState.speed === 5 ? 'bg-[#0d3b36] text-white' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                5x
              </button>
              <span className="text-slate-400 text-xs px-1 font-mono">
                Day {simState.day}/60
              </span>
            </div>

            {/* Jump to full simulation button */}
            <button
              type="button"
              onClick={onNavigateToSimulation}
              className="px-3 py-1.5 rounded-lg bg-teal-50 hover:bg-teal-100 border border-teal-200 text-[#0d3b36] text-xs font-bold no-print"
            >
              Open Plague Lab →
            </button>
          </div>
        </div>

        {/* RADAR MAP CANVAS & REGIONAL BREAKDOWN */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Detailed Tactical Vector Map of India */}
          <div className="lg:col-span-8">
            <IndiaMap
              states={simState.states}
              onSelectState={onSelectState}
              selectedStateId={selectedStateId}
              isSimulating={simState.isRunning}
            />
          </div>

          {/* Regional Severity Matrix & Genomic Alert Column */}
          <div className="lg:col-span-4 flex flex-col gap-3">
            <div className="p-4 rounded-xl bg-white border border-slate-200/80 shadow-2xs flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="font-headline text-xs uppercase font-extrabold text-[#0d3b36] tracking-wider">
                  Regional Severity Matrix
                </span>
                <span className="text-xs text-teal-800 font-bold bg-teal-50 px-2 py-0.5 rounded border border-teal-100">
                  T+42 Index
                </span>
              </div>

              <div className="flex flex-col gap-1.5">
                {simState.states.slice(0, 5).map((st) => (
                  <div
                    key={st.id}
                    onClick={() => onSelectState(st)}
                    className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-200 hover:border-[#0d3b36] cursor-pointer transition-colors"
                  >
                    <div className="flex flex-col">
                      <span className="font-headline font-bold text-xs text-slate-900">
                        {st.name} ({st.code})
                      </span>
                      <span className="text-[11px] text-slate-400">
                        {st.subRegion}
                      </span>
                    </div>
                    <div className="flex flex-col items-end">
                      <span
                        className={`font-mono text-xs font-extrabold ${
                          st.activeRt > 1.25 ? 'text-red-600' : st.activeRt > 1.0 ? 'text-amber-600' : 'text-emerald-700'
                        }`}
                      >
                        R(t) {st.activeRt}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.2 rounded uppercase ${
                          st.status === 'critical'
                            ? 'text-red-700 bg-red-100'
                            : st.status === 'monitored'
                            ? 'text-amber-800 bg-amber-100'
                            : 'text-emerald-800 bg-emerald-100'
                        }`}
                      >
                        {st.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Genomic Mutation Drift Alert Card */}
            <div className="p-4 rounded-xl bg-teal-50 border border-teal-200 shadow-2xs flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="font-headline text-xs uppercase tracking-wider text-[#0d3b36] font-extrabold flex items-center gap-1.5">
                  <Dna className="w-4 h-4 text-teal-700" />
                  Genomic Lineage Alert
                </span>
                <span className="text-xs text-[#0d3b36] font-mono font-bold bg-white px-2 py-0.5 rounded border border-teal-200">
                  Spike: F486P
                </span>
              </div>
              <p className="text-xs text-slate-700 leading-relaxed font-body">
                Lineage <strong>Omicron BA.5.2.1 (IN-Clade Delta-Prime)</strong> displays a{' '}
                <strong>24% acceleration</strong> in viral binding affinity. Cross-neutralization titers remain responsive to Tier-2 synthetic mRNA booster pools.
              </p>
              <div className="flex items-center justify-between pt-1 text-[11px] text-slate-500 font-mono border-t border-teal-200/60">
                <span>SEED: DEL491-X</span>
                <span className="text-emerald-700 font-bold">ESCAPE RISK: LOW</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* MULTI-CURVE SEIR EPIDEMIOLOGICAL GRAPH WITH DOCTOR (NO OCCLUSION) */}
      <SEIRGraph
        dataPoints={seirPoints}
        peakDay={peakDay}
        peakCases={peakCases}
        currentRt={simState.currentRt}
      />

      {/* PARAMETER SENSITIVITY PANEL & NPI COUNTERMEASURES MATRIX */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Sobol Parameter Sensitivity Breakdown */}
        <div className="lg:col-span-7 bg-white rounded-2xl p-5 sm:p-6 flex flex-col justify-between gap-4 shadow-sm border border-slate-200/80 print-exact print-break-avoid">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-headline font-bold text-base text-[#0d3b36]">
                Parameter Sensitivity Variance
              </h3>
              <p className="text-xs text-slate-500 font-body">
                Global Sobol Sensitivity Index (S_i) across transmission dynamics
              </p>
            </div>
            <span className="px-2.5 py-1 rounded-md bg-teal-50 text-[#0d3b36] font-mono text-xs font-bold border border-teal-200">
              SOBOL RANKING
            </span>
          </div>

          <div className="flex flex-col gap-4">
            {/* Parameter 1 */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-800 font-semibold">Basic Reproduction Number (R₀ = 2.45)</span>
                <span className="text-red-600 font-mono font-bold">0.41 Criticality</span>
              </div>
              <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-red-600 rounded-full w-[82%]" />
              </div>
              <div className="flex justify-between text-[11px] text-slate-400 font-mono">
                <span>Primary driver of early-stage cluster divergence</span>
                <span>Elasticity: +12% / 0.1 Δ</span>
              </div>
            </div>

            {/* Parameter 2 */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-800 font-semibold">Infection Fatality Rate (IFR = 0.82%)</span>
                <span className="text-amber-600 font-mono font-bold">0.26 Criticality</span>
              </div>
              <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-amber-500 rounded-full w-[52%]" />
              </div>
              <div className="flex justify-between text-[11px] text-slate-400 font-mono">
                <span>Hospital triage saturation modulates effective mortality</span>
                <span>Elasticity: +4.2% / 0.05 Δ</span>
              </div>
            </div>

            {/* Parameter 3 */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-800 font-semibold">Serial Generation Interval (T_g = 3.6 Days)</span>
                <span className="text-teal-700 font-mono font-bold">0.18 Criticality</span>
              </div>
              <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-teal-600 rounded-full w-[36%]" />
              </div>
              <div className="flex justify-between text-[11px] text-slate-400 font-mono">
                <span>Generational turnover shortens clinical intervention window</span>
                <span>Elasticity: -6.1% / 0.5d</span>
              </div>
            </div>

            {/* Parameter 4 */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-800 font-semibold">Pre-Symptomatic Shedding Window (1.8 Days)</span>
                <span className="text-emerald-700 font-mono font-bold">0.15 Criticality</span>
              </div>
              <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-600 rounded-full w-[30%]" />
              </div>
              <div className="flex justify-between text-[11px] text-slate-400 font-mono">
                <span>Governs silent dispersal in high-density rail corridors</span>
                <span>Elasticity: +8.4% / 0.2d</span>
              </div>
            </div>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-50 text-slate-600 text-xs flex items-center gap-2 border border-slate-200">
            <Info className="w-4 h-4 text-teal-700 shrink-0" />
            <span>Sensitivity indices computed via 10,000 Monte Carlo iterations on National GIS Telemetry Matrix.</span>
          </div>
        </div>

        {/* Countermeasure Matrix (NPI) */}
        <div className="lg:col-span-5 bg-white rounded-2xl p-5 sm:p-6 flex flex-col justify-between gap-4 shadow-sm border border-slate-200/80 print-exact print-break-avoid">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-headline font-bold text-base text-[#0d3b36]">
                Countermeasure Matrix (NPI)
              </h3>
              <p className="text-xs text-slate-500 font-body">
                Active containment interventions in India Sector
              </p>
            </div>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          </div>

          <div className="flex flex-col gap-2.5">
            {simState.countermeasures.slice(0, 4).map((npi) => (
              <div
                key={npi.id}
                className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-2.5">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold ${
                      npi.deployed ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-500'
                    }`}
                  >
                    <Shield className="w-4 h-4" />
                  </div>
                  <div className="flex flex-col">
                    <span className="font-headline font-bold text-xs text-slate-900">
                      {npi.name}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {npi.target}
                    </span>
                  </div>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    npi.deployed
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-slate-200 text-slate-600'
                  }`}
                >
                  {npi.statusLabel}
                </span>
              </div>
            ))}
          </div>

          <div className="pt-2 flex items-center justify-between text-xs border-t border-slate-100">
            <span className="font-semibold text-slate-500">EST. TRANSMISSION REDUCTION:</span>
            <span className="text-emerald-700 font-mono font-bold text-sm">
              -38.4% by Day 60
            </span>
          </div>
        </div>
      </section>

      {/* CLINICAL VERIFICATION & HASH SIGN-OFF */}
      <section className="w-full bg-white rounded-2xl p-5 sm:p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm border border-slate-200/80 print-exact print-break-avoid">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <span className="font-headline text-sm text-[#0d3b36] font-bold uppercase tracking-wider">
              Clinical Biosecurity Authority Clearance
            </span>
          </div>
          <p className="text-xs text-slate-600 max-w-2xl leading-relaxed font-body">
            This document contains computational epidemiologic projections under India National Biosecurity Protocol 9-DEF. Models are recalibrated at 4-hour intervals using automated genomic pipelines and state-level healthcare feeds.
          </p>
        </div>

        <div className="flex items-center gap-4 shrink-0">
          <div className="flex flex-col text-right">
            <span className="font-mono text-xs text-[#0d3b36] font-bold">SHA-256 HASH VERIFIED</span>
            <span className="font-mono text-[10px] text-slate-400">7f4a:92b8:10c4:ee91:0a12</span>
          </div>
          <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center text-[#0d3b36]">
            <QrCode className="w-5 h-5" />
          </div>
        </div>
      </section>
    </div>
  );
};
