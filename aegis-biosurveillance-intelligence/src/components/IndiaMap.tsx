import React, { useState, useMemo } from 'react';
import { StateOutbreakData } from '../types';
import { Layers, Eye, Info, CheckCircle2 } from 'lucide-react';
import { INDIA_MAP_PATHS, PathData } from './indiaMapPaths';
import { STATE_ID_MAP } from './indiaMapConfig';

interface IndiaMapProps {
  states: StateOutbreakData[];
  onSelectState?: (state: StateOutbreakData) => void;
  selectedStateId?: string;
  isSimulating?: boolean;
}

const getInfectionColor = (state: StateOutbreakData | undefined, isDark: boolean): string => {
  if (!state) return isDark ? '#1e293b' : '#f1f5f9';
  const ratio = state.totalInfected / (state.population * 0.01);
  if (ratio <= 0.001) return isDark ? '#064e3b' : '#d1fae5';
  if (ratio <= 0.005) return isDark ? '#047857' : '#6ee7b7';
  if (ratio <= 0.02) return isDark ? '#b45309' : '#fcd34d';
  if (ratio <= 0.05) return isDark ? '#c2410c' : '#fb923c';
  if (ratio <= 0.1) return isDark ? '#b91c1c' : '#f87171';
  return isDark ? '#7f1d1d' : '#dc2626';
};

export const IndiaMap: React.FC<IndiaMapProps> = ({
  states,
  onSelectState,
  selectedStateId,
  isSimulating = true,
}) => {
  const [hoveredSvgId, setHoveredSvgId] = useState<string | null>(null);
  const [mapMode, setMapMode] = useState<'standard' | 'heatmap'>('standard');

  const isDark = mapMode === 'heatmap';
  const oceanColor = isDark ? '#0b192c' : '#7ec8f8';
  const stateStroke = isDark ? '#38bdf8' : '#0f6e56';
  const hoveredState = hoveredSvgId ? states.find(s => {
    const svgId = Object.entries(STATE_ID_MAP).find(([_, name]) => name === s.name)?.[0];
    return svgId === hoveredSvgId;
  }) : null;

  const stateColorMap = useMemo(() => {
    const map: Record<string, string> = {};
    INDIA_MAP_PATHS.forEach((p: PathData) => {
      const displayName = STATE_ID_MAP[p.id] || p.id;
      const stateData = states.find(s => s.name === displayName || s.name.includes(displayName));
      map[p.id] = getInfectionColor(stateData, isDark);
    });
    return map;
  }, [states, isDark]);

  return (
    <div className="relative w-full flex flex-col overflow-hidden bg-white rounded-2xl border border-slate-200/90 shadow-sm">
      {/* Toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-2 px-4 py-3 border-b border-slate-200/80 bg-slate-50/90 backdrop-blur z-20">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 bg-teal-50 text-teal-800 border border-teal-200/80 px-2.5 py-1 rounded-md text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-teal-600" />
            <span>INDIA MAP — {states.length} STATES</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-lg bg-slate-200/70 p-0.5 text-xs font-semibold text-slate-600">
            <button
              onClick={() => setMapMode('standard')}
              className={`px-2.5 py-1 rounded-md transition-all ${
                !isDark ? 'bg-white text-slate-900 shadow-2xs font-bold' : 'hover:text-slate-900'
              }`}
            >
              Standard
            </button>
            <button
              onClick={() => setMapMode('heatmap')}
              className={`px-2.5 py-1 rounded-md transition-all ${
                isDark ? 'bg-slate-900 text-cyan-300 shadow-2xs font-bold' : 'hover:text-slate-900'
              }`}
            >
              Heatmap
            </button>
          </div>
        </div>
      </div>

      {/* SVG Map */}
      <div
        className="w-full flex items-center justify-center p-2 relative overflow-hidden select-none"
        style={{ backgroundColor: oceanColor }}
      >
        <svg
          viewBox="0 0 800 900"
          className="w-full max-w-[640px] h-auto drop-shadow-md transition-all duration-300"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* State Paths */}
          {INDIA_MAP_PATHS.map((path: PathData) => {
            const isSelected = (() => {
              const displayName = STATE_ID_MAP[path.id] || path.id;
              return states.find(s => s.name === displayName || s.name.includes(displayName))?.id === selectedStateId;
            })();
            const isHovered = hoveredSvgId === path.id;
            const fillColor = stateColorMap[path.id] || (isDark ? '#1e293b' : '#f1f5f9');

            return (
              <path
                key={path.id}
                d={path.d}
                fill={fillColor}
                stroke={isSelected ? '#f59e0b' : isHovered ? '#0d9488' : stateStroke}
                strokeWidth={isSelected ? 2.0 : isHovered ? 1.5 : 0.7}
                className="cursor-pointer transition-all duration-200"
                style={{
                  filter: isSelected ? 'url(#glow)' : 'none',
                }}
                onMouseEnter={() => setHoveredSvgId(path.id)}
                onMouseLeave={() => setHoveredSvgId(null)}
                onClick={() => {
                  const displayName = STATE_ID_MAP[path.id] || path.id;
                  const stateData = states.find(s => s.name === displayName || s.name.includes(displayName));
                  if (stateData && onSelectState) onSelectState(stateData);
                }}
              />
            );
          })}

          {/* Hovered state label */}
          {hoveredState && (
            <g>
              <rect
                x="10"
                y="10"
                width="200"
                height="50"
                rx="6"
                fill={isDark ? 'rgba(15,23,42,0.9)' : 'rgba(255,255,255,0.95)'}
                stroke={isDark ? '#38bdf8' : '#0f6e56'}
                strokeWidth="1"
              />
              <text
                x="20"
                y="30"
                fontSize="12"
                fontWeight="bold"
                fill={isDark ? '#e2e8f0' : '#1e293b'}
              >
                {hoveredState.name}
              </text>
              <text
                x="20"
                y="46"
                fontSize="10"
                fill={isDark ? '#94a3b8' : '#64748b'}
              >
                Infected: {(hoveredState.totalInfected / 1000000).toFixed(2)}M | Rt: {hoveredState.currentRt.toFixed(2)}
              </text>
            </g>
          )}
        </svg>
      </div>

      {/* Legend */}
      <div className="px-4 py-3 border-t border-slate-200/80 bg-slate-50/90">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-[10px] font-bold text-slate-600 uppercase">Infection Level:</span>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: isDark ? '#064e3b' : '#d1fae5' }} />
            <span className="text-[10px] text-slate-600">Low</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: isDark ? '#047857' : '#6ee7b7' }} />
            <span className="text-[10px] text-slate-600">Moderate</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: isDark ? '#b45309' : '#fcd34d' }} />
            <span className="text-[10px] text-slate-600">Elevated</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: isDark ? '#c2410c' : '#fb923c' }} />
            <span className="text-[10px] text-slate-600">High</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: isDark ? '#b91c1c' : '#f87171' }} />
            <span className="text-[10px] text-slate-600">Severe</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: isDark ? '#7f1d1d' : '#dc2626' }} />
            <span className="text-[10px] text-slate-600">Critical</span>
          </div>
        </div>
      </div>
    </div>
  );
};
