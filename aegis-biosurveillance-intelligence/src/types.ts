export type PageView = 
  | 'overview' 
  | 'simulation' 
  | 'analysis' 
  | 'backtesting' 
  | 'reports';

export type PathogenTargetId = 'sars-cov-2' | 'h5n1' | 'nipah' | 'acinetobacter';

export interface PathogenTarget {
  id: PathogenTargetId;
  name: string;
  code: string;
  classification: string;
  baseR0: number;
  baseIFR: number;
  baseInfectivity: number;
  baseSeverity: number;
  baseLethality: number;
  defaultRt: number;
  incubationDays: number;
  serialInterval: number;
  description: string;
  initialEpicenter: string;
}

export interface StateOutbreakData {
  id: string;
  code: string;
  name: string;
  subRegion: string;
  x: number; // SVG coordinate
  y: number; // SVG coordinate
  population: number;
  infected: number;
  recovered: number;
  deceased: number;
  activeRt: number;
  status: 'critical' | 'monitored' | 'contained';
  severityTier?: 'critical' | 'moderate' | 'less' | 'uninfected';
  hospitalBedLoad: number; // percentage
  airHub: boolean;
  railJunction: boolean;
  infectedAtDay?: number;
  isOrigin?: boolean;
}

export interface SimulationTrait {
  id: string;
  name: string;
  category: 'transmission' | 'symptoms' | 'abilities';
  cost: number;
  unlocked: boolean;
  infectivityDelta: number;
  severityDelta: number;
  lethalityDelta: number;
  description: string;
  iconName: string;
}

export interface CountermeasureItem {
  id: string;
  name: string;
  target: string;
  deployed: boolean;
  cost: number;
  efficacy: number; // % reduction in transmission
  statusLabel: string;
  icon: string;
}

export interface SEIRDataPoint {
  day: number;
  label: string;
  susceptible: number;
  exposed: number;
  infectious: number;
  recovered: number;
  deceased: number;
  realObserved?: number;
  classicSEIR: number;
  neuralSEIR: number;
  ciLower: number;
  ciUpper: number;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: 'Chief Epidemiologist' | 'Lead Biostatistician' | 'Clinical Officer' | 'Public Health Analyst';
  credentialId: string;
  clearanceLevel: string;
  organization: string;
  verifiedAt: string;
}

export interface SimulationState {
  day: number;
  maxDays: number;
  isRunning: boolean;
  speed: 1 | 2 | 5;
  dnaPoints: number;
  infectivity: number; // 0 - 100
  severity: number;    // 0 - 100
  lethality: number;   // 0 - 100
  totalInfected: number;
  totalRecovered: number;
  totalDeceased: number;
  currentRt: number;
  containmentIndex: number;
  countermeasureEfficacy: number;
  targetPathogen: PathogenTargetId;
  traits: SimulationTrait[];
  countermeasures: CountermeasureItem[];
  states: StateOutbreakData[];
  tickerMessage: string;
  originStateId?: string;
  originCity?: string;
}
