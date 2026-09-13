// SVG Path data and utilities for official India States & Union Territories
import { RAW_STATE_PATHS } from './statePathConstants';

export interface StatePathDefinition {
  id: string;
  name: string;
  d: string;
}

export function getStatePath(stateId: string): string | undefined {
  return RAW_STATE_PATHS[stateId]?.d;
}

export function getAllStatePaths(): { id: string; title: string; d: string }[] {
  return Object.entries(RAW_STATE_PATHS).map(([id, val]) => ({
    id,
    title: val.title,
    d: val.d,
  }));
}
