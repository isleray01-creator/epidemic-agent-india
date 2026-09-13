import React from 'react';
import { 
  Printer, 
  User, 
  Menu, 
  ChevronDown
} from 'lucide-react';
import { PageView, PathogenTargetId, UserProfile } from '../types';
import { PATHOGEN_TARGETS } from '../data/simulationData';

interface HeaderProps {
  selectedPathogenId: PathogenTargetId;
  onSelectPathogen: (id: PathogenTargetId) => void;
  currentUser: UserProfile | null;
  onOpenAuth: () => void;
  onPrintReport: () => void;
  onToggleMobileMenu?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  selectedPathogenId,
  onSelectPathogen,
  currentUser,
  onOpenAuth,
  onPrintReport,
  onToggleMobileMenu,
}) => {
  return (
    <header className="no-print sticky top-0 left-0 right-0 h-16 bg-white/95 backdrop-blur-md z-40 border-b border-slate-200/80 shadow-2xs">
      <div className="h-full w-full px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-4">
        {/* Left Section: Mobile Menu + Pathogen Target Selector */}
        <div className="flex items-center gap-3">
          {/* Mobile hamburger menu toggle */}
          <button
            type="button"
            onClick={onToggleMobileMenu}
            className="lg:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors"
            title="Toggle Navigation Menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Active Pathogen Target Dropdown */}
          <div className="relative flex items-center">
            <label htmlFor="pathogen-select" className="sr-only">Active Pathogen Target</label>
            <select
              id="pathogen-select"
              value={selectedPathogenId}
              onChange={(e) => onSelectPathogen(e.target.value as PathogenTargetId)}
              className="bg-slate-50 hover:bg-slate-100 text-slate-900 text-xs font-semibold py-2 pl-3.5 pr-8 rounded-xl border border-slate-300/80 focus:outline-none focus:ring-2 focus:ring-[#0d9488] appearance-none cursor-pointer max-w-[240px] sm:max-w-[320px] truncate shadow-2xs transition-colors"
            >
              {PATHOGEN_TARGETS.map((p) => (
                <option key={p.id} value={p.id}>
                  Target: {p.name}
                </option>
              ))}
            </select>
            <ChevronDown className="w-4 h-4 absolute right-2.5 pointer-events-none text-slate-500" />
          </div>
        </div>

        {/* Right Section: Export PDF + User Profile */}
        <div className="flex items-center gap-3">
          {/* Export PDF Button */}
          <button
            type="button"
            onClick={onPrintReport}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#0d3b36] hover:bg-[#082623] text-white text-xs font-bold shadow-xs hover:shadow transition-all"
            title="Print or Save Surveillance Dossier as PDF"
          >
            <Printer className="w-4 h-4" />
            <span className="hidden sm:inline">Export PDF</span>
          </button>

          {/* User Profile Pill / Login Trigger */}
          <button
            type="button"
            onClick={onOpenAuth}
            className="flex items-center gap-2.5 p-1 pl-2 sm:pr-3.5 rounded-full bg-slate-100 hover:bg-slate-200/80 border border-slate-200 text-[#0d3b36] transition-colors"
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
