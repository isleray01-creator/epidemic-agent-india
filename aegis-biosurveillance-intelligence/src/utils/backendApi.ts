/**
 * EpiPulse Backend API Client
 * Connects the React frontend to the Python epidemic-agent-india backend
 * via the FastAPI bridge server running on port 8000.
 */

const API_BASE = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_URL) || 'http://localhost:8000';

export interface SimulateRequest {
  model_type?: string;
  states?: string[];
  variant?: string;
  days?: number;
  interventions?: string[];
  initial_infected?: number;
  population?: number;
}

export interface SimulationResult {
  daily_cases: Record<string, number[]>;
  daily_deaths: Record<string, number[]>;
  daily_Rt: Record<string, number[]>;
  cumulative_cases: Record<string, number[]>;
  cumulative_deaths: Record<string, number[]>;
  peak_day: Record<string, number>;
  peak_cases: Record<string, number>;
  total_deaths: Record<string, number>;
  final_infected: Record<string, number>;
  metadata: Record<string, unknown>;
}

export interface StateInfo {
  name: string;
  population: number;
}

export interface VariantParams {
  R0: number;
  IFR: number;
  immune_escape: number;
  serial_interval: number;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }
  return response.json();
}

export async function healthCheck(): Promise<{ status: string; version: string; backend: string }> {
  return apiFetch('/api/health');
}

export async function getVariants(): Promise<Record<string, VariantParams>> {
  const data = await apiFetch<{ variants: Record<string, VariantParams> }>('/api/config/variants');
  return data.variants;
}

export async function getStates(): Promise<StateInfo[]> {
  const data = await apiFetch<{ states: StateInfo[] }>('/api/config/states');
  return data.states;
}

export async function simulate(req: SimulateRequest = {}): Promise<{ success: boolean; result: SimulationResult }> {
  return apiFetch('/api/simulate', {
    method: 'POST',
    body: JSON.stringify({
      model_type: 'seir',
      states: ['Maharashtra', 'Kerala', 'Delhi'],
      variant: 'wildtype',
      days: 60,
      interventions: ['contact_tracing'],
      initial_infected: 100,
      ...req,
    }),
  });
}

export async function simulateSEIR(req: SimulateRequest = {}): Promise<SimulationResult> {
  return apiFetch('/api/simulate/seir', {
    method: 'POST',
    body: JSON.stringify({
      states: ['Maharashtra', 'Kerala', 'Delhi'],
      variant: 'wildtype',
      days: 60,
      interventions: ['contact_tracing'],
      initial_infected: 100,
      ...req,
    }),
  });
}

export async function runWorkflow(req: SimulateRequest = {}): Promise<{ success: boolean; result: Record<string, unknown> }> {
  return apiFetch('/api/workflow/run', {
    method: 'POST',
    body: JSON.stringify({
      states: ['Maharashtra', 'Kerala', 'Delhi'],
      variant: 'wildtype',
      days: 60,
      interventions: ['contact_tracing'],
      initial_infected: 100,
      ...req,
    }),
  });
}
