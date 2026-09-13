import React, { useState } from 'react';
import { 
  SimulationState, 
  StateOutbreakData, 
  SEIRDataPoint 
} from '../types';
import { IndiaMap } from '../components/IndiaMap';
import { PlagueIncHUD } from '../components/PlagueIncHUD';
import { SEIRGraph } from '../components/SEIRGraph';
import { simulateSEIR } from '../utils/backendApi';
import { Activity, ShieldAlert, Sparkles, Building2, Train, Plane, Cpu } from 'lucide-react';

interface SimulationViewProps {
  simState: SimulationState;
  seirPoints: SEIRDataPoint[];
  peakDay: number;
  peakCases: number;
  onTogglePlay: () => void;
  onChangeSpeed: (speed: 1 | 2 | 5) => void;
  onReset: () => void;
  onStepDay: () => void;
  onToggleTrait: (traitId: string) => void;
  onToggleCountermeasure: (cmId: string) => void;
  onSelectState: (state: StateOutbreakData) => void;
  selectedStateId?: string;
}

export const SimulationView: React.FC<SimulationViewProps> = ({
  simState,
  seirPoints,
  peakDay,
  peakCases,
  onTogglePlay,
  onChangeSpeed,
  onReset,
  onStepDay,
  onToggleTrait,
  onToggleCountermeasure,
  onSelectState,
  selectedStateId,
}) => {
  const selectedState = simState.states.find((s) => s.id === selectedStateId) || simState.states[0];
  const [backendLoading, setBackendLoading] = useState(false);
  const [backendResult, setBackendResult] = useState<string | null>(null);

  const handleRunBackend = async () => {
    setBackendLoading(true);
    setBackendResult(null);
    try {
      const result = await simulateSEIR({
        states: simState.states.map(s => s.name),
        variant: 'wildtype',
        days: 90,
        initial_infected: 100,
      });
      const totalCases = Object.values(result.cumulative_cases).reduce(
        (sum, cases) => sum + (cases[cases.length - 1] || 0), 0
      );
      const totalDeaths = Object.values(result.cumulative_deaths || {}).reduce(
        (sum, deaths) => sum + (deaths[deaths.length - 1] || 0), 0
      );
      setBackendResult(`Backend SEIR complete: ${totalCases.toLocaleString()} total cases, ${totalDeaths.toLocaleString()} deaths across ${Object.keys(result.cumulative_cases).length} states.`);
    } catch (err) {
      setBackendResult(`Backend unavailable: ${err instanceof Error ? err.message : 'Connection failed'}. Running client-side simulation.`);
    } finally {
      setBackendLoading(false);
    }
  };

  return (
    <div className="flex flex-col w-full gap-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-teal-600" />
            <span className="text-xs font-mono font-bold text-teal-700 uppercase tracking-widest">
              EPIDEMIC SIMULATION ENGINE // ACTIVE
            </span>
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-[#0d3b36]">
            Transmission Laboratory — India Geo-Theatre
          </h1>
          <p className="text-xs text-slate-500 font-body">
            Dynamic compartmental simulation where infection parameters, mutations, and non-pharmaceutical interventions reshape transmission curves across all Indian states in real time.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-mono bg-slate-50 px-3 py-2 rounded-xl border border-slate-200">
            <span className="text-slate-500">DYNAMIC R(t):</span>
            <span className={`font-extrabold text-sm ${simState.currentRt > 1.2 ? 'text-red-600' : 'text-emerald-700'}`}>
              {simState.currentRt}
            </span>
          </div>
          <button
            onClick={handleRunBackend}
            disabled={backendLoading}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wider border transition-all ${
              backendLoading
                ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-wait'
                : 'bg-teal-600 text-white border-teal-700 hover:bg-teal-700 cursor-pointer'
            }`}
          >
            <Cpu className={`w-3.5 h-3.5 ${backendLoading ? 'animate-spin' : ''}`} />
            {backendLoading ? 'Running...' : 'Run Python Backend'}
          </button>
        </div>
      </div>

      {/* Backend Result Banner */}
      {backendResult && (
        <div className="bg-teal-50 border border-teal-200 rounded-xl px-4 py-3 text-xs font-mono text-teal-800">
          {backendResult}
        </div>
      )}

      {/* PLAGUE INC HUD & MUTATION / NPI CONTROLS */}
      <PlagueIncHUD
        day={simState.day}
        maxDays={simState.maxDays}
        isRunning={simState.isRunning}
        speed={simState.speed}
        dnaPoints={simState.dnaPoints}
        infectivity={simState.infectivity}
        severity={simState.severity}
        lethality={simState.lethality}
        tickerMessage={simState.tickerMessage}
        traits={simState.traits}
        countermeasures={simState.countermeasures}
        onTogglePlay={onTogglePlay}
        onChangeSpeed={onChangeSpeed}
        onReset={onReset}
        onStepDay={onStepDay}
        onToggleTrait={onToggleTrait}
        onToggleCountermeasure={onToggleCountermeasure}
      />

      {/* MAP & SELECTED REGIONAL TELEMETRY INSPECTOR */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Real India Vector Map */}
        <div className="lg:col-span-8 bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between mb-3 border-b border-slate-100 pb-2">
            <span className="font-headline font-bold text-sm text-[#0d3b36]">
              Real-Time Tactical Geographic Outbreak Map
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Click any state node to inspect regional ICU & hospital capacity
            </span>
          </div>
          <IndiaMap
            states={simState.states}
            onSelectState={onSelectState}
            selectedStateId={selectedStateId}
            isSimulating={simState.isRunning}
          />
        </div>

        {/* Selected Regional Hub Telemetry Card */}
        <div className="lg:col-span-4 flex flex-col gap-4">
          <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <span className="text-[10px] text-slate-400 font-bold uppercase font-mono">
                  REGIONAL BIO-SENSOR TELEMETRY
                </span>
                <h3 className="font-headline font-bold text-base text-slate-900">
                  {selectedState.name} ({selectedState.code})
                </h3>
              </div>
              <span
                className={`px-2.5 py-1 rounded-md text-xs font-bold uppercase ${
                  selectedState.status === 'critical'
                    ? 'bg-red-100 text-red-700'
                    : selectedState.status === 'monitored'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-emerald-100 text-emerald-700'
                }`}
              >
                {selectedState.status}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold block mb-0.5">Active Infected</span>
                <strong className="text-base text-[#0d3b36] font-mono">
                  {selectedState.infected.toLocaleString()}
                </strong>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold block mb-0.5">Effective R(t)</span>
                <strong
                  className={`text-base font-mono ${
                    selectedState.activeRt > 1.2 ? 'text-red-600' : 'text-emerald-700'
                  }`}
                >
                  {selectedState.activeRt}
                </strong>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold block mb-0.5">Hospital ICU Load</span>
                <strong className="text-base text-slate-900 font-mono">
                  {selectedState.hospitalBedLoad}%
                </strong>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 font-bold block mb-0.5">Population</span>
                <strong className="text-base text-slate-900 font-mono">
                  {(selectedState.population / 1000000).toFixed(1)}M
                </strong>
              </div>
            </div>

            {/* Hub Transit Connections */}
            <div className="space-y-2 pt-1 border-t border-slate-100">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                Transit Vector Corridors
              </span>
              <div className="flex items-center gap-2 text-xs text-slate-700">
                <Plane className="w-4 h-4 text-teal-700" />
                <span>Major International Air Hub: <strong>{selectedState.airHub ? 'Active Bio-Triage' : 'Secondary Feeder'}</strong></span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-700">
                <Train className="w-4 h-4 text-amber-600" />
                <span>Express Railway Junction: <strong>{selectedState.railJunction ? 'High Vector Flow' : 'Local Spur'}</strong></span>
              </div>
            </div>
          </div>

          {/* Plague Inc Tips Callout */}
          <div className="p-4 rounded-2xl bg-teal-50 border border-teal-200 text-xs text-slate-700 space-y-2">
            <div className="flex items-center gap-2 font-headline font-bold text-[#0d3b36]">
              <Sparkles className="w-4 h-4 text-teal-700" />
              <span>Plague Inc Dynamics Rules</span>
            </div>
            <p className="leading-relaxed font-body">
              • Evolving <strong>Aerosol Plumes</strong> or <strong>Express Rail Adaptation</strong> boosts infectivity, increasing R(t) and accelerating inter-state spread.
            </p>
            <p className="leading-relaxed font-body">
              • Deploying <strong>Metropolitan Mask Mandates</strong> or <strong>Ring Immunization</strong> dampens transmission, flattening the curve peak.
            </p>
          </div>
        </div>
      </div>

      {/* DYNAMIC SHIFTING SEIR GRAPH */}
      <SEIRGraph
        dataPoints={seirPoints}
        peakDay={peakDay}
        peakCases={peakCases}
        currentRt={simState.currentRt}
      />
    </div>
  );
};
