import React from 'react';
import { 
  ShieldCheck, 
  Clock, 
  Printer, 
  User, 
  Menu, 
  ChevronDown, 
  Activity,
  FileText
} from 'lucide-react';
import { PageView, PathogenTargetId, UserProfile } from '../types';
import { PATHOGEN_TARGETS } from '../data/simulationData';

interface HeaderProps {
  currentPage: PageView;
  onNavigate: (page: PageView) => void;
  selectedPathogenId: PathogenTargetId;
  onSelectPathogen: (id: PathogenTargetId) => void;
  day: number;
  currentUser: UserProfile | null;
  onOpenAuth: () => void;
  onOpenTerms: () => void;
  onPrintReport: () => void;
  onToggleMobileMenu?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentPage,
  onNavigate,
  selectedPathogenId,
  onSelectPathogen,
  day,
  currentUser,
  onOpenAuth,
  onOpenTerms,
  onPrintReport,
  onToggleMobileMenu,
}) => {
  return (
    <header className="no-print sticky top-0 left-0 right-0 h-16 bg-white/90 backdrop-blur-md z-40 border-b border-slate-200/80 shadow-2xs">
      <div className="h-full w-full px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-3">
        {/* Left Section: Mobile Menu + Status + Pathogen Selector */}
        <div className="flex items-center gap-3">
          {/* Mobile hamburger menu toggle */}
          <button
            type="button"
            onClick={onToggleMobileMenu}
            className="lg:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors"
            title="Toggle Menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Live Clinical Stream Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-teal-50 text-teal-700 border border-teal-200/70">
            <span className="w-2 h-2 rounded-full bg-teal-600" />
            <span className="text-[10.5px] font-headline font-bold uppercase tracking-wider text-teal-700 hidden sm:inline">
              SIMULATION READY
            </span>
            <span className="text-[10px] font-bold text-teal-600 sm:hidden">
              LIVE
            </span>
          </div>

          {/* Day / Timestamp Indicator */}
          <div className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
            <Clock className="w-3.5 h-3.5 text-teal-700" />
            <span className="text-xs font-mono font-semibold text-slate-800">
              DAY {day} // 08:42:19 UTC
            </span>
          </div>

          {/* Active Pathogen Target Dropdown */}
          <div className="relative flex items-center">
            <label htmlFor="pathogen-select" className="sr-only">Active Pathogen Target</label>
            <select
              id="pathogen-select"
              value={selectedPathogenId}
              onChange={(e) => onSelectPathogen(e.target.value as PathogenTargetId)}
              className="bg-white text-slate-900 text-xs font-semibold py-1.5 pl-3 pr-8 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0d9488] appearance-none cursor-pointer max-w-[210px] sm:max-w-[280px] truncate shadow-2xs"
            >
              {PATHOGEN_TARGETS.map((p) => (
                <option key={p.id} value={p.id}>
                  TARGET: {p.name}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 absolute right-2.5 pointer-events-none text-slate-400" />
          </div>
        </div>

        {/* Center: Desktop Navigation Tabs */}
        <nav className="hidden lg:flex items-center gap-5 text-xs font-headline font-bold tracking-wider uppercase">
          <button
            type="button"
            onClick={() => onNavigate('overview')}
            className={`pb-1 transition-all ${
              currentPage === 'overview'
                ? 'text-[#0d3b36] border-b-2 border-[#0d3b36]'
                : 'text-slate-500 hover:text-[#0d3b36]'
            }`}
          >
            Overview
          </button>
          <button
            type="button"
            onClick={() => onNavigate('simulation')}
            className={`pb-1 transition-all ${
              currentPage === 'simulation'
                ? 'text-[#0d3b36] border-b-2 border-[#0d3b36]'
                : 'text-slate-500 hover:text-[#0d3b36]'
            }`}
          >
            Radar Simulation
          </button>
          <button
            type="button"
            onClick={() => onNavigate('analysis')}
            className={`pb-1 transition-all ${
              currentPage === 'analysis'
                ? 'text-[#0d3b36] border-b-2 border-[#0d3b36]'
                : 'text-slate-500 hover:text-[#0d3b36]'
            }`}
          >
            SEIR Analysis
          </button>
          <button
            type="button"
            onClick={() => onNavigate('backtesting')}
            className={`pb-1 transition-all ${
              currentPage === 'backtesting'
                ? 'text-[#0d3b36] border-b-2 border-[#0d3b36]'
                : 'text-slate-500 hover:text-[#0d3b36]'
            }`}
          >
            Backtesting
          </button>
          <button
            type="button"
            onClick={() => onNavigate('reports')}
            className={`pb-1 transition-all ${
              currentPage === 'reports'
                ? 'text-[#0d3b36] border-b-2 border-[#0d3b36]'
                : 'text-slate-500 hover:text-[#0d3b36]'
            }`}
          >
            Surveillance Reports
          </button>
        </nav>

        {/* Right Section: Status + Print PDF Button + User Profile */}
        <div className="flex items-center gap-2.5">
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
            <span className="text-[10px] uppercase font-bold tracking-wider">
              MONITORING NOMINAL
            </span>
          </div>

          {/* Export PDF Button */}
          <button
            type="button"
            onClick={onPrintReport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0d3b36] hover:bg-[#082623] text-white text-xs font-bold shadow-xs hover:shadow transition-all"
            title="Print or Save Surveillance Dossier as PDF"
          >
            <Printer className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Export PDF</span>
          </button>

          {/* User Profile Pill / Login Trigger */}
          <button
            type="button"
            onClick={onOpenAuth}
            className="flex items-center gap-2 p-1 pl-2 sm:pr-3 rounded-full bg-teal-50 hover:bg-teal-100 border border-teal-200/80 text-[#0d3b36] transition-colors"
            title="Manage Clinical Authentication"
          >
            <div className="w-7 h-7 rounded-full bg-[#0d3b36] text-white flex items-center justify-center font-bold text-xs">
              <User className="w-3.5 h-3.5" />
            </div>
            <div className="hidden sm:flex flex-col text-left">
              <span className="text-[11px] font-headline font-bold text-slate-900 leading-none truncate max-w-[120px]">
                {currentUser ? currentUser.name.split(',')[0] : 'Sign In'}
              </span>
              <span className="text-[9px] text-teal-700 font-mono">
                {currentUser ? currentUser.clearanceLevel.split('//')[1]?.trim() || 'DEF-4' : 'GUEST'}
              </span>
            </div>
          </button>
        </div>
      </div>
    </header>
  );
};
