import React from 'react';
import { Activity, Sparkles, MessageSquare } from 'lucide-react';

interface DoctorAnalystProps {
  currentRt: number;
  peakDay: number;
  peakCases: number;
  compact?: boolean;
}

export const DoctorAnalyst: React.FC<DoctorAnalystProps> = ({
  currentRt,
  peakDay,
  peakCases,
  compact = false,
}) => {
  return (
    <div className="flex flex-col sm:flex-row items-center gap-4 bg-gradient-to-r from-emerald-50/70 via-teal-50/40 to-slate-50 border border-teal-200/60 rounded-xl p-4 shadow-xs relative overflow-hidden">
      {/* Subtle Background Accent */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-teal-500/5 rounded-full blur-2xl pointer-events-none" />

      {/* Doctor Vector Avatar */}
      <div className="relative shrink-0 flex items-center justify-center">
        <div className="w-20 h-28 sm:w-24 sm:h-32 flex items-center justify-center">
          <svg
            viewBox="0 0 160 220"
            className="w-full h-full drop-shadow-md select-none"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Ground Shadow */}
            <ellipse cx="80" cy="214" rx="45" ry="5" fill="#0f172a" fillOpacity="0.12" />

            {/* Trousers */}
            <path d="M 64 165 L 68 210 L 76 210 L 75 165 Z" fill="#334155" />
            <path d="M 83 165 L 82 210 L 90 210 L 94 165 Z" fill="#334155" />
            {/* Shoes */}
            <rect x="66" y="208" width="12" height="5" rx="2" fill="#0f172a" />
            <rect x="80" y="208" width="12" height="5" rx="2" fill="#0f172a" />

            {/* Clinical Lab Coat */}
            <path
              d="M 52 80 L 46 175 L 75 185 L 85 185 L 114 175 L 108 80 Z"
              fill="#ffffff"
              stroke="#cbd5e1"
              strokeWidth="1.5"
            />
            {/* Lapels */}
            <path d="M 70 80 L 80 130 L 66 155" stroke="#0d3b36" strokeWidth="1.8" strokeLinecap="round" />
            <path d="M 90 80 L 80 130 L 94 155" stroke="#0d3b36" strokeWidth="1.8" strokeLinecap="round" />

            {/* Stethoscope */}
            <path
              d="M 72 74 C 68 95 72 118 77 122 C 81 126 84 122 84 118"
              stroke="#0d9488"
              strokeWidth="1.8"
              strokeLinecap="round"
              fill="none"
            />
            <circle cx="84" cy="118" r="2.8" fill="#0d3b36" />

            {/* Left Arm holding Datapad */}
            <path d="M 56 82 L 40 118 L 48 130" stroke="#ffffff" strokeWidth="9" strokeLinecap="round" />
            <rect x="34" y="122" width="22" height="15" rx="2" fill="#0d3b36" stroke="#0d9488" strokeWidth="1" />
            <rect x="37" y="125" width="16" height="2" fill="#99f6e4" />
            <rect x="37" y="129" width="10" height="1.5" fill="#10b981" />

            {/* Right Arm - Gesturing Upward */}
            <path
              d="M 104 82 L 126 65 L 138 38"
              stroke="#ffffff"
              strokeWidth="8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="139" cy="36" r="4" fill="#f59e0b" />
            <line x1="140" y1="35" x2="148" y2="26" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" />

            {/* Shirt & Tie */}
            <polygon points="76,68 84,68 80,90" fill="#ccfbf1" />
            <polygon points="78,82 82,82 81,105" fill="#0d3b36" />

            {/* Head & Glasses */}
            <rect x="75" y="58" width="10" height="12" rx="2" fill="#f59e0b" />
            <path d="M 72 44 C 72 32 88 30 90 44 C 90 52 86 60 78 60 C 73 60 72 52 72 44 Z" fill="#f59e0b" />
            <path d="M 70 42 C 70 28 84 25 92 31 C 93 37 90 41 88 43 C 84 37 76 37 70 42 Z" fill="#1e293b" />
            {/* Clinical Spectacles */}
            <rect x="76" y="40" width="17" height="6" rx="1.5" fill="#ffffff" stroke="#0d3b36" strokeWidth="1.2" />
            <line x1="77" y1="43" x2="91" y2="43" stroke="#0d9488" strokeWidth="1" />
          </svg>
        </div>

        {/* Status Dot */}
        <span className="absolute bottom-1 right-2 w-3 h-3 rounded-full bg-emerald-500 border-2 border-white" />
      </div>

      {/* Clinical Speech & Analyst Briefing (Zero occlusion layout) */}
      <div className="flex-1 text-xs text-slate-700 space-y-1.5">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="font-headline font-bold text-slate-900 text-sm">
              Dr. V. Swaminathan, FAMS, DSc
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#0d3b36] text-teal-200">
              CHIEF EPIDEMIOLOGIST
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-700 font-semibold">
            <Activity className="w-3.5 h-3.5" />
            <span>SEIR NON-OCCLUDED BRIEFING</span>
          </div>
        </div>

        <p className="text-slate-600 leading-relaxed font-body">
          <strong className="text-slate-900">Clinical Evaluation: </strong>
          Physics-Informed Neural SEIR (PINN) confirms peak inundation around{' '}
          <strong className="text-[#0d3b36]">Day {peakDay}</strong> at approximately{' '}
          <strong className="text-[#0d3b36]">{(peakCases / 1000000).toFixed(2)}M cases</strong>. 
          Targeted tier-1 ring vaccination and metropolitan masking have compressed the effective reproduction number down to{' '}
          <strong className={currentRt > 1.2 ? 'text-red-600' : 'text-emerald-700'}>
            R(t) = {currentRt}
          </strong>. 
          All curve telemetry coordinates and timeline axes remain fully unobstructed and accessible.
        </p>

        <div className="flex items-center gap-3 pt-1 text-[11px] text-slate-500 font-mono">
          <span>PIPELINE: NovaSeq 6000 DeepLineage</span>
          <span>•</span>
          <span className="text-teal-700 font-bold">SOBOL SENSITIVITY: 0.41 (R₀ CRITICALITY)</span>
        </div>
      </div>
    </div>
  );
};
