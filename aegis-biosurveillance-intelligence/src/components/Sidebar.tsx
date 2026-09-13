import React from 'react';
import { 
  ShieldCheck, 
  BarChart3, 
  Radar, 
  Dna, 
  ShieldAlert, 
  FileSpreadsheet, 
  History, 
  AlertCircle, 
  X,
  FileText,
  Radio
} from 'lucide-react';
import { PageView } from '../types';

interface SidebarProps {
  currentPage: PageView;
  onNavigate: (page: PageView) => void;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
  onOpenTerms: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onNavigate,
  isOpenMobile = false,
  onCloseMobile,
  onOpenTerms,
}) => {
  const navItems: { id: PageView; label: string; icon: React.ReactNode; badge?: string }[] = [
    {
      id: 'overview',
      label: 'Executive Briefing',
      icon: <BarChart3 className="w-4 h-4" />,
    },
    {
      id: 'simulation',
      label: 'Bio-Radar Telemetry',
      icon: <Radar className="w-4 h-4" />,
      badge: 'LIVE',
    },
    {
      id: 'analysis',
      label: 'Pathogen PINN Trajectory',
      icon: <Dna className="w-4 h-4" />,
    },
    {
      id: 'backtesting',
      label: 'Variant Backtesting',
      icon: <History className="w-4 h-4" />,
    },
    {
      id: 'reports',
      label: 'Surveillance Reports & PDF',
      icon: <FileSpreadsheet className="w-4 h-4" />,
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpenMobile && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-xs lg:hidden"
        />
      )}

      {/* Main Sidebar Container */}
      <aside
        className={`no-print fixed top-0 left-0 h-full w-72 bg-white z-50 flex flex-col justify-between border-r border-slate-200 shadow-sm transition-transform duration-300 ${
          isOpenMobile ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex flex-col">
          {/* Top Branding */}
          <div className="h-16 px-4 flex items-center justify-between border-b border-slate-200/80 bg-slate-50/70">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-[#0d3b36] text-white flex items-center justify-center shadow-xs">
                <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" className="text-teal-300" />
                </svg>
              </div>
              <div className="flex flex-col">
                <span className="font-headline font-extrabold text-base text-[#0d3b36] tracking-tight leading-tight">
                  EpiPulse
                </span>
                <span className="text-[10px] uppercase tracking-widest text-teal-700 font-bold">
                  Epidemic Response Simulator
                </span>
              </div>
            </div>

            {/* Mobile close button */}
            {isOpenMobile && (
              <button
                type="button"
                onClick={onCloseMobile}
                className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-700"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>

          {/* Classification Pill */}
          <div className="px-4 py-3">
            <div className="px-3 py-1.5 rounded-lg bg-teal-50 border border-teal-200/60 flex items-center justify-between">
              <span className="text-[10px] text-teal-800 font-bold uppercase tracking-wider">
                Classification
              </span>
              <span className="text-[11px] font-mono text-[#0d3b36] font-extrabold">
                RESEARCH ACCESS // v2.0
              </span>
            </div>
          </div>

          {/* Navigation Section */}
          <div className="px-4 py-1">
            <span className="px-2 text-[10px] uppercase tracking-widest text-slate-400 font-bold">
              Surveillance Vectors
            </span>
          </div>

          <nav className="px-3 flex flex-col gap-1 mt-1">
            {navItems.map((item) => {
              const isActive = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    onNavigate(item.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`flex items-center justify-between px-3 py-2.5 rounded-xl font-headline text-xs transition-all ${
                    isActive
                      ? 'bg-teal-50 text-[#0d3b36] font-extrabold border-l-4 border-[#0d9488] shadow-2xs'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 font-semibold'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <span className={isActive ? 'text-[#0d9488]' : 'text-slate-400'}>
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-red-100 text-red-700">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Clinical Advisory Feed */}
          <div className="px-4 pt-4 pb-1">
            <span className="px-2 text-[10px] uppercase tracking-widest text-slate-400 font-bold">
              Clinical Advisory Feed
            </span>
          </div>

          <div className="px-4 flex flex-col gap-2">
            <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/80 flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-amber-700 font-bold flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping" />
                  ICMR TELEMETRY
                </span>
                <span className="text-[10px] text-slate-400 font-mono">T-04m</span>
              </div>
              <p className="text-[11px] text-slate-600 leading-relaxed font-body">
                Spike mutation divergence (F486P) detected in Maharashtra biosensor ring corridor.
              </p>
            </div>

            <div className="p-2.5 rounded-lg border border-slate-200 bg-white flex flex-col gap-1">
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                <span className="font-bold text-teal-800">GENOMIC SURVEILLANCE</span>
                <span>T-18m</span>
              </div>
              <p className="text-[10.5px] text-slate-600">
                Kerala contact tracing ring covers 94% of symptomatic clusters.
              </p>
            </div>
          </div>
        </div>

        {/* Bottom Section: Telemetry Uplink + Terms Disclaimer Link */}
        <div className="p-4 bg-slate-50/80 border-t border-slate-200 flex flex-col gap-3">
          {/* Telemetry Uplink Gauge */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Telemetry Uplink
              </span>
              <div className="flex items-center gap-1.5">
                <Radio className="w-3 h-3 text-emerald-600 animate-pulse" />
                <span className="text-xs text-emerald-700 font-bold font-mono">99.98% Active</span>
              </div>
            </div>
            <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-600 w-11/12 rounded-full" />
            </div>
          </div>

          {/* Terms & Accuracy Disclaimer Trigger */}
          <button
            type="button"
            onClick={onOpenTerms}
            className="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-600 text-[11px] font-semibold transition-colors"
          >
            <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
            <span>Accuracy & Legal Disclaimer</span>
          </button>
        </div>
      </aside>
    </>
  );
};
