const COVID_API_BASE = 'https://data.incovid19.org/v4/min';

export interface CovidStateData {
  cases: number;
  recovered: number;
  deceased: number;
  tested: number;
  vaccinated1: number;
  vaccinated2: number;
}

export interface CovidApiResponse {
  [stateCode: string]: {
    total?: CovidStateData;
    delta?: CovidStateData;
    delta7?: CovidStateData;
  };
}

export async function fetchCovidData(): Promise<CovidApiResponse> {
  try {
    const response = await fetch(`${COVID_API_BASE}/timeseries.min.json`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    return data;
  } catch (err) {
    console.error('Failed to fetch COVID data:', err);
    return {};
  }
}

export async function fetchStateTimeseries(stateCode: string): Promise<Record<string, unknown>> {
  try {
    const response = await fetch(`${COVID_API_BASE}/timeseries-${stateCode}.min.json`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (err) {
    console.error(`Failed to fetch timeseries for ${stateCode}:`, err);
    return {};
  }
}

// Map our state names to COVID API state codes
export const STATE_CODE_MAP: Record<string, string> = {
  'Maharashtra': 'MH',
  'Delhi': 'DL',
  'Karnataka': 'KA',
  'Kerala': 'KL',
  'Tamil Nadu': 'TN',
  'West Bengal': 'WB',
  'Uttar Pradesh': 'UP',
  'Gujarat': 'GJ',
  'Rajasthan': 'RJ',
  'Madhya Pradesh': 'MP',
  'Telangana': 'TG',
  'Andhra Pradesh': 'AP',
  'Assam': 'AS',
  'Jammu & Kashmir': 'JK',
  'Punjab': 'PB',
  'Odisha': 'OR',
  'Bihar': 'BR',
  'Chhattisgarh': 'CT',
  'Jharkhand': 'JH',
  'Uttarakhand': 'UK',
  'Himachal Pradesh': 'HP',
  'Goa': 'GA',
  'Tripura': 'TR',
  'Manipur': 'MN',
  'Meghalaya': 'ML',
  'Nagaland': 'NL',
  'Arunachal Pradesh': 'AR',
  'Mizoram': 'MZ',
  'Sikkim': 'SK',
  'Haryana': 'HR',
  'Chandigarh': 'CH',
  'Puducherry': 'PY',
  'Andaman & Nicobar': 'AN',
  'Dadra & Nagar Haveli': 'DN',
  'Daman & Diu': 'DD',
  'Lakshadweep': 'LD',
  'Ladakh': 'LA',
};
