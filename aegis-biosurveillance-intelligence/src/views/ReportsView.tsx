import React, { useState, useEffect } from 'react';
import { 
  Printer, 
  Download, 
  FileCheck, 
  ShieldCheck, 
  AlertTriangle, 
  QrCode, 
  Dna, 
  Activity,
  Calendar,
  Building,
  UserCheck,
  RefreshCw
} from 'lucide-react';
import { StateOutbreakData, SimulationState } from '../types';
import { fetchCovidData, CovidApiResponse, STATE_CODE_MAP } from '../utils/covidApi';

interface ReportsViewProps {
  simState: SimulationState;
  onPrint: () => void;
  onOpenTerms: () => void;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  simState,
  onPrint,
  onOpenTerms,
}) => {
  const [covidData, setCovidData] = useState<CovidApiResponse>({});
  const [loading, setLoading] = useState(false);
  const [lastFetched, setLastFetched] = useState<string | null>(null);

  const loadRealData = async () => {
    setLoading(true);
    try {
      const data = await fetchCovidData();
      setCovidData(data);
      setLastFetched(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Failed to load COVID data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRealData();
  }, []);

  // Get latest date from the time series
  const getLatestData = (stateCode: string) => {
    const stateData = covidData[stateCode];
    if (!stateData) return null;
    
    // The API returns time series, get the latest date
    const dates = Object.keys(stateData).filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d));
    if (dates.length === 0) return null;
    
    const latestDate = dates[dates.length - 1];
    return stateData[latestDate];
  };

  return (
    <div className="flex flex-col w-full gap-6">
      {/* Top Action Bar (hidden in print) */}
      <div className="no-print bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
              <span className="p-1 rounded bg-teal-100 text-teal-800 text-xs font-mono font-bold">
                EPIDEMIC REPORT
              </span>
              {lastFetched && (
                <span className="text-xs text-slate-500 font-mono">
                  Last updated: {lastFetched}
                </span>
              )}
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-[#0d3b36]">
            EpiPulse Epidemiologic Intelligence Report
          </h1>
          <p className="text-xs text-slate-500 font-body">
            Real-time epidemiological data from COVID-19 India API + simulation model
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={loadRealData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Data</span>
          </button>
          <button
            type="button"
            onClick={onPrint}
            id="print-pdf-button"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#0d3b36] hover:bg-[#082623] text-white text-xs font-headline font-bold shadow-md hover:shadow transition-all cursor-pointer"
          >
            <Printer className="w-4 h-4" />
            <span>Print as PDF</span>
          </button>
          <button
            type="button"
            onClick={onOpenTerms}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
            <span>Disclaimer</span>
          </button>
        </div>
      </div>

      {/* PRINTABLE DOSSIER SHEET */}
      <article className="bg-white rounded-2xl p-6 sm:p-10 border border-slate-200/80 shadow-sm print-exact flex flex-col gap-6 text-slate-800 font-body">
        {/* Dossier Header */}
        <div className="border-b-2 border-[#0d3b36] pb-5 flex flex-col sm:flex-row justify-between items-start gap-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-[#0d3b36] text-white flex items-center justify-center shrink-0 shadow-xs">
              <ShieldCheck className="w-7 h-7 text-teal-300" />
            </div>
            <div>
              <span className="text-[10px] font-headline font-bold uppercase tracking-widest text-teal-800">
                EPIDEMIC RESPONSE REPORT
              </span>
              <h2 className="font-headline font-extrabold text-xl sm:text-2xl text-slate-900 leading-tight">
                EpiPulse Epidemiologic Intelligence Report
              </h2>
              <p className="text-xs text-slate-500 font-mono">
                Report Serial: EP-IND-2026-T{simState.day}-PDF
              </p>
            </div>
          </div>

          <div className="flex flex-col text-left sm:text-right font-mono text-xs text-slate-600">
            <div><strong>Date of Issuance:</strong> {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</div>
            <div><strong>Simulation Day:</strong> {simState.day} of 90</div>
            <div><strong>Sovereign Domain:</strong> Republic of India (28S/8UT)</div>
          </div>
        </div>

        {/* Executive Summary */}
        <section className="space-y-2">
          <h3 className="font-headline font-bold text-sm uppercase tracking-wider text-[#0d3b36] flex items-center gap-2">
            <FileCheck className="w-4 h-4 text-teal-700" />
            <span>1. Executive Epidemiologic Assessment</span>
          </h3>
          <p className="text-xs text-slate-700 leading-relaxed">
            The SEIR ensemble model indicates national active infections currently stand at{' '}
            <strong>{(simState.totalInfected / 1000000).toFixed(2)}M individuals</strong> with an effective reproduction index of{' '}
            <strong>R(t) = {simState.currentRt}</strong>. Hospital ICU load is monitored at <strong>{simState.containmentIndex}%</strong> containment index. 
            Current countermeasure efficacy stands at <strong>{simState.countermeasureEfficacy}%</strong> transmission reduction based on deployed interventions.
          </p>
        </section>

        {/* State Surveillance Table */}
        <section className="space-y-3">
          <h3 className="font-headline font-bold text-sm uppercase tracking-wider text-[#0d3b36] flex items-center gap-2">
            <Building className="w-4 h-4 text-teal-700" />
            <span>2. State & Regional Bio-Surveillance Matrix</span>
          </h3>

          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-headline font-bold">
                  <th className="py-2.5 px-3">State / UT</th>
                  <th className="py-2.5 px-3">Active Cases</th>
                  <th className="py-2.5 px-3">Recovered</th>
                  <th className="py-2.5 px-3">Deaths</th>
                  <th className="py-2.5 px-3">R(t) Sim</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {simState.states.map((st) => {
                  const stateCode = STATE_CODE_MAP[st.name];
                  const realData = stateCode ? getLatestData(stateCode) : null;
                  return (
                    <tr key={st.id} className="hover:bg-slate-50/50">
                      <td className="py-2 px-3 font-semibold text-slate-900 font-body">
                        {st.name}
                      </td>
                      <td className="py-2 px-3 font-bold text-slate-800">
                        {realData?.total?.cases ? realData.total.cases.toLocaleString() : st.infected.toLocaleString()}
                        {realData?.total?.cases && <span className="text-[9px] text-slate-400 ml-1">LIVE</span>}
                      </td>
                      <td className="py-2 px-3 text-emerald-700">
                        {realData?.total?.recovered ? realData.total.recovered.toLocaleString() : '—'}
                      </td>
                      <td className="py-2 px-3 text-red-600">
                        {realData?.total?.deceased ? realData.total.deceased.toLocaleString() : '—'}
                      </td>
                      <td className="py-2 px-3 font-bold">
                        <span className={st.activeRt > 1.2 ? 'text-red-600' : 'text-emerald-700'}>
                          {st.activeRt}
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                            st.status === 'critical'
                              ? 'bg-red-100 text-red-700'
                              : st.status === 'monitored'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-emerald-100 text-emerald-800'
                          }`}
                        >
                          {st.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* Countermeasures & Pathogen */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <h4 className="font-headline font-bold text-xs uppercase text-[#0d3b36] flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-teal-700" />
              <span>3. Active Countermeasures ({simState.countermeasures.filter(c => c.deployed).length} deployed)</span>
            </h4>
            <ul className="text-xs text-slate-600 space-y-1 font-body">
              {simState.countermeasures.filter(c => c.deployed).map(cm => (
                <li key={cm.id}>• <strong>{cm.name}:</strong> {cm.target} — Est. -{cm.efficacy}% transmission.</li>
              ))}
              {simState.countermeasures.filter(c => c.deployed).length === 0 && (
                <li>No countermeasures currently deployed.</li>
              )}
            </ul>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <h4 className="font-headline font-bold text-xs uppercase text-[#0d3b36] flex items-center gap-1.5">
              <Dna className="w-4 h-4 text-teal-700" />
              <span>4. Pathogen Parameters</span>
            </h4>
            <ul className="text-xs text-slate-600 space-y-1 font-body">
              <li>• <strong>Target Pathogen:</strong> {simState.targetPathogen.toUpperCase().replace(/-/g, ' ')}</li>
              <li>• <strong>Infectivity:</strong> {simState.infectivity}% | <strong>Severity:</strong> {simState.severity}% | <strong>Lethality:</strong> {simState.lethality}%</li>
              <li>• <strong>DNA Points Accumulated:</strong> {simState.dnaPoints} (mutation capacity)</li>
            </ul>
          </div>
        </section>

        {/* Disclaimer */}
        <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-300/80 text-xs text-amber-950 space-y-1.5 print-exact">
          <div className="flex items-center gap-2 font-headline font-bold text-amber-900">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span className="uppercase tracking-wider">Mandatory Accuracy & Legal Disclaimer</span>
          </div>
          <p className="leading-relaxed font-body text-[11px] text-amber-900/90">
            <strong>NOTICE:</strong> This epidemiologic report combines real-time data from the COVID-19 India API with computational SEIR modeling. While the state-level case data is sourced from genuine surveillance reports, the SEIR projections are simulation-based estimates intended for research and scenario evaluation. Results may not reflect actual current conditions. This dossier does not replace official clinical diagnoses or statutory advisories from ICMR or NDMA.
          </p>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 text-xs font-mono text-slate-500">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center text-[#0d3b36]">
              <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" className="text-teal-600" />
              </svg>
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-slate-800">EpiPulse Simulation Engine</span>
              <span>Data: COVID-19 India API | Model: SEIR Ensemble v2.0</span>
              <span className="text-[10px] text-teal-800">Session: EP-IND-2026-T{simState.day}</span>
            </div>
          </div>

          <div className="flex flex-col text-left sm:text-right text-[10px]">
            <span>GENERATED BY EPIPULSE SIMULATION ENGINE v2.0</span>
            <span>RESEARCH USE ONLY — NOT A CLINICAL DIAGNOSIS</span>
          </div>
        </div>
      </article>
    </div>
  );
};
