import React, { useState } from 'react';
import { SEIRDataPoint } from '../types';
import { DoctorAnalyst } from './DoctorAnalyst';

interface SEIRGraphProps {
  dataPoints: SEIRDataPoint[];
  peakDay: number;
  peakCases: number;
  currentRt: number;
  pinnBeta?: number;
  pinnGamma?: number;
}

export const SEIRGraph: React.FC<SEIRGraphProps> = ({
  dataPoints,
  peakDay,
  peakCases,
  currentRt,
  pinnBeta = 0.341,
  pinnGamma = 0.198,
}) => {
  const [hoveredPoint, setHoveredPoint] = useState<SEIRDataPoint | null>(null);

  // SVG dimensions
  const svgWidth = 900;
  const svgHeight = 360;
  const padding = { top: 40, right: 30, bottom: 50, left: 60 };

  const plotWidth = svgWidth - padding.left - padding.right;
  const plotHeight = svgHeight - padding.top - padding.bottom;

  // Max value for Y scaling (e.g. 2.7M)
  const maxY = 2700000;

  // Helper coordinate converters
  const getX = (day: number) => padding.left + (day / 90) * plotWidth;
  const getY = (val: number) => padding.top + plotHeight - (Math.min(val, maxY) / maxY) * plotHeight;

  // Generate path strings
  // 1. CI Band Path (fill)
  const ciPathD = dataPoints.reduce((acc, pt, i) => {
    const x = getX(pt.day);
    const y = getY(pt.ciUpper);
    return i === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
  }, '');

  const ciBottomPath = [...dataPoints].reverse().reduce((acc, pt) => {
    const x = getX(pt.day);
    const y = getY(pt.ciLower);
    return `${acc} L ${x} ${y}`;
  }, '');

  const completeCiArea = `${ciPathD} ${ciBottomPath} Z`;

  // 2. Classic SEIR path
  const classicPathD = dataPoints.reduce((acc, pt, i) => {
    const x = getX(pt.day);
    const y = getY(pt.classicSEIR);
    return i === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
  }, '');

  // 3. Neural SEIR path
  const neuralPathD = dataPoints.reduce((acc, pt, i) => {
    const x = getX(pt.day);
    const y = getY(pt.neuralSEIR);
    return i === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
  }, '');

  // 4. Real Observed path (only up to Day 42)
  const observedPoints = dataPoints.filter((pt) => pt.realObserved !== undefined);
  const realObservedPathD = observedPoints.reduce((acc, pt, i) => {
    const x = getX(pt.day);
    const y = getY(pt.realObserved!);
    return i === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
  }, '');

  // Day 42 coordinates for vertical NOW marker
  const xDay42 = getX(42);
  const xPeak = getX(peakDay);
  const yPeak = getY(peakCases);

  return (
    <section className="w-full bg-white rounded-2xl p-4 sm:p-6 flex flex-col gap-4 shadow-sm border border-slate-200/80 relative overflow-hidden print-exact print-break-avoid">
      {/* Graph Header & Legend */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3 pb-3 border-b border-slate-200">
        <div>
          <h2 className="font-headline text-lg sm:text-xl text-[#0d3b36] font-extrabold tracking-tight">
            Deep-Informed SEIR Epidemic Trajectory — Projective Ensemble
          </h2>
          <p className="text-xs text-slate-500 font-body">
            Continuous compartmental dynamics: Susceptible → Exposed → Infectious → Removed (Physics-Informed PINN Fit)
          </p>
        </div>

        {/* Legend Chips */}
        <div className="flex items-center flex-wrap gap-2 text-xs font-medium">
          <span className="flex items-center gap-1.5 text-slate-900 font-semibold px-2 py-1 rounded bg-slate-100">
            <span className="w-3.5 h-1 bg-slate-900 rounded-full" /> Real Observed
          </span>
          <span className="flex items-center gap-1.5 text-slate-500 px-2 py-1 rounded bg-slate-100">
            <span className="w-3.5 h-0.5 bg-slate-400 border-dashed" /> Classic SEIR
          </span>
          <span className="flex items-center gap-1.5 text-teal-700 font-bold px-2 py-1 rounded bg-teal-50 border border-teal-200">
            <span className="w-3.5 h-1 bg-teal-600 rounded-full" /> Neural SEIR (Learned)
          </span>
          <span className="flex items-center gap-1.5 text-teal-600 px-2 py-1 rounded bg-teal-50/60 border border-teal-100">
            <span className="w-3 h-2 bg-teal-500/20 border border-teal-500/40 rounded-xs" /> 95% CI Band
          </span>
        </div>
      </div>

      {/* MAIN GRAPH CANVAS (UNOBSTRUCTED - 100% CLEAR VIEW) */}
      <div className="relative w-full h-[380px] sm:h-[420px] bg-[#f8fafc]/90 rounded-xl p-2 border border-slate-200/80 shadow-inner overflow-hidden">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-full select-none"
          preserveAspectRatio="none"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="ci-band-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0d9488" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#0d9488" stopOpacity="0.03" />
            </linearGradient>
            <filter id="neural-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2.5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Horizontal Grid Lines */}
          <line x1={padding.left} y1={getY(2500000)} x2={svgWidth - padding.right} y2={getY(2500000)} stroke="#e2e8f0" strokeWidth="1" />
          <line x1={padding.left} y1={getY(1800000)} x2={svgWidth - padding.right} y2={getY(1800000)} stroke="#e2e8f0" strokeWidth="1" />
          <line x1={padding.left} y1={getY(1000000)} x2={svgWidth - padding.right} y2={getY(1000000)} stroke="#e2e8f0" strokeWidth="1" />
          <line x1={padding.left} y1={getY(200000)} x2={svgWidth - padding.right} y2={getY(200000)} stroke="#e2e8f0" strokeWidth="1" />

          {/* Vertical Grid Lines at key milestones */}
          <line x1={getX(0)} y1={padding.top} x2={getX(0)} y2={svgHeight - padding.bottom} stroke="#edf2f7" strokeWidth="1" />
          <line x1={getX(25)} y1={padding.top} x2={getX(25)} y2={svgHeight - padding.bottom} stroke="#edf2f7" strokeDasharray="3 3" strokeWidth="1" />
          <line x1={getX(42)} y1={padding.top} x2={getX(42)} y2={svgHeight - padding.bottom} stroke="#edf2f7" strokeDasharray="3 3" strokeWidth="1" />
          <line x1={getX(65)} y1={padding.top} x2={getX(65)} y2={svgHeight - padding.bottom} stroke="#edf2f7" strokeDasharray="3 3" strokeWidth="1" />
          <line x1={getX(90)} y1={padding.top} x2={getX(90)} y2={svgHeight - padding.bottom} stroke="#edf2f7" strokeWidth="1" />

          {/* Y-Axis Numeric Labels (Right-aligned to left padding) */}
          <text x={padding.left - 12} y={getY(2500000) + 4} fill="#64748b" fontFamily="Inter" fontSize="11" fontWeight="700" textAnchor="end">2.5M</text>
          <text x={padding.left - 12} y={getY(1800000) + 4} fill="#64748b" fontFamily="Inter" fontSize="11" fontWeight="700" textAnchor="end">1.8M</text>
          <text x={padding.left - 12} y={getY(1000000) + 4} fill="#64748b" fontFamily="Inter" fontSize="11" fontWeight="700" textAnchor="end">1.0M</text>
          <text x={padding.left - 12} y={getY(200000) + 4} fill="#64748b" fontFamily="Inter" fontSize="11" fontWeight="700" textAnchor="end">0.2M</text>

          {/* 95% Confidence Interval Area */}
          <path d={completeCiArea} fill="url(#ci-band-grad)" />

          {/* Classical SEIR Trajectory Curve */}
          <path d={classicPathD} stroke="#94a3b8" strokeWidth="2" strokeDasharray="4 4" fill="none" />

          {/* Real Observed Curve (solid dark slate with circles up to Day 42) */}
          <path d={realObservedPathD} stroke="#0f172a" strokeWidth="3" strokeLinecap="round" fill="none" />
          {observedPoints.filter((_, idx) => idx % 6 === 0 || idx === observedPoints.length - 1).map((pt) => (
            <circle
              key={`obs-${pt.day}`}
              cx={getX(pt.day)}
              cy={getY(pt.realObserved!)}
              r={pt.day === 42 ? 5.5 : 3.5}
              fill={pt.day === 42 ? '#0d9488' : '#0f172a'}
              stroke="#ffffff"
              strokeWidth="1.5"
            />
          ))}

          {/* Neural PINN Learned SEIR Curve (Teal Glow) */}
          <path d={neuralPathD} stroke="#0d9488" strokeWidth="3.5" strokeLinecap="round" filter="url(#neural-glow)" fill="none" />

          {/* Current Timeline Divider (T+42 Today) */}
          <line
            x1={xDay42}
            y1={padding.top - 10}
            x2={xDay42}
            y2={svgHeight - padding.bottom + 10}
            stroke="#dc2626"
            strokeWidth="1.8"
            strokeDasharray="4 2"
          />
          <rect x={xDay42 - 40} y={padding.top - 15} width="80" height="20" rx="4" fill="#dc2626" />
          <text x={xDay42} y={padding.top - 1} fill="#ffffff" fontFamily="Inter" fontSize="10" fontWeight="800" textAnchor="middle">
            NOW (T+42)
          </text>

          {/* Projected Peak Marker & Callout Box */}
          <g transform={`translate(${xPeak}, ${yPeak})`}>
            <circle r="6" fill="#ffffff" stroke="#0d9488" strokeWidth="2.5" />
            <line x1="0" y1="-6" x2="0" y2="-32" stroke="#0d9488" strokeWidth="1.5" />
            <circle cx="0" cy="-32" r="3" fill="#0d9488" />
            <rect
              x="-76"
              y="-72"
              width="152"
              height="34"
              rx="6"
              fill="#ffffff"
              stroke="#0d9488"
              strokeWidth="1.5"
              filter="drop-shadow(0 2px 4px rgba(0,0,0,0.08))"
            />
            <text x="0" y="-55" fill="#0d3b36" fontFamily="Plus Jakarta Sans" fontSize="10.5" fontWeight="800" textAnchor="middle">
              PEAK: DAY {peakDay} • {(peakCases / 1000000).toFixed(2)}M
            </text>
            <text x="0" y="-42" fill="#059669" fontFamily="Inter" fontSize="9" fontWeight="700" textAnchor="middle">
              +4.2% Learned vs Real
            </text>
          </g>

          {/* X-Axis Timeline Labels */}
          <text x={getX(0)} y={svgHeight - 18} fill="#64748b" fontFamily="Inter" fontSize="10" fontWeight="600">Day 0 (01 Jan)</text>
          <text x={getX(25)} y={svgHeight - 18} fill="#64748b" fontFamily="Inter" fontSize="10" fontWeight="600" textAnchor="middle">Day 25</text>
          <text x={getX(42)} y={svgHeight - 18} fill="#dc2626" fontFamily="Inter" fontSize="10.5" fontWeight="800" textAnchor="middle">Day 42 (Today)</text>
          <text x={getX(65)} y={svgHeight - 18} fill="#64748b" fontFamily="Inter" fontSize="10" fontWeight="600" textAnchor="middle">Day 65 (Post-Peak)</text>
          <text x={getX(90)} y={svgHeight - 18} fill="#64748b" fontFamily="Inter" fontSize="10" fontWeight="600" textAnchor="end">Day 90 (End)</text>

          {/* Interactive Hover Vertical Line and Points */}
          {hoveredPoint && (
            <g>
              <line
                x1={getX(hoveredPoint.day)}
                y1={padding.top}
                x2={getX(hoveredPoint.day)}
                y2={svgHeight - padding.bottom}
                stroke="#0d9488"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              <circle
                cx={getX(hoveredPoint.day)}
                cy={getY(hoveredPoint.neuralSEIR)}
                r="5"
                fill="#0d9488"
                stroke="#ffffff"
                strokeWidth="2"
              />
            </g>
          )}

          {/* Invisible interactive hover rects along days */}
          {dataPoints.map((pt) => (
            <rect
              key={`hover-rect-${pt.day}`}
              x={getX(pt.day) - plotWidth / 180}
              y={padding.top}
              width={plotWidth / 90}
              height={plotHeight}
              fill="transparent"
              className="cursor-crosshair"
              onMouseEnter={() => setHoveredPoint(pt)}
              onMouseLeave={() => setHoveredPoint(null)}
            />
          ))}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredPoint && (
          <div
            className="absolute top-4 right-4 z-20 bg-white/95 backdrop-blur rounded-xl p-3 border border-teal-200 shadow-xl text-xs space-y-1 pointer-events-none"
          >
            <div className="font-headline font-bold text-slate-900 border-b border-slate-100 pb-1 flex items-center justify-between gap-3">
              <span>{hoveredPoint.label}</span>
              <span className="text-teal-700 font-mono font-bold">
                {(hoveredPoint.neuralSEIR / 1000000).toFixed(2)}M Active
              </span>
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] text-slate-600 font-mono">
              <div>Susceptible: {(hoveredPoint.susceptible / 1000000).toFixed(1)}M</div>
              <div>Exposed: {(hoveredPoint.exposed / 1000000).toFixed(2)}M</div>
              <div>Infectious: {(hoveredPoint.infectious / 1000000).toFixed(2)}M</div>
              <div>Recovered: {(hoveredPoint.recovered / 1000000).toFixed(2)}M</div>
              {hoveredPoint.realObserved !== undefined && (
                <div className="col-span-2 text-slate-900 font-bold pt-0.5">
                  Observed Ground Truth: {(hoveredPoint.realObserved / 1000000).toFixed(2)}M
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* DOCTOR ANALYST BRIEFING DOCK (COMPLETELY CLEAN - ZERO OCCLUSION OF GRAPH) */}
      <DoctorAnalyst currentRt={currentRt} peakDay={peakDay} peakCases={peakCases} />

      {/* Model Dynamics Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1 text-xs text-slate-600">
        <div className="flex flex-col gap-1 p-3 rounded-xl bg-slate-50 border border-slate-200">
          <span className="text-[11px] uppercase font-bold text-teal-700">PINN Learned Parameter Β</span>
          <span className="text-slate-900 font-bold font-mono text-sm">{pinnBeta} ± 0.012</span>
          <span className="text-[11px] text-slate-500">Reflects transmission coefficient calibrated across 28 metropolitan hubs.</span>
        </div>
        <div className="flex flex-col gap-1 p-3 rounded-xl bg-slate-50 border border-slate-200">
          <span className="text-[11px] uppercase font-bold text-emerald-700">Latency Removal γ</span>
          <span className="text-slate-900 font-bold font-mono text-sm">{pinnGamma} (Recovery 5.05 Days)</span>
          <span className="text-[11px] text-slate-500">Accelerated viral clearance linked to targeted antiviral ring deployment.</span>
        </div>
        <div className="flex flex-col gap-1 p-3 rounded-xl bg-slate-50 border border-slate-200">
          <span className="text-[11px] uppercase font-bold text-amber-700">Peak Inundation Window</span>
          <span className="text-slate-900 font-bold font-mono text-sm">24 Feb – 02 Mar 2026</span>
          <span className="text-[11px] text-slate-500">ICU bed capacity buffered at 84% threshold under NDMA guidance.</span>
        </div>
      </div>
    </section>
  );
};
