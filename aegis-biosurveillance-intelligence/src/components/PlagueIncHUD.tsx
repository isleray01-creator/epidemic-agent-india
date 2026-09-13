import React, { useState } from 'react';
import { 
  Dna, 
  Play, 
  Pause, 
  FastForward, 
  RotateCcw, 
  Wind, 
  Plane, 
  Train, 
  Hand, 
  Flame, 
  Activity, 
  Zap, 
  ShieldAlert, 
  EyeOff, 
  Megaphone,
  Plus,
  Minus,
  Sparkles
} from 'lucide-react';
import { SimulationTrait, CountermeasureItem } from '../types';

interface PlagueIncHUDProps {
  day: number;
  maxDays: number;
  isRunning: boolean;
  speed: 1 | 2 | 5;
  dnaPoints: number;
  infectivity: number;
  severity: number;
  lethality: number;
  tickerMessage: string;
  traits: SimulationTrait[];
  countermeasures: CountermeasureItem[];
  onTogglePlay: () => void;
  onChangeSpeed: (speed: 1 | 2 | 5) => void;
  onReset: () => void;
  onStepDay: () => void;
  onToggleTrait: (traitId: string) => void;
  onToggleCountermeasure: (cmId: string) => void;
}

export const PlagueIncHUD: React.FC<PlagueIncHUDProps> = ({
  day,
  maxDays,
  isRunning,
  speed,
  dnaPoints,
  infectivity,
  severity,
  lethality,
  tickerMessage,
  traits,
  countermeasures,
  onTogglePlay,
  onChangeSpeed,
  onReset,
  onStepDay,
  onToggleTrait,
  onToggleCountermeasure,
}) => {
  const [activeTab, setActiveTab] = useState<'transmission' | 'symptoms' | 'abilities' | 'countermeasures'>('transmission');

  // Helper icon map
  const getTraitIcon = (name: string) => {
    switch (name) {
      case 'wind': return <Wind className="w-4 h-4" />;
      case 'plane': return <Plane className="w-4 h-4" />;
      case 'train': return <Train className="w-4 h-4" />;
      case 'hand': return <Hand className="w-4 h-4" />;
      case 'flame': return <Flame className="w-4 h-4" />;
      case 'activity': return <Activity className="w-4 h-4" />;
      case 'zap': return <Zap className="w-4 h-4" />;
      case 'shield-alert': return <ShieldAlert className="w-4 h-4" />;
      case 'eye-off': return <EyeOff className="w-4 h-4" />;
      default: return <Dna className="w-4 h-4" />;
    }
  };

  const filteredTraits = traits.filter((t) => t.category === activeTab);

  return (
    <div className="w-full bg-white rounded-2xl p-4 sm:p-5 shadow-sm border border-slate-200/80 flex flex-col gap-4">
      {/* HUD Header Bar: Outbreak Ticker & Status Gauges */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
        {/* News Ticker & Live Indicator */}
        <div className="flex flex-col gap-1.5 w-full lg:max-w-xl">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="w-2.5 h-2.5 rounded-full bg-teal-600" />
            <span className="font-headline text-xs uppercase font-extrabold tracking-wider text-teal-700">
              EPIDEMIC TRANSMISSION SIMULATOR
            </span>
            <span className="px-2 py-0.5 rounded-full bg-white border border-slate-200 text-[10px] text-teal-700 font-bold">
              SIMULATION
            </span>
          </div>

          <div className="flex items-center gap-2 text-slate-700 text-xs bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-2xs">
            <Megaphone className="w-4 h-4 text-amber-500 shrink-0" />
            <span className="truncate font-medium text-slate-700">
              {tickerMessage}
            </span>
          </div>
        </div>

        {/* Plague Inc Gauges: DNA Points, Infectivity, Severity, Lethality & Speed Controls */}
        <div className="flex items-center flex-wrap gap-4 w-full lg:w-auto justify-between lg:justify-end">
          {/* DNA Points Capsule */}
          <div className="flex items-center gap-2.5 bg-white px-3.5 py-1.5 rounded-xl border border-slate-200 shadow-2xs">
            <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <Dna className="w-4 h-4 animate-pulse" />
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">DNA Points</span>
              <span className="font-headline font-extrabold text-sm sm:text-base text-emerald-700">
                {dnaPoints} DNA
              </span>
            </div>
          </div>

          {/* Infectivity */}
          <div className="flex flex-col gap-1 w-20 sm:w-24">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500 font-semibold text-[11px]">Infectivity</span>
              <span className="text-teal-700 font-bold font-mono">{infectivity}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-teal-600 rounded-full transition-all duration-300" style={{ width: `${infectivity}%` }} />
            </div>
          </div>

          {/* Severity */}
          <div className="flex flex-col gap-1 w-20 sm:w-24">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500 font-semibold text-[11px]">Severity</span>
              <span className="text-amber-600 font-bold font-mono">{severity}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-amber-500 rounded-full transition-all duration-300" style={{ width: `${severity}%` }} />
            </div>
          </div>

          {/* Lethality */}
          <div className="flex flex-col gap-1 w-20 sm:w-24">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500 font-semibold text-[11px]">Lethality</span>
              <span className="text-red-600 font-bold font-mono">{lethality}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-red-600 rounded-full transition-all duration-300" style={{ width: `${lethality}%` }} />
            </div>
          </div>

          {/* Playback Controls */}
          <div className="flex items-center gap-1 bg-white p-1 rounded-lg border border-slate-200 shadow-2xs">
            <button
              type="button"
              onClick={onTogglePlay}
              className={`p-1.5 rounded transition-colors ${
                isRunning ? 'bg-amber-100 text-amber-800' : 'bg-emerald-600 text-white'
              }`}
              title={isRunning ? 'Pause Simulation' : 'Run Simulation'}
            >
              {isRunning ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            </button>

            <button
              type="button"
              onClick={() => onChangeSpeed(1)}
              className={`px-2 py-1 rounded text-xs font-bold transition-colors ${
                speed === 1 ? 'bg-[#0d3b36] text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              1x
            </button>
            <button
              type="button"
              onClick={() => onChangeSpeed(2)}
              className={`px-2 py-1 rounded text-xs font-bold transition-colors ${
                speed === 2 ? 'bg-[#0d3b36] text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              2x
            </button>
            <button
              type="button"
              onClick={() => onChangeSpeed(5)}
              className={`px-2 py-1 rounded text-xs font-bold transition-colors ${
                speed === 5 ? 'bg-[#0d3b36] text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              5x
            </button>

            <button
              type="button"
              onClick={onStepDay}
              className="p-1.5 rounded text-slate-600 hover:bg-slate-100 text-xs font-bold"
              title="Step +1 Day"
            >
              <FastForward className="w-3.5 h-3.5" />
            </button>

            <button
              type="button"
              onClick={onReset}
              className="p-1.5 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100"
              title="Reset Simulation"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>

            <span className="text-slate-500 text-xs px-2 font-mono font-semibold border-l border-slate-200">
              Day {day}/{maxDays}
            </span>
          </div>
        </div>
      </div>

      {/* Plague Inc Dynamic Mutation & Countermeasures Tree */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-200 pb-2">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-teal-600" />
            <span className="font-headline font-bold text-xs uppercase tracking-wider text-slate-900">
              Epidemiologic Variables & Containment Tree
            </span>
          </div>

          {/* Category Tabs */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
            <button
              type="button"
              onClick={() => setActiveTab('transmission')}
              className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${
                activeTab === 'transmission' ? 'bg-white text-[#0d3b36] shadow-2xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Transmission ({traits.filter(t => t.category === 'transmission' && t.unlocked).length}/{traits.filter(t => t.category === 'transmission').length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('symptoms')}
              className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${
                activeTab === 'symptoms' ? 'bg-white text-[#0d3b36] shadow-2xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Symptoms ({traits.filter(t => t.category === 'symptoms' && t.unlocked).length}/{traits.filter(t => t.category === 'symptoms').length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('abilities')}
              className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${
                activeTab === 'abilities' ? 'bg-white text-[#0d3b36] shadow-2xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Abilities / Drift ({traits.filter(t => t.category === 'abilities' && t.unlocked).length}/{traits.filter(t => t.category === 'abilities').length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('countermeasures')}
              className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${
                activeTab === 'countermeasures' ? 'bg-white text-emerald-800 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Countermeasures (NPI) ({countermeasures.filter(c => c.deployed).length}/{countermeasures.length})
            </button>
          </div>
        </div>

        {/* Content based on Active Tab */}
        {activeTab !== 'countermeasures' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {filteredTraits.map((trait) => {
              const canAfford = dnaPoints >= trait.cost || trait.unlocked;

              return (
                <div
                  key={trait.id}
                  className={`p-3 rounded-xl border flex flex-col justify-between gap-2.5 transition-all ${
                    trait.unlocked
                      ? 'bg-teal-50/60 border-teal-300 shadow-2xs'
                      : 'bg-white border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          trait.unlocked
                            ? 'bg-[#0d3b36] text-teal-200'
                            : 'bg-slate-100 text-slate-500'
                        }`}
                      >
                        {getTraitIcon(trait.iconName)}
                      </div>
                      <div>
                        <h4 className="font-headline font-bold text-xs text-slate-900 leading-tight">
                          {trait.name}
                        </h4>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {trait.unlocked ? 'MUTATION ACTIVE' : `${trait.cost} DNA Pts`}
                        </span>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => onToggleTrait(trait.id)}
                      disabled={!canAfford && !trait.unlocked}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-all ${
                        trait.unlocked
                          ? 'bg-red-100 text-red-700 hover:bg-red-200'
                          : canAfford
                          ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-2xs'
                          : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                      }`}
                    >
                      {trait.unlocked ? 'Devolve' : 'Evolve'}
                    </button>
                  </div>

                  <p className="text-[11px] text-slate-600 leading-normal">
                    {trait.description}
                  </p>

                  <div className="flex items-center gap-2 pt-1 border-t border-slate-100 text-[10px] font-mono text-slate-500">
                    {trait.infectivityDelta > 0 && <span className="text-teal-700 font-bold">+{trait.infectivityDelta}% Inf</span>}
                    {trait.severityDelta > 0 && <span className="text-amber-600 font-bold">+{trait.severityDelta}% Sev</span>}
                    {trait.lethalityDelta > 0 && <span className="text-red-600 font-bold">+{trait.lethalityDelta}% Leth</span>}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {countermeasures.map((cm) => (
              <div
                key={cm.id}
                className={`p-3 rounded-xl border flex items-center justify-between gap-3 transition-all ${
                  cm.deployed
                    ? 'bg-emerald-50/70 border-emerald-300 shadow-2xs'
                    : 'bg-white border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center font-bold ${
                      cm.deployed ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    <Activity className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-headline font-bold text-xs text-slate-900 leading-tight">
                      {cm.name}
                    </h4>
                    <p className="text-[10px] text-slate-500 truncate max-w-[170px]">
                      {cm.target}
                    </p>
                    <span className="text-[10px] text-emerald-700 font-bold font-mono">
                      -{cm.efficacy}% R(t) transmission
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => onToggleCountermeasure(cm.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                    cm.deployed
                      ? 'bg-emerald-700 text-white shadow-2xs'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {cm.deployed ? 'Deployed' : 'Deploy'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
