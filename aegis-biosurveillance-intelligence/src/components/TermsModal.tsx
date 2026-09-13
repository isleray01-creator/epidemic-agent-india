import React from 'react';
import { AlertTriangle, ShieldCheck, X } from 'lucide-react';

interface TermsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAccept?: () => void;
}

export const TermsModal: React.FC<TermsModalProps> = ({ isOpen, onClose, onAccept }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div 
        id="terms-modal-card"
        className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden"
      >
        {/* Header */}
        <div className="p-5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-headline font-bold text-lg text-slate-900">
                Terms of Use & Clinical Accuracy Disclaimer
              </h3>
              <p className="text-xs text-slate-500 font-mono">
                TERMS OF USE // REF-EPIPULSE-2026-TOS
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 flex items-center justify-center transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto text-sm text-slate-700 space-y-4 leading-relaxed">
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold block mb-1">
                Notice: Simulation & Mathematical Projections Are Not 100% Genuinely Correct
              </strong>
              <span>
                All epidemiological forecasts, reproduction rates (R_t), transmission vectors, SEIR projections, and model curves generated within the EpiPulse platform are mathematical computational estimates based on parameterized stochastic differential models. They do not constitute guaranteed deterministic clinical diagnoses or absolute real-world representations.
              </span>
            </div>
          </div>

          <div className="space-y-3 text-slate-600 text-xs">
            <h4 className="font-bold text-slate-900 text-sm">1. Nature of Computational Modeling</h4>
            <p>
              Epidemiological simulations are subject to dynamic variability, testing reporting lags, behavioral changes, genomic reassortment, and demographic variance. Variables such as infectivity, lethality, and vaccine neutralization titers are calibrated using synthetic and empirical observational datasets.
            </p>

            <h4 className="font-bold text-slate-900 text-sm">2. Clinical & Operational Decision-Making</h4>
            <p>
              Public health officers, clinical directors, and emergency management responders must NOT base critical life-safety containment, curfew, or pharmaceutical deployment solely on this software without independent empirical validation by certified statutory health authorities, including the Indian Council of Medical Research (ICMR), Ministry of Health and Family Welfare (MoHFW), and the World Health Organization (WHO).
            </p>

            <h4 className="font-bold text-slate-900 text-sm">3. Limitation of Liability</h4>
            <p>
              EpiPulse Simulator and its computational researchers provide this system for analytical research, training, countermeasure evaluation, and epidemiological modeling. Under no circumstances shall developers or contributors be held liable for clinical or administrative decisions made pursuant to these projections.
            </p>

            <h4 className="font-bold text-slate-900 text-sm">4. Data Integrity & Biosecurity Hash</h4>
            <p>
              Model snapshots are hashed with SHA-256 for audit traceability across national biosecurity monitoring stations. Periodic recalibration occurs every 4 hours or upon receipt of updated state sentinel genomic feeds.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>BIOSECURITY AUDIT PASSED // 2026</span>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={onClose}
              className="flex-1 sm:flex-none px-4 py-2 rounded-lg border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-100 transition-colors"
            >
              Close
            </button>
            <button
              onClick={() => {
                if (onAccept) onAccept();
                onClose();
              }}
              className="flex-1 sm:flex-none px-5 py-2 rounded-lg bg-[#0d3b36] hover:bg-[#082623] text-white text-xs font-bold shadow-sm transition-colors"
            >
              I Understand & Acknowledge
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
