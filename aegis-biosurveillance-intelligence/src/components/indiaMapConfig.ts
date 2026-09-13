import { PathData } from './indiaMapPaths';

// Mapping from SVG path IDs to display names
export const STATE_ID_MAP: Record<string, string> = {
  Andaman_and_Nicobar_Island: 'Andaman & Nicobar',
  Andhra_Pradesh: 'Andhra Pradesh',
  Arunachal_Pradesh: 'Arunachal Pradesh',
  Assam: 'Assam',
  Bihar: 'Bihar',
  Chandigarh: 'Chandigarh',
  Chhattisgarh: 'Chhattisgarh',
  Dadara_and_Nagar_Havelli: 'Dadra & Nagar Haveli',
  Daman_and_Diu: 'Daman & Diu',
  Goa: 'Goa',
  Gujarat: 'Gujarat',
  Haryana: 'Haryana',
  Himachal_Pradesh: 'Himachal Pradesh',
  Jammu_and_Kashmir: 'Jammu & Kashmir',
  Jharkhand: 'Jharkhand',
  Karnataka: 'Karnataka',
  Kerala: 'Kerala',
  Ladakh: 'Ladakh',
  Lakshadweep: 'Lakshadweep',
  Madhya_Pradesh: 'Madhya Pradesh',
  Maharashtra: 'Maharashtra',
  Manipur: 'Manipur',
  Meghalaya: 'Meghalaya',
  Mizoram: 'Mizoram',
  NCT_of_Delhi: 'Delhi',
  Nagaland: 'Nagaland',
  Odisha: 'Odisha',
  Puducherry: 'Puducherry',
  Punjab: 'Punjab',
  Rajasthan: 'Rajasthan',
  Sikkim: 'Sikkim',
  Tamil_Nadu: 'Tamil Nadu',
  Telangana: 'Telangana',
  Tripura: 'Tripura',
  Uttar_Pradesh: 'Uttar Pradesh',
  Uttarakhand: 'Uttarakhand',
  West_Bengal: 'West Bengal',
};

// Reverse mapping: display name -> SVG ID
export const DISPLAY_TO_SVG_ID: Record<string, string> = {};
Object.entries(STATE_ID_MAP).forEach(([svgId, display]) => {
  DISPLAY_TO_SVG_ID[display] = svgId;
});
