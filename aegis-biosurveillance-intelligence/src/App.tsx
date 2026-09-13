import React, { useState, useEffect, useCallback } from 'react';
import { 
  PageView, 
  PathogenTargetId, 
  SimulationState, 
  StateOutbreakData, 
  SimulationTrait, 
  CountermeasureItem,
  UserProfile 
} from './types';
import { 
  INITIAL_SIMULATION_STATE, 
  PATHOGEN_TARGETS, 
  DEFAULT_USER 
} from './data/simulationData';
import { calculateSEIRTrajectory } from './utils/seirModel';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { AuthModal } from './components/AuthModal';
import { TermsModal } from './components/TermsModal';
import { OverviewView } from './views/OverviewView';
import { SimulationView } from './views/SimulationView';
import { AnalysisView } from './views/AnalysisView';
import { BacktestingView } from './views/BacktestingView';
import { ReportsView } from './views/ReportsView';

export default function App() {
  // Navigation state
  const [currentPage, setCurrentPage] = useState<PageView>('overview');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);

  // Modals state
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [isTermsModalOpen, setIsTermsModalOpen] = useState<boolean>(false);
  const [hasAcceptedTerms, setHasAcceptedTerms] = useState<boolean>(() => {
    return localStorage.getItem('epipulse_terms_accepted') === 'true';
  });

  // User state (persisted in localStorage)
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('epipulse_user');
    if (saved) {
      try { return JSON.parse(saved); } catch { return DEFAULT_USER; }
    }
    return DEFAULT_USER;
  });

  // Show T&C modal on first visit if not accepted
  useEffect(() => {
    if (!hasAcceptedTerms) {
      setIsTermsModalOpen(true);
    }
  }, []);

  // Pathogen target
  const [selectedPathogenId, setSelectedPathogenId] = useState<PathogenTargetId>('sars-cov-2');

  // Interactive Plague Inc simulation state
  const [simState, setSimState] = useState<SimulationState>(INITIAL_SIMULATION_STATE);
  const [selectedStateId, setSelectedStateId] = useState<string>('MH');

  // Dynamic SEIR model points based on simulation variables
  const seirTrajectory = calculateSEIRTrajectory({
    infectivity: simState.infectivity,
    severity: simState.severity,
    containmentEfficacy: simState.countermeasureEfficacy,
  });

  // Client-side simulation state initializes automatically

  // Simulation tick loop (Plague Inc progression)
  useEffect(() => {
    if (!simState.isRunning) return;

    // Speed interval in milliseconds
    const intervalTime = simState.speed === 1 ? 1200 : simState.speed === 2 ? 600 : 250;

    const timer = setInterval(() => {
      setSimState((prev) => {
        if (prev.day >= prev.maxDays) {
          return { ...prev, isRunning: false };
        }

        const nextDay = prev.day + 1;
        const dnaGain = nextDay % 3 === 0 ? 3 : 1;

        // Dynamic transmission growth multiplier based on R(t) and active traits
        const rtFactor = prev.currentRt;
        const deltaInfected = Math.round(prev.totalInfected * (rtFactor > 1 ? 0.015 : -0.008));
        const newTotalInfected = Math.max(100000, prev.totalInfected + deltaInfected);
        const newDeceased = prev.totalDeceased + Math.round((newTotalInfected * (prev.lethality / 100)) / 900);

        // Update Indian states infection levels proportionally
        const updatedStates = prev.states.map((st) => {
          const stateDelta = Math.round(st.infected * (st.activeRt > 1 ? 0.014 : -0.006));
          const updatedInfected = Math.max(1000, st.infected + stateDelta);
          const newBedLoad = Math.min(99, Math.max(20, Math.round((updatedInfected / (st.population * 0.003)) * 45)));

          return {
            ...st,
            infected: updatedInfected,
            hospitalBedLoad: newBedLoad,
            status: newBedLoad > 85 ? 'critical' : newBedLoad > 65 ? 'monitored' : 'stable',
          };
        });

        // Dynamic news ticker updates as days advance
        let ticker = prev.tickerMessage;
        if (nextDay === 15) {
          ticker = 'T+15D: Severe aerosol transmission verified along Western Ghats transport network; ring screening deployed.';
        } else if (nextDay === 28) {
          ticker = 'T+28D: Mumbai-Delhi railway corridor reports 82% passenger bio-masking adherence under NDMA mandate.';
        } else if (nextDay === 42) {
          ticker = 'T+42D: High cluster transmission recorded in Mumbai-Thane urban corridor; inter-state transit bio-screening activated.';
        } else if (nextDay === 54) {
          ticker = 'T+54D: Projected nationwide wave peak reached; ICU bed occupancy stabilizing across tier-1 hospital clusters.';
        } else if (nextDay === 70) {
          ticker = 'T+70D: Secondary transmission index decays below 0.95; ring immunization campaign expands to rural corridors.';
        }

        return {
          ...prev,
          day: nextDay,
          dnaPoints: prev.dnaPoints + dnaGain,
          totalInfected: newTotalInfected,
          totalDeceased: newDeceased,
          states: updatedStates,
          tickerMessage: ticker,
        };
      });
    }, intervalTime);

    return () => clearInterval(timer);
  }, [simState.isRunning, simState.speed]);

  // Recalculate Rt and epidemic indicators whenever traits or countermeasures change
  const recalculateSimulationMetrics = useCallback((
    traits: SimulationTrait[],
    countermeasures: CountermeasureItem[]
  ) => {
    let baseInfectivity = 65;
    let baseSeverity = 28;
    let baseLethality = 4;

    // Apply active trait modifiers
    traits.forEach((t) => {
      if (t.unlocked) {
        baseInfectivity += t.infectivityDelta;
        baseSeverity += t.severityDelta;
        baseLethality += t.lethalityDelta;
      }
    });

    // Apply countermeasure efficacy
    let totalContainmentEfficacy = 0;
    countermeasures.forEach((cm) => {
      if (cm.deployed) {
        totalContainmentEfficacy += cm.efficacy;
      }
    });

    const calculatedRt = parseFloat(
      Math.max(0.65, (baseInfectivity / 45) * (1 - totalContainmentEfficacy / 100)).toFixed(2)
    );

    const calculatedContainmentIndex = Math.min(99, Math.round(50 + totalContainmentEfficacy * 0.9));

    setSimState((prev) => {
      // Update each state's local Rt according to national containment shifts
      const updatedStates = prev.states.map((st) => ({
        ...st,
        activeRt: parseFloat(Math.max(0.7, calculatedRt + (st.airHub ? 0.08 : -0.05)).toFixed(2)),
      }));

      return {
        ...prev,
        infectivity: Math.min(100, baseInfectivity),
        severity: Math.min(100, baseSeverity),
        lethality: Math.min(100, baseLethality),
        currentRt: calculatedRt,
        countermeasureEfficacy: totalContainmentEfficacy,
        containmentIndex: calculatedContainmentIndex,
        states: updatedStates,
      };
    });
  }, []);

  // Plague Inc: Toggle Trait (Evolve / Devolve)
  const handleToggleTrait = (traitId: string) => {
    setSimState((prev) => {
      const trait = prev.traits.find((t) => t.id === traitId);
      if (!trait) return prev;

      let newDna = prev.dnaPoints;
      let newUnlocked = !trait.unlocked;

      if (newUnlocked) {
        if (newDna < trait.cost) return prev; // Cannot afford
        newDna -= trait.cost;
      } else {
        // Devolving refunds half the DNA points
        newDna += Math.floor(trait.cost / 2);
      }

      const updatedTraits = prev.traits.map((t) =>
        t.id === traitId ? { ...t, unlocked: newUnlocked } : t
      );

      // Ticker message when a mutation evolves
      const newTicker = newUnlocked
        ? `MUTATION ADAPTATION: Pathogen has evolved [${trait.name}]! Viral transmission characteristics shifted.`
        : `GENETIC SUPPRESSION: [${trait.name}] devolved to conserve biosecurity resistance buffer.`;

      // Trigger metric recalculation
      recalculateSimulationMetrics(updatedTraits, prev.countermeasures);

      return {
        ...prev,
        dnaPoints: newDna,
        traits: updatedTraits,
        tickerMessage: newTicker,
      };
    });
  };

  // Plague Inc: Toggle Countermeasure (Deploy / Withdraw)
  const handleToggleCountermeasure = (cmId: string) => {
    setSimState((prev) => {
      const cm = prev.countermeasures.find((c) => c.id === cmId);
      if (!cm) return prev;

      const newDeployed = !cm.deployed;
      const updatedCMs = prev.countermeasures.map((c) =>
        c.id === cmId ? { ...c, deployed: newDeployed, statusLabel: newDeployed ? 'Active Tier 1' : 'Standby' } : c
      );

      const newTicker = newDeployed
        ? `NDMA DIRECTIVE: [${cm.name}] deployed nationwide! Est. -${cm.efficacy}% transmission suppression.`
        : `INTERVENTION WITHDRAWN: [${cm.name}] scaled down to passive monitoring.`;

      // Trigger metric recalculation
      recalculateSimulationMetrics(prev.traits, updatedCMs);

      return {
        ...prev,
        countermeasures: updatedCMs,
        tickerMessage: newTicker,
      };
    });
  };

  // Playback handlers
  const handleTogglePlay = () => {
    setSimState((prev) => ({ ...prev, isRunning: !prev.isRunning }));
  };

  const handleChangeSpeed = (speed: 1 | 2 | 5) => {
    setSimState((prev) => ({ ...prev, speed }));
  };

  const handleResetSimulation = () => {
    setSimState({
      ...INITIAL_SIMULATION_STATE,
      isRunning: false,
      day: 0,
      dnaPoints: 45,
    });
  };

  const handleStepDay = () => {
    setSimState((prev) => ({
      ...prev,
      day: Math.min(prev.maxDays, prev.day + 1),
      dnaPoints: prev.dnaPoints + 2,
    }));
  };

  // State selection handler
  const handleSelectState = (state: StateOutbreakData) => {
    setSelectedStateId(state.id);
  };

  // Print PDF trigger
  const handlePrintReport = () => {
    window.print();
  };

  // Pathogen target switch handler
  const handleSelectPathogen = (id: PathogenTargetId) => {
    setSelectedPathogenId(id);
    const target = PATHOGEN_TARGETS.find((p) => p.id === id);
    if (target) {
      setSimState((prev) => ({
        ...prev,
        infectivity: target.baseInfectivity,
        severity: target.baseSeverity,
        lethality: target.baseLethality,
        currentRt: target.defaultRt,
        tickerMessage: `PATHOGEN SWITCHED: Active biosensor telemetry now tracking ${target.name} across all Indian air & rail hubs.`,
      }));
    }
  };

  return (
    <div className="min-h-screen bg-[#f1f5f9] text-slate-900 font-body flex flex-col antialiased">
      {/* SIDEBAR NAVIGATION (Desktop fixed & Mobile drawer) */}
      <Sidebar
        currentPage={currentPage}
        onNavigate={(page) => setCurrentPage(page)}
        isOpenMobile={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
        onOpenTerms={() => setIsTermsModalOpen(true)}
      />

      {/* MAIN WRAPPER (Shifted right on desktop by sidebar width 18rem / 288px) */}
      <div className="flex-1 lg:pl-72 flex flex-col min-w-0">
        {/* TOP HEADER */}
        <Header
          selectedPathogenId={selectedPathogenId}
          onSelectPathogen={handleSelectPathogen}
          currentUser={currentUser}
          onOpenAuth={() => setIsAuthModalOpen(true)}
          onPrintReport={handlePrintReport}
          onToggleMobileMenu={() => setIsMobileMenuOpen(true)}
        />

        {/* MAIN VIEW CONTAINER */}
        <main className="flex-1 w-full max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
          {currentPage === 'overview' && (
            <OverviewView
              simState={simState}
              seirPoints={seirTrajectory.points}
              peakDay={seirTrajectory.peakDay}
              peakCases={seirTrajectory.peakCases}
              onSelectState={handleSelectState}
              selectedStateId={selectedStateId}
              onPrint={handlePrintReport}
              onRefreshSync={() => {}}
              onSpeedChange={handleChangeSpeed}
              onTogglePlay={handleTogglePlay}
              onNavigateToSimulation={() => setCurrentPage('simulation')}
            />
          )}

          {currentPage === 'simulation' && (
            <SimulationView
              simState={simState}
              seirPoints={seirTrajectory.points}
              peakDay={seirTrajectory.peakDay}
              peakCases={seirTrajectory.peakCases}
              onTogglePlay={handleTogglePlay}
              onChangeSpeed={handleChangeSpeed}
              onReset={handleResetSimulation}
              onStepDay={handleStepDay}
              onToggleTrait={handleToggleTrait}
              onToggleCountermeasure={handleToggleCountermeasure}
              onSelectState={handleSelectState}
              selectedStateId={selectedStateId}
            />
          )}

          {currentPage === 'analysis' && (
            <AnalysisView
              initialPoints={seirTrajectory.points}
              initialRt={simState.currentRt}
            />
          )}

          {currentPage === 'backtesting' && (
            <BacktestingView />
          )}

          {currentPage === 'reports' && (
            <ReportsView
              simState={simState}
              onPrint={handlePrintReport}
              onOpenTerms={() => setIsTermsModalOpen(true)}
            />
          )}
        </main>

        {/* FOOTER (hidden in print) */}
        <footer className="no-print border-t border-slate-200/80 bg-white/60 py-4 px-6 text-xs text-slate-500">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="font-headline font-bold text-[#0d3b36]">EpiPulse</span>
              <span>•</span>
              <span>Epidemic Response Simulator</span>
            </div>

            <div className="flex items-center gap-4 text-slate-600">
              <button
                type="button"
                onClick={() => setIsTermsModalOpen(true)}
                className="hover:text-[#0d3b36] underline cursor-pointer"
              >
                Terms & Accuracy Disclaimer
              </button>
              <button
                type="button"
                onClick={() => setIsAuthModalOpen(true)}
                className="hover:text-[#0d3b36] cursor-pointer"
              >
                {currentUser ? `Signed in as ${currentUser.name}` : 'Login / Signup'}
              </button>
            </div>
          </div>
        </footer>
      </div>

      {/* AUTHENTICATION MODAL (LOGIN / SIGNUP) */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        currentUser={currentUser}
        onLoginSuccess={(user) => {
          setCurrentUser(user);
          localStorage.setItem('epipulse_user', JSON.stringify(user));
          setIsAuthModalOpen(false);
        }}
        onSignOut={() => {
          setCurrentUser(null);
          localStorage.removeItem('epipulse_user');
        }}
      />

      {/* MANDATORY TERMS & ACCURACY DISCLAIMER MODAL */}
      <TermsModal
        isOpen={isTermsModalOpen}
        onClose={() => {
          setIsTermsModalOpen(false);
          // If they close without accepting, keep showing on next visit
        }}
        onAccept={() => {
          localStorage.setItem('epipulse_terms_accepted', 'true');
          setHasAcceptedTerms(true);
          setIsTermsModalOpen(false);
        }}
      />
    </div>
  );
}
