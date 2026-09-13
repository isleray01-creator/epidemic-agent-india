import { StateOutbreakData } from '../types';
import { STATE_CENTER_COORDS, STATE_ADJACENCY_NETWORK, INTERSTATE_TRANSIT_CORRIDORS } from '../data/indiaMapPaths';

export interface PropagationOptions {
  currentDay: number;
  infectivity: number; // 0 - 100
  transitRestrictionActive: boolean; // npi_rail_lock deployed
  airportBioScreeningActive: boolean; // npi_air_screening deployed
  baseRt: number;
}

export function propagateEpidemicStep(
  states: StateOutbreakData[],
  options: PropagationOptions
): {
  updatedStates: StateOutbreakData[];
  newlyInfectedStateNames: string[];
  totalInfected: number;
  totalDeceased: number;
  totalRecovered: number;
} {
  const {
    currentDay,
    infectivity,
    transitRestrictionActive,
    airportBioScreeningActive,
    baseRt,
  } = options;

  const newlyInfectedStateNames: string[] = [];

  // State lookup by ID
  const stateMap = new Map<string, StateOutbreakData>();
  states.forEach((st) => stateMap.set(st.id, { ...st }));

  // Find currently infected states
  const infectedStateIds = states
    .filter((st) => st.infected > 0)
    .map((st) => st.id);

  // 1. Check direct land border propagation (adjacent neighbors)
  infectedStateIds.forEach((srcId) => {
    const srcState = stateMap.get(srcId);
    if (!srcState || srcState.infected < 50) return;

    const neighbors = STATE_ADJACENCY_NETWORK[srcId] || [];
    // Transmission probability depends on source infection density & pathogen infectivity
    const infectionPressure = (srcState.infected / srcState.population) * 1000;
    // Transit restriction cuts adjacent road/commuter border crossover by 45%
    const borderFactor = transitRestrictionActive ? 0.55 : 1.0;
    const spreadChance = Math.min(0.65, (0.08 + (infectivity / 150) + infectionPressure * 0.1) * borderFactor);

    neighbors.forEach((nbrId) => {
      const nbrState = stateMap.get(nbrId);
      if (!nbrState) return;

      if (nbrState.infected === 0) {
        // Uninfected state candidate for spillover
        // Deterministic check combined with threshold
        const daysSinceSrcInfection = currentDay - (srcState.infectedAtDay ?? 0);
        if (daysSinceSrcInfection >= 2 && Math.random() < spreadChance) {
          const initialSeeding = Math.round(50 + Math.random() * 120 * (infectivity / 50));
          nbrState.infected = initialSeeding;
          nbrState.infectedAtDay = currentDay;
          nbrState.activeRt = parseFloat(Math.max(1.15, baseRt * 1.05).toFixed(2));
          newlyInfectedStateNames.push(nbrState.name);
        }
      }
    });
  });

  // 2. Check interstate transit corridor vectors (Air & High-speed Rail corridors)
  INTERSTATE_TRANSIT_CORRIDORS.forEach((corridor) => {
    const fromState = stateMap.get(corridor.from);
    const toState = stateMap.get(corridor.to);
    if (!fromState || !toState) return;

    // Both can transmit bidirectionally if one is infected
    const [src, dest] = fromState.infected > toState.infected ? [fromState, toState] : [toState, fromState];
    if (src.infected > 300 && dest.infected === 0) {
      // Vector filtering based on deployed countermeasures
      let transmissionBlocked = false;
      if (corridor.mode === 'air_rail' || corridor.mode === 'rail') {
        if (transitRestrictionActive) {
          // Rail lock cuts transit transmission by 80%
          if (Math.random() > 0.20) transmissionBlocked = true;
        }
      }
      if (corridor.mode === 'air_rail') {
        if (airportBioScreeningActive) {
          // Airport screening reduces international/interstate air transmission by 50%
          if (Math.random() > 0.50) transmissionBlocked = true;
        }
      }

      if (!transmissionBlocked) {
        const corridorSpreadChance = (corridor.mode === 'air_rail' ? 0.35 : 0.22) * (infectivity / 60);
        if (Math.random() < corridorSpreadChance) {
          const initialSeeding = Math.round(80 + Math.random() * 200 * (infectivity / 50));
          dest.infected = initialSeeding;
          dest.infectedAtDay = currentDay;
          dest.activeRt = parseFloat(Math.max(1.2, baseRt * 1.1).toFixed(2));
          newlyInfectedStateNames.push(dest.name);
        }
      }
    }
  });

  // 3. Update numbers for all states and classify Severity Tiers
  // Tier thresholds:
  // - 'critical': Bed load > 75% or active infected > 100,000 or (isOrigin && day < 10)
  // - 'moderate': Active infected > 5,000 or Bed load > 45%
  // - 'less': Active infected between 1 and 5,000
  // - 'uninfected': Active infected === 0
  let totalInfectedSum = 0;
  let totalDeceasedSum = 0;
  let totalRecoveredSum = 0;

  const updatedStates: StateOutbreakData[] = Array.from(stateMap.values()).map((st) => {
    if (st.infected > 0) {
      const growthRate = st.activeRt > 1 ? (st.activeRt - 1) * 0.045 : -0.012;
      const deltaInfected = Math.round(st.infected * growthRate);
      const nextInfected = Math.max(10, st.infected + deltaInfected);
      
      const newlyRecovered = Math.round(st.infected * 0.022);
      const nextRecovered = st.recovered + newlyRecovered;
      
      const newlyDeceased = Math.round(st.infected * 0.0008);
      const nextDeceased = st.deceased + newlyDeceased;

      // Hospital bed load capacity ratio
      const estimatedIcuCapacity = Math.max(500, Math.round(st.population * 0.0015));
      const bedLoad = Math.min(99, Math.max(12, Math.round((nextInfected / estimatedIcuCapacity) * 45)));

      // Classify Severity Tier: Critical, Moderate, Less, Uninfected
      let severityTier: 'critical' | 'moderate' | 'less' | 'uninfected' = 'less';
      let status: 'critical' | 'monitored' | 'contained' = 'contained';

      if (bedLoad >= 70 || nextInfected >= 150000 || (st.isOrigin && currentDay <= 12)) {
        severityTier = 'critical';
        status = 'critical';
      } else if (bedLoad >= 40 || nextInfected >= 8000) {
        severityTier = 'moderate';
        status = 'monitored';
      } else {
        severityTier = 'less';
        status = 'contained';
      }

      totalInfectedSum += nextInfected;
      totalDeceasedSum += nextDeceased;
      totalRecoveredSum += nextRecovered;

      return {
        ...st,
        infected: nextInfected,
        recovered: nextRecovered,
        deceased: nextDeceased,
        hospitalBedLoad: bedLoad,
        status,
        severityTier,
      };
    } else {
      return {
        ...st,
        infected: 0,
        recovered: 0,
        deceased: 0,
        hospitalBedLoad: 8,
        status: 'contained',
        severityTier: 'uninfected',
      };
    }
  });

  return {
    updatedStates,
    newlyInfectedStateNames,
    totalInfected: totalInfectedSum,
    totalDeceased: totalDeceasedSum,
    totalRecovered: totalRecoveredSum,
  };
}
