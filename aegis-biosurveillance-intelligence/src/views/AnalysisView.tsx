import React, { useState } from 'react';
import { SEIRDataPoint } from '../types';
import { SEIRGraph } from '../components/SEIRGraph';
import { Sliders, Activity, BookOpen, Sparkles, RefreshCw } from 'lucide-react';
import { calculateSEIRTrajectory } from '../utils/seirModel';

interface AnalysisViewProps {
  initialPoints: SEIRDataPoint[];
  initialRt: number;
}

export const AnalysisView: React.FC<AnalysisViewProps> = ({
  initialPoints,
  initialRt,
}) => {
  // Interactive sliders for PINN SEIR Workbench
  const [beta, setBeta] = useState<number>(0.34);
  const [gamma, setGamma] = useState<number>(0.20);
  const [containment, setContainment] = useState<number>(38);

  // Dynamically compute trajectory based on slider parameters
  const calculatedTrajectory = calculateSEIRTrajectory({
    pinnBeta: beta,
    pinnGamma: gamma,
    containmentEfficacy: containment,
  });

  const currentRt = parseFloat(((beta / gamma) * (1 - containment / 100)).toFixed(2));

  const handleReset = () => {
    setBeta(0.34);
    setGamma(0.20);
    setContainment(38);
  };

  return (
    <div className="flex flex-col w-full gap-6">
      {/* Header */}
      <div className="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded bg-teal-100 text-teal-800 text-xs font-mono font-bold">
              MATHEMATICAL EPIDEMIOLOGY
            </span>
            <span className="text-xs text-slate-500 font-mono">
              PINN (Physics-Informed Neural Network)
            </span>
          </div>
          <h1 className="font-headline font-extrabold text-2xl text-[#0d3b36]">
            SEIR Trajectory & Parameter Estimation Workbench
          </h1>
          <p className="text-xs text-slate-500 font-body">
            Calibrate differential transmission dynamics across continuous compartments. Real-time visual comparison of Classic ODEs versus Neural SEIR adjustments with unoccluded trajectory views.
          </p>
        </div>

        <button
          type="button"
          onClick={handleReset}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-colors shrink-0"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Reset Parameters</span>
        </button>
      </div>

      {/* PARAMETER TUNING SLIDERS */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col gap-4">
        <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
          <Sliders className="w-4 h-4 text-teal-700" />
          <span className="font-headline font-bold text-xs uppercase tracking-wider text-slate-900">
            Dynamical Differential Equation Parameters
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Beta Slider */}
          <div className="flex flex-col gap-2 p-3 rounded-xl bg-slate-50 border border-slate-200">
            <div className="flex justify-between items-center text-xs">
              <span className="font-bold text-slate-800">Effective Transmission Rate (β)</span>
              <span className="font-mono font-extrabold text-teal-700 bg-white px-2 py-0.5 rounded border border-slate-200">
                {beta.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0.15"
              max="0.55"
              step="0.01"
              value={beta}
              onChange={(e) => setBeta(parseFloat(e.target.value))}
              className="w-full accent-teal-700 cursor-pointer"
            />
            <span className="text-[11px] text-slate-500">
              Governs daily contact rate and viral droplet transmission probability.
            </span>
          </div>

          {/* Gamma Slider */}
          <div className="flex flex-col gap-2 p-3 rounded-xl bg-slate-50 border border-slate-200">
            <div className="flex justify-between items-center text-xs">
              <span className="font-bold text-slate-800">Removal / Recovery Rate (γ)</span>
              <span className="font-mono font-extrabold text-emerald-700 bg-white px-2 py-0.5 rounded border border-slate-200">
                {gamma.toFixed(2)} ({(1 / gamma).toFixed(1)}d)
              </span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.35"
              step="0.01"
              value={gamma}
              onChange={(e) => setGamma(parseFloat(e.target.value))}
              className="w-full accent-emerald-600 cursor-pointer"
            />
            <span className="text-[11px] text-slate-500">
              Mean duration of infectious period before isolation or recovery.
            </span>
          </div>

          {/* Containment Efficacy Slider */}
          <div className="flex flex-col gap-2 p-3 rounded-xl bg-slate-50 border border-slate-200">
            <div className="flex justify-between items-center text-xs">
              <span className="font-bold text-slate-800">NPI Containment Strength</span>
              <span className="font-mono font-extrabold text-[#0d3b36] bg-white px-2 py-0.5 rounded border border-slate-200">
                {containment}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="75"
              step="1"
              value={containment}
              onChange={(e) => setContainment(parseInt(e.target.value, 10))}
              className="w-full accent-[#0d3b36] cursor-pointer"
            />
            <span className="text-[11px] text-slate-500">
              Combined suppression effect of masking, border testing, and ring vaccines.
            </span>
          </div>
        </div>
      </div>

      {/* SEIR GRAPH WITH DR. SWAMINATHAN (ZERO OCCLUSION) */}
      <SEIRGraph
        dataPoints={calculatedTrajectory.points}
        peakDay={calculatedTrajectory.peakDay}
        peakCases={calculatedTrajectory.peakCases}
        currentRt={currentRt}
        pinnBeta={beta}
        pinnGamma={gamma}
      />

      {/* MATHEMATICAL FOUNDATION CARD */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex flex-col gap-3">
          <div className="flex items-center gap-2 text-slate-900 font-headline font-bold text-sm">
            <BookOpen className="w-4 h-4 text-teal-700" />
            <span>Compartmental Differential Equations</span>
          </div>
          <div className="bg-slate-50 p-3 rounded-xl font-mono text-xs text-slate-700 space-y-1.5 border border-slate-200">
            <div>dS/dt = -β · S · I / N</div>
            <div>dE/dt = β · S · I / N - σ · E</div>
            <div>dI/dt = σ · E - γ · I</div>
            <div>dR/dt = γ · I</div>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed font-body">
            Where <strong>S</strong> is susceptible, <strong>E</strong> is latent exposed, <strong>I</strong> is infectious, and <strong>R</strong> is recovered/removed. The population <strong>N</strong> remains conserved across the 90-day trajectory.
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs flex flex-col gap-3">
          <div className="flex items-center gap-2 text-slate-900 font-headline font-bold text-sm">
            <Sparkles className="w-4 h-4 text-teal-700" />
            <span>Neural PINN Residual Regularization</span>
          </div>
          <div className="bg-slate-50 p-3 rounded-xl font-mono text-xs text-slate-700 space-y-1.5 border border-slate-200">
            <div>L_total = L_data + λ · L_physics</div>
            <div>L_physics = || dI/dt - (σ·E - γ·I) ||²</div>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed font-body">
            Unlike unconstrained neural networks, the Physics-Informed loss function penalizes violations of epidemiologic conservation laws, preventing hallucinations while adapting to real-world behavioral changes.
          </p>
        </div>
      </div>
    </div>
  );
};
