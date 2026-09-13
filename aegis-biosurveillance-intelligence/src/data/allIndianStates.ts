import { StateOutbreakData } from '../types';
import { STATE_CENTER_COORDS } from './indiaMapPaths';

// Initial state outbreak data for all 37 Indian states and UTs
export function createInitialStatesData(originStateKey: string = 'Maharashtra'): StateOutbreakData[] {
  return Object.entries(STATE_CENTER_COORDS).map(([key, info]) => {
    const isOrigin = key === originStateKey;
    const initialInfected = isOrigin ? 1200 : 0;
    const initialRt = isOrigin ? 2.45 : 0.95;
    const initialBedLoad = isOrigin ? 32 : 12;

    return {
      id: key,
      code: key.substring(0, 3).toUpperCase(),
      name: info.name,
      subRegion: `${info.name} Sector`,
      x: info.cx,
      y: info.cy,
      population: info.pop,
      infected: initialInfected,
      recovered: 0,
      deceased: isOrigin ? 8 : 0,
      activeRt: initialRt,
      status: isOrigin ? 'critical' : 'contained',
      severityTier: isOrigin ? 'critical' : 'uninfected',
      hospitalBedLoad: initialBedLoad,
      airHub: info.airHub,
      railJunction: info.railJunction,
      infectedAtDay: isOrigin ? 0 : undefined,
      isOrigin: isOrigin,
    };
  });
}
