import { useState, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Circle, Marker, Popup, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useApp } from '../App';
import type { RiskLevel } from '../types';
import { Card, RiskBadge, StatusBadge, Select, Btn } from './ui';
import { DISTRICTS } from '../mockData';

// ── Types ─────────────────────────────────────────────────────────────────

interface GeoReport {
  id: string; lat: number; lng: number;
  farmerName: string; farmerPhone: string;
  village: string; block: string; district: string;
  species: string; affectedCount: number; mortalityCount: number;
  riskLevel: RiskLevel; status: string;
  disease?: string; symptoms: string[]; createdAt: string;
}

interface GeoOutbreak {
  id: string; lat: number; lng: number;
  disease: string; district: string; block: string;
  affectedVillages: number; affectedAnimals: number; mortalityCount: number;
  riskLevel: RiskLevel; status: 'active' | 'contained' | 'resolved';
  startDate: string; radius: number;
}

interface GeoFacility {
  id: string; lat: number; lng: number;
  name: string; type: 'vet_center' | 'lab';
  district: string; address: string; phone: string;
}

interface RiskZone {
  id: string; lat: number; lng: number;
  radius: number; riskLevel: RiskLevel; district: string; label: string;
}

// ── Static geo data ────────────────────────────────────────────────────────

const GEO_REPORTS: GeoReport[] = [
  { id: 'RPT-2026-08741', lat: 23.048, lng: 72.512, farmerName: 'Ramesh Patel', farmerPhone: '+91-98765-43210', village: 'Bhadaj', block: 'Daskroi', district: 'Ahmedabad', species: 'Cattle', affectedCount: 8, mortalityCount: 1, riskLevel: 'high', status: 'lab_testing', disease: 'Foot and Mouth Disease (FMD)', symptoms: ['Fever', 'Blisters on tongue/feet', 'Excessive salivation', 'Lameness'], createdAt: '2026-09-10' },
  { id: 'RPT-2026-08810', lat: 23.082, lng: 72.551, farmerName: 'Suresh Chauhan', farmerPhone: '+91-97654-32109', village: 'Ranip', block: 'Daskroi', district: 'Ahmedabad', species: 'Cattle', affectedCount: 4, mortalityCount: 0, riskLevel: 'high', status: 'under_review', disease: 'Lumpy Skin Disease', symptoms: ['Skin nodules', 'Fever', 'Swollen lymph nodes'], createdAt: '2026-09-12' },
  { id: 'RPT-2026-08805', lat: 23.114, lng: 72.032, farmerName: 'Bhavna Solanki', farmerPhone: '+91-96543-21098', village: 'Viramgam', block: 'Viramgam', district: 'Ahmedabad', species: 'Buffalo', affectedCount: 2, mortalityCount: 1, riskLevel: 'critical', status: 'confirmed', disease: 'Black Quarter (BQ)', symptoms: ['Sudden death', 'Swollen legs', 'Bleeding'], createdAt: '2026-09-11' },
  { id: 'RPT-2026-08790', lat: 22.832, lng: 69.353, farmerName: 'Kantilal Mer', farmerPhone: '+91-94321-09876', village: 'Mandvi', block: 'Mandvi', district: 'Kutch', species: 'Camel', affectedCount: 1, mortalityCount: 0, riskLevel: 'low', status: 'assigned', disease: undefined, symptoms: ['Fever', 'Nasal discharge', 'Loss of appetite'], createdAt: '2026-09-09' },
  { id: 'RPT-2026-08770', lat: 24.112, lng: 72.394, farmerName: 'Dhiraj Singh', farmerPhone: '+91-93210-98765', village: 'Danta', block: 'Danta', district: 'Banaskantha', species: 'Cattle', affectedCount: 6, mortalityCount: 3, riskLevel: 'critical', status: 'confirmed', disease: 'Black Quarter (BQ)', symptoms: ['Sudden death', 'Muscle swelling', 'Lameness'], createdAt: '2026-09-11' },
  { id: 'RPT-2026-08752', lat: 22.563, lng: 72.931, farmerName: 'Ravi Patel', farmerPhone: '+91-92109-87654', village: 'Anand', block: 'Anand', district: 'Anand', species: 'Cattle', affectedCount: 5, mortalityCount: 0, riskLevel: 'medium', status: 'under_review', disease: 'Lumpy Skin Disease', symptoms: ['Skin nodules', 'Fever'], createdAt: '2026-09-08' },
  { id: 'RPT-2026-08745', lat: 23.041, lng: 72.519, farmerName: 'Meena Patel', farmerPhone: '+91-91098-76543', village: 'Bhadaj', block: 'Daskroi', district: 'Ahmedabad', species: 'Goat', affectedCount: 3, mortalityCount: 0, riskLevel: 'medium', status: 'resolved', disease: 'PPR (Peste des Petits Ruminants)', symptoms: ['Nasal discharge', 'Coughing'], createdAt: '2026-08-20' },
  { id: 'RPT-2026-08699', lat: 22.302, lng: 70.800, farmerName: 'Arvind Bhai', farmerPhone: '+91-90987-65432', village: 'Gondal', block: 'Gondal', district: 'Rajkot', species: 'Buffalo', affectedCount: 8, mortalityCount: 0, riskLevel: 'medium', status: 'sample_collected', disease: 'Brucellosis', symptoms: ['Abortion', 'Reduced milk production'], createdAt: '2026-08-25' },
  { id: 'RPT-2026-08620', lat: 23.599, lng: 72.384, farmerName: 'Jignesh Shah', farmerPhone: '+91-89876-54321', village: 'Unjha', block: 'Unjha', district: 'Mehsana', species: 'Cattle', affectedCount: 4, mortalityCount: 1, riskLevel: 'high', status: 'confirmed', disease: 'Hemorrhagic Septicemia (HS)', symptoms: ['Fever', 'Swollen throat', 'Difficulty breathing'], createdAt: '2026-09-01' },
  { id: 'RPT-2026-08601', lat: 21.762, lng: 72.158, farmerName: 'Harish Gohil', farmerPhone: '+91-88765-43210', village: 'Ghogha', block: 'Ghogha', district: 'Bhavnagar', species: 'Buffalo', affectedCount: 3, mortalityCount: 0, riskLevel: 'low', status: 'submitted', disease: undefined, symptoms: ['Reduced milk production', 'Fever'], createdAt: '2026-09-12' },
  { id: 'RPT-2026-08588', lat: 22.308, lng: 73.178, farmerName: 'Yogesh Parmar', farmerPhone: '+91-87654-32109', village: 'Savli', block: 'Savli', district: 'Vadodara', species: 'Cattle', affectedCount: 2, mortalityCount: 0, riskLevel: 'low', status: 'assigned', disease: undefined, symptoms: ['Lameness', 'Loss of appetite'], createdAt: '2026-09-10' },
];

const GEO_OUTBREAKS: GeoOutbreak[] = [
  { id: 'OBK-001', lat: 23.055, lng: 72.525, disease: 'Foot and Mouth Disease', district: 'Ahmedabad', block: 'Daskroi', affectedVillages: 7, affectedAnimals: 142, mortalityCount: 3, riskLevel: 'high', status: 'active', startDate: '2026-09-05', radius: 14000 },
  { id: 'OBK-002', lat: 22.563, lng: 72.930, disease: 'Lumpy Skin Disease', district: 'Anand', block: 'Anand', affectedVillages: 4, affectedAnimals: 68, mortalityCount: 0, riskLevel: 'medium', status: 'active', startDate: '2026-09-08', radius: 9000 },
  { id: 'OBK-003', lat: 24.112, lng: 72.394, disease: 'Black Quarter', district: 'Banaskantha', block: 'Danta', affectedVillages: 2, affectedAnimals: 18, mortalityCount: 5, riskLevel: 'critical', status: 'active', startDate: '2026-09-11', radius: 7000 },
  { id: 'OBK-004', lat: 23.025, lng: 69.800, disease: 'PPR', district: 'Kutch', block: 'Bhuj', affectedVillages: 6, affectedAnimals: 210, mortalityCount: 8, riskLevel: 'high', status: 'contained', startDate: '2026-08-28', radius: 16000 },
  { id: 'OBK-005', lat: 23.599, lng: 72.384, disease: 'Hemorrhagic Septicemia', district: 'Mehsana', block: 'Unjha', affectedVillages: 3, affectedAnimals: 44, mortalityCount: 2, riskLevel: 'medium', status: 'active', startDate: '2026-09-01', radius: 8000 },
  { id: 'OBK-006', lat: 22.302, lng: 70.800, disease: 'Brucellosis', district: 'Rajkot', block: 'Gondal', affectedVillages: 5, affectedAnimals: 82, mortalityCount: 0, riskLevel: 'medium', status: 'active', startDate: '2026-08-20', radius: 11000 },
];

const GEO_FACILITIES: GeoFacility[] = [
  { id: 'f1', lat: 23.2156, lng: 72.6369, name: 'GBRC Gandhinagar', type: 'lab', district: 'Gandhinagar', address: 'Sector 11, Gandhinagar', phone: '+91-79-2323-4567' },
  { id: 'f2', lat: 22.5500, lng: 72.9200, name: 'NDDB Laboratory', type: 'lab', district: 'Anand', address: 'NDDB Campus, Anand', phone: '+91-2692-260148' },
  { id: 'f3', lat: 22.5645, lng: 72.9289, name: 'SAU Vet College Lab', type: 'lab', district: 'Anand', address: 'SAU Campus, Anand', phone: '+91-2692-261506' },
  { id: 'f4', lat: 23.0300, lng: 72.5850, name: 'District Vet Hospital, Ahmedabad', type: 'vet_center', district: 'Ahmedabad', address: 'Kochrab, Ahmedabad', phone: '+91-79-2640-1234' },
  { id: 'f5', lat: 23.2502, lng: 69.6693, name: 'District Vet Hospital, Kutch', type: 'vet_center', district: 'Kutch', address: 'Hospital Road, Bhuj', phone: '+91-2832-220123' },
  { id: 'f6', lat: 22.3039, lng: 70.8022, name: 'District Vet Hospital, Rajkot', type: 'vet_center', district: 'Rajkot', address: 'Kalawad Road, Rajkot', phone: '+91-281-234-5678' },
  { id: 'f7', lat: 24.1667, lng: 72.4167, name: 'District Vet Hospital, Banaskantha', type: 'vet_center', district: 'Banaskantha', address: 'Palanpur, Banaskantha', phone: '+91-2742-250123' },
  { id: 'f8', lat: 23.5979, lng: 72.3714, name: 'District Vet Hospital, Mehsana', type: 'vet_center', district: 'Mehsana', address: 'Highway Road, Mehsana', phone: '+91-2762-221234' },
  { id: 'f9', lat: 21.7645, lng: 72.1519, name: 'District Vet Hospital, Bhavnagar', type: 'vet_center', district: 'Bhavnagar', address: 'Wavaria, Bhavnagar', phone: '+91-278-242-3456' },
  { id: 'f10', lat: 22.3072, lng: 73.1812, name: 'District Vet Hospital, Vadodara', type: 'vet_center', district: 'Vadodara', address: 'Akota, Vadodara', phone: '+91-265-234-5678' },
];

const RISK_ZONES: RiskZone[] = [
  { id: 'rz1', lat: 23.02, lng: 72.57, radius: 36000, riskLevel: 'high', district: 'Ahmedabad', label: 'HIGH' },
  { id: 'rz2', lat: 24.17, lng: 72.42, radius: 46000, riskLevel: 'critical', district: 'Banaskantha', label: 'CRITICAL' },
  { id: 'rz3', lat: 23.25, lng: 69.67, radius: 58000, riskLevel: 'high', district: 'Kutch', label: 'HIGH' },
  { id: 'rz4', lat: 22.56, lng: 72.93, radius: 21000, riskLevel: 'medium', district: 'Anand', label: 'MEDIUM' },
  { id: 'rz5', lat: 23.60, lng: 72.38, radius: 26000, riskLevel: 'medium', district: 'Mehsana', label: 'MEDIUM' },
  { id: 'rz6', lat: 22.30, lng: 70.80, radius: 29000, riskLevel: 'medium', district: 'Rajkot', label: 'MEDIUM' },
];

// ── Colour helpers ─────────────────────────────────────────────────────────

const RISK_STROKE: Record<RiskLevel, string> = {
  low:      '#15803d',
  medium:   '#d97706',
  high:     '#dc2626',
  critical: '#7c2d12',
};
const RISK_FILL: Record<RiskLevel, string> = {
  low:      '#dcfce7',
  medium:   '#fef3c7',
  high:     '#fee2e2',
  critical: '#ffedd5',
};

const riskCircleOptions = (level: RiskLevel, opacity = 0.25) => ({
  color: RISK_STROKE[level],
  fillColor: RISK_FILL[level],
  fillOpacity: opacity,
  weight: 2,
  dashArray: '6 4',
});

const reportCircleOptions = (level: RiskLevel) => ({
  color: RISK_STROKE[level],
  fillColor: RISK_STROKE[level],
  fillOpacity: 0.85,
  weight: 2,
});

// ── Custom DivIcon factory ─────────────────────────────────────────────────

function makeFacilityIcon(type: 'vet_center' | 'lab') {
  const emoji = type === 'vet_center' ? '🏥' : '🧪';
  return L.divIcon({
    html: `<div style="font-size:22px;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,0.4))">${emoji}</div>`,
    className: '',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
  });
}

// ── Permission helper ──────────────────────────────────────────────────────

function canSeeFarmerPersonalInfo(role: string) {
  return role === 'admin';
}

function canSeeReport(report: GeoReport, role: string, userDistrict = 'Ahmedabad', userBlock = 'Daskroi') {
  if (role === 'farmer') return false;
  if (role === 'paravet') return report.district === userDistrict && report.block === userBlock;
  if (role === 'vet') return report.district === userDistrict;
  return true; // gov, admin, lab see all
}

// ── Legend ─────────────────────────────────────────────────────────────────

function MapLegend() {
  return (
    <div className="absolute bottom-6 right-3 z-[1000] bg-white border border-[#d1d9d1] rounded-lg shadow-lg p-3 text-xs min-w-[170px]">
      <p className="font-semibold text-gray-700 mb-2 font-display">Legend</p>
      <div className="space-y-1.5">
        <p className="text-gray-500 font-medium uppercase tracking-wide text-[10px] mt-2">Risk Level</p>
        {(['low','medium','high','critical'] as RiskLevel[]).map(r => (
          <div key={r} className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: RISK_STROKE[r], border: `2px solid ${RISK_STROKE[r]}` }} />
            <span className="uppercase font-semibold tracking-wide" style={{ color: RISK_STROKE[r] }}>{r}</span>
          </div>
        ))}
        <p className="text-gray-500 font-medium uppercase tracking-wide text-[10px] mt-3">Layers</p>
        {[
          { icon: '●', label: 'Disease Report', color: '#6b7280' },
          { icon: '○', label: 'Outbreak Cluster', color: '#6b7280' },
          { icon: '⬜', label: 'Risk Zone', color: '#6b7280' },
          { icon: '🏥', label: 'Vet Center', color: '#6b7280' },
          { icon: '🧪', label: 'Laboratory', color: '#6b7280' },
        ].map(({ icon, label }) => (
          <div key={label} className="flex items-center gap-2 text-gray-600">
            <span className="w-4 text-center">{icon}</span>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

interface RiskMapProps {
  userDistrict?: string;
  userBlock?: string;
}

export default function RiskMapLeaflet({ userDistrict = 'Ahmedabad', userBlock = 'Daskroi' }: RiskMapProps) {
  const { role } = useApp();

  // ── Filter state ────────────────────────────────────────────────────────
  const [filterDistrict, setFilterDistrict]   = useState('all');
  const [filterBlock, setFilterBlock]         = useState('');
  const [filterVillage, setFilterVillage]     = useState('');
  const [filterDisease, setFilterDisease]     = useState('all');
  const [filterSpecies, setFilterSpecies]     = useState('all');
  const [filterRisk, setFilterRisk]           = useState<RiskLevel | 'all'>('all');
  const [filterDateFrom, setFilterDateFrom]   = useState('');
  const [filterDateTo, setFilterDateTo]       = useState('');

  const [showReports,   setShowReports]   = useState(true);
  const [showOutbreaks, setShowOutbreaks] = useState(true);
  const [showRiskZones, setShowRiskZones] = useState(true);
  const [showVetCenters,setShowVetCenters]= useState(true);
  const [showLabs,      setShowLabs]      = useState(true);

  const [filtersOpen, setFiltersOpen] = useState(true);

  // ── Filtered data ───────────────────────────────────────────────────────
  const filteredReports = useMemo(() => {
    return GEO_REPORTS.filter(r => {
      if (!canSeeReport(r, role || 'government', userDistrict, userBlock)) return false;
      if (filterDistrict !== 'all' && r.district !== filterDistrict) return false;
      if (filterBlock    && !r.block.toLowerCase().includes(filterBlock.toLowerCase())) return false;
      if (filterVillage  && !r.village.toLowerCase().includes(filterVillage.toLowerCase())) return false;
      if (filterDisease !== 'all' && (!r.disease || !r.disease.toLowerCase().includes(filterDisease.toLowerCase()))) return false;
      if (filterSpecies !== 'all' && r.species !== filterSpecies) return false;
      if (filterRisk    !== 'all' && r.riskLevel !== filterRisk) return false;
      if (filterDateFrom && r.createdAt < filterDateFrom) return false;
      if (filterDateTo   && r.createdAt > filterDateTo)   return false;
      return true;
    });
  }, [role, userDistrict, userBlock, filterDistrict, filterBlock, filterVillage, filterDisease, filterSpecies, filterRisk, filterDateFrom, filterDateTo]);

  const filteredOutbreaks = useMemo(() => {
    return GEO_OUTBREAKS.filter(o => {
      if (filterDistrict !== 'all' && o.district !== filterDistrict) return false;
      if (filterDisease !== 'all' && !o.disease.toLowerCase().includes(filterDisease.toLowerCase())) return false;
      if (filterRisk    !== 'all' && o.riskLevel !== filterRisk) return false;
      return true;
    });
  }, [filterDistrict, filterDisease, filterRisk]);

  const filteredRiskZones = useMemo(() => {
    return RISK_ZONES.filter(z => {
      if (filterDistrict !== 'all' && z.district !== filterDistrict) return false;
      if (filterRisk     !== 'all' && z.riskLevel !== filterRisk) return false;
      return true;
    });
  }, [filterDistrict, filterRisk]);

  const filteredFacilities = useMemo(() => {
    return GEO_FACILITIES.filter(f => {
      if (filterDistrict !== 'all' && f.district !== filterDistrict) return false;
      if (!showVetCenters && f.type === 'vet_center') return false;
      if (!showLabs       && f.type === 'lab')        return false;
      return true;
    });
  }, [filterDistrict, showVetCenters, showLabs]);

  const resetFilters = () => {
    setFilterDistrict('all'); setFilterBlock(''); setFilterVillage('');
    setFilterDisease('all'); setFilterSpecies('all'); setFilterRisk('all');
    setFilterDateFrom(''); setFilterDateTo('');
  };

  const showPersonalInfo = canSeeFarmerPersonalInfo(role || '');

  // ── Summary counts ──────────────────────────────────────────────────────
  const criticalCount = filteredReports.filter(r => r.riskLevel === 'critical').length;
  const highCount     = filteredReports.filter(r => r.riskLevel === 'high').length;
  const activeOutbreaks = filteredOutbreaks.filter(o => o.status === 'active').length;

  return (
    <div className="flex flex-col h-full min-h-[600px]">
      {/* Top bar */}
      <div className="flex items-center justify-between gap-4 px-1 pb-3 flex-wrap">
        <div className="flex items-center gap-4 flex-wrap text-sm">
          <span className="flex items-center gap-1.5 text-red-700 font-semibold">
            <span className="w-2.5 h-2.5 rounded-full bg-red-600" />
            {criticalCount} Critical
          </span>
          <span className="flex items-center gap-1.5 text-orange-700 font-semibold">
            <span className="w-2.5 h-2.5 rounded-full bg-orange-500" />
            {highCount} High
          </span>
          <span className="flex items-center gap-1.5 text-gray-600">
            <span className="w-2.5 h-2.5 rounded-full bg-gray-400" />
            {activeOutbreaks} Active Outbreaks
          </span>
          <span className="text-gray-400 text-xs">
            {filteredReports.length} report{filteredReports.length !== 1 ? 's' : ''} shown
          </span>
        </div>
        <Btn variant="ghost" size="sm" onClick={() => setFiltersOpen(o => !o)}>
          {filtersOpen ? '← Hide Filters' : 'Filters →'}
        </Btn>
      </div>

      <div className="flex flex-1 gap-4 min-h-0">
        {/* ── Filter panel ──────────────────────────────────────────────── */}
        {filtersOpen && (
          <div className="w-64 flex-shrink-0 overflow-y-auto bg-white border border-[#d1d9d1] rounded-lg">
            <div className="p-4 border-b border-[#d1d9d1] flex items-center justify-between">
              <span className="font-display font-600 text-sm text-gray-800">Filters</span>
              <button onClick={resetFilters} className="text-xs text-[#166534] hover:underline font-medium">Reset all</button>
            </div>

            <div className="p-4 space-y-4">
              {/* Location filters */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Location</p>
                <div className="space-y-2">
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">District</label>
                    <Select value={filterDistrict} onChange={setFilterDistrict}>
                      <option value="all">All Districts</option>
                      {DISTRICTS.map(d => <option key={d}>{d}</option>)}
                    </Select>
                  </div>
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">Block / Taluka</label>
                    <input value={filterBlock} onChange={e => setFilterBlock(e.target.value)}
                      placeholder="e.g. Daskroi"
                      className="w-full border border-[#d1d9d1] rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#166534]" />
                  </div>
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">Village</label>
                    <input value={filterVillage} onChange={e => setFilterVillage(e.target.value)}
                      placeholder="e.g. Bhadaj"
                      className="w-full border border-[#d1d9d1] rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#166534]" />
                  </div>
                </div>
              </div>

              {/* Disease filter */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Disease</p>
                <Select value={filterDisease} onChange={setFilterDisease}>
                  <option value="all">All Diseases</option>
                  {['FMD','Lumpy Skin','Black Quarter','PPR','Hemorrhagic Septicemia','Brucellosis','Theileriosis'].map(d => (
                    <option key={d}>{d}</option>
                  ))}
                </Select>
              </div>

              {/* Species filter */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Species</p>
                <Select value={filterSpecies} onChange={setFilterSpecies}>
                  <option value="all">All Species</option>
                  {['Cattle','Buffalo','Goat','Sheep','Camel'].map(s => <option key={s}>{s}</option>)}
                </Select>
              </div>

              {/* Risk level filter */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Risk Level</p>
                <div className="space-y-1.5">
                  {(['all','low','medium','high','critical'] as const).map(r => (
                    <button key={r} onClick={() => setFilterRisk(r)}
                      className={`w-full text-left px-2.5 py-1.5 rounded text-sm flex items-center gap-2 transition-colors
                        ${filterRisk === r ? 'bg-[#166534] text-white' : 'text-gray-700 hover:bg-gray-50'}`}>
                      {r !== 'all' && (
                        <span className="w-3 h-3 rounded-sm flex-shrink-0"
                          style={{ background: filterRisk === r ? 'white' : RISK_STROKE[r as RiskLevel] }} />
                      )}
                      <span className="font-medium uppercase tracking-wide text-xs">
                        {r === 'all' ? 'All Levels' : r}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Date filter */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Date Range</p>
                <div className="space-y-2">
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">From</label>
                    <input type="date" value={filterDateFrom} onChange={e => setFilterDateFrom(e.target.value)}
                      className="w-full border border-[#d1d9d1] rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#166534]" />
                  </div>
                  <div>
                    <label className="text-xs text-gray-600 block mb-1">To</label>
                    <input type="date" value={filterDateTo} onChange={e => setFilterDateTo(e.target.value)}
                      className="w-full border border-[#d1d9d1] rounded px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#166534]" />
                  </div>
                </div>
              </div>

              {/* Layer toggles */}
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Layers</p>
                <div className="space-y-1.5">
                  {[
                    { label: '● Disease Reports', state: showReports,    set: setShowReports },
                    { label: '○ Outbreak Clusters',state: showOutbreaks,  set: setShowOutbreaks },
                    { label: '⬜ Risk Zones',       state: showRiskZones, set: setShowRiskZones },
                    { label: '🏥 Vet Centers',      state: showVetCenters,set: setShowVetCenters },
                    { label: '🧪 Laboratories',     state: showLabs,      set: setShowLabs },
                  ].map(({ label, state, set }) => (
                    <label key={label} className="flex items-center gap-2 cursor-pointer select-none">
                      <input type="checkbox" checked={state} onChange={e => set(e.target.checked)}
                        className="w-4 h-4 accent-[#166534] cursor-pointer" />
                      <span className="text-sm text-gray-700">{label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {!showPersonalInfo && (
                <div className="bg-amber-50 border border-amber-200 rounded p-2.5 text-xs text-amber-700">
                  <p className="font-semibold">🔒 Privacy Notice</p>
                  <p className="mt-0.5">Farmer names and contact details are not shown at this permission level.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Map area ───────────────────────────────────────────────────── */}
        <div className="flex-1 relative rounded-lg overflow-hidden border border-[#d1d9d1] min-h-[500px]">
          <MapContainer
            center={[22.5, 71.5]}
            zoom={7}
            style={{ height: '100%', width: '100%', minHeight: 500 }}
            zoomControl={true}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {/* Risk Zones (broadest, rendered first / lowest z-index) */}
            {showRiskZones && filteredRiskZones.map(zone => (
              <Circle key={zone.id}
                center={[zone.lat, zone.lng]}
                radius={zone.radius}
                pathOptions={{ ...riskCircleOptions(zone.riskLevel, 0.15), weight: 1.5 }}>
                <Tooltip permanent direction="center" className="risk-zone-label">
                  <span style={{
                    fontSize: 10, fontWeight: 700, color: RISK_STROKE[zone.riskLevel],
                    letterSpacing: '0.08em', fontFamily: 'Work Sans, sans-serif',
                  }}>
                    {zone.label}
                  </span>
                </Tooltip>
              </Circle>
            ))}

            {/* Outbreak Clusters */}
            {showOutbreaks && filteredOutbreaks.map(o => (
              <Circle key={o.id}
                center={[o.lat, o.lng]}
                radius={o.radius}
                pathOptions={{
                  color: RISK_STROKE[o.riskLevel],
                  fillColor: RISK_FILL[o.riskLevel],
                  fillOpacity: 0.22,
                  weight: 2.5,
                  dashArray: o.status === 'contained' ? '8 4' : '4 3',
                }}>
                <Popup maxWidth={280}>
                  <OutbreakPopup outbreak={o} />
                </Popup>
                <Tooltip direction="top">
                  <span className="font-semibold text-xs">{o.disease}</span>
                </Tooltip>
              </Circle>
            ))}

            {/* Disease Reports */}
            {showReports && filteredReports.map(r => (
              <CircleMarker key={r.id}
                center={[r.lat, r.lng]}
                radius={r.riskLevel === 'critical' ? 11 : r.riskLevel === 'high' ? 9 : r.riskLevel === 'medium' ? 7 : 6}
                pathOptions={reportCircleOptions(r.riskLevel)}>
                <Popup maxWidth={300} minWidth={260}>
                  <ReportPopup report={r} showPersonalInfo={showPersonalInfo} />
                </Popup>
                <Tooltip direction="top">
                  <span className="text-xs">{r.id} · {r.village}</span>
                </Tooltip>
              </CircleMarker>
            ))}

            {/* Facilities (Vet Centers + Labs) */}
            {filteredFacilities.map(f => (
              <Marker key={f.id}
                position={[f.lat, f.lng]}
                icon={makeFacilityIcon(f.type)}>
                <Popup maxWidth={260}>
                  <FacilityPopup facility={f} />
                </Popup>
              </Marker>
            ))}
          </MapContainer>

          {/* Legend overlay */}
          <MapLegend />
        </div>
      </div>
    </div>
  );
}

// ── Popup components ───────────────────────────────────────────────────────

function ReportPopup({ report, showPersonalInfo }: { report: GeoReport; showPersonalInfo: boolean }) {
  const riskColor = RISK_STROKE[report.riskLevel];
  return (
    <div style={{ fontFamily: 'Inter, sans-serif', minWidth: 240 }}>
      <div style={{ borderBottom: '1px solid #e9ede9', paddingBottom: 6, marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#6b7280' }}>{report.id}</span>
          <span style={{
            fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
            color: riskColor, background: RISK_FILL[report.riskLevel],
            border: `1px solid ${riskColor}`, letterSpacing: '0.06em',
          }}>
            {report.riskLevel.toUpperCase()}
          </span>
        </div>
        <p style={{ fontWeight: 700, fontSize: 14, color: '#111827', margin: '4px 0 2px' }}>
          {report.village}, {report.block}
        </p>
        <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>{report.district} · {report.species}</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 12, marginBottom: 8 }}>
        <div>
          <p style={{ color: '#9ca3af', fontSize: 10, marginBottom: 1 }}>AFFECTED</p>
          <p style={{ fontWeight: 600, color: '#111827' }}>{report.affectedCount} animals</p>
        </div>
        <div>
          <p style={{ color: '#9ca3af', fontSize: 10, marginBottom: 1 }}>DEATHS</p>
          <p style={{ fontWeight: 600, color: report.mortalityCount > 0 ? '#dc2626' : '#111827' }}>
            {report.mortalityCount}
          </p>
        </div>
        <div>
          <p style={{ color: '#9ca3af', fontSize: 10, marginBottom: 1 }}>DISEASE</p>
          <p style={{ fontWeight: 600, color: '#111827', fontSize: 11 }}>{report.disease || 'Under investigation'}</p>
        </div>
        <div>
          <p style={{ color: '#9ca3af', fontSize: 10, marginBottom: 1 }}>DATE</p>
          <p style={{ fontWeight: 600, color: '#111827' }}>{report.createdAt}</p>
        </div>
      </div>

      {report.symptoms.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <p style={{ color: '#9ca3af', fontSize: 10, marginBottom: 3 }}>SYMPTOMS</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            {report.symptoms.map(s => (
              <span key={s} style={{ fontSize: 10, padding: '1px 5px', background: '#f3f4f6', borderRadius: 3, color: '#374151' }}>{s}</span>
            ))}
          </div>
        </div>
      )}

      <div style={{ borderTop: '1px solid #e9ede9', paddingTop: 6, fontSize: 11 }}>
        <span style={{
          padding: '1px 6px', borderRadius: 3, fontSize: 10, fontWeight: 600,
          background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0',
        }}>
          {report.status.replace(/_/g, ' ')}
        </span>
      </div>

      {showPersonalInfo && (
        <div style={{ marginTop: 6, paddingTop: 6, borderTop: '1px solid #e9ede9', fontSize: 11 }}>
          <p style={{ color: '#6b7280', marginBottom: 2 }}>👤 {report.farmerName}</p>
          <p style={{ color: '#6b7280' }}>📞 {report.farmerPhone}</p>
        </div>
      )}
    </div>
  );
}

function OutbreakPopup({ outbreak }: { outbreak: GeoOutbreak }) {
  const riskColor = RISK_STROKE[outbreak.riskLevel];
  return (
    <div style={{ fontFamily: 'Inter, sans-serif', minWidth: 230 }}>
      <div style={{ borderBottom: '1px solid #e9ede9', paddingBottom: 6, marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#6b7280' }}>{outbreak.id}</span>
          <span style={{
            fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
            color: riskColor, background: RISK_FILL[outbreak.riskLevel],
            border: `1px solid ${riskColor}`, letterSpacing: '0.06em',
          }}>
            {outbreak.riskLevel.toUpperCase()}
          </span>
        </div>
        <p style={{ fontWeight: 700, fontSize: 14, color: '#111827', margin: '4px 0 2px' }}>
          🔴 {outbreak.disease}
        </p>
        <p style={{ fontSize: 12, color: '#6b7280', margin: 0 }}>
          {outbreak.district} · {outbreak.block}
        </p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, fontSize: 12, textAlign: 'center', marginBottom: 8 }}>
        {[['Villages', outbreak.affectedVillages], ['Animals', outbreak.affectedAnimals], ['Deaths', outbreak.mortalityCount]].map(([k, v]) => (
          <div key={k} style={{ background: '#f9fafb', borderRadius: 4, padding: '4px 2px' }}>
            <p style={{ fontWeight: 700, fontSize: 16, color: Number(v) > 0 && k === 'Deaths' ? '#dc2626' : '#111827', margin: 0 }}>{v}</p>
            <p style={{ color: '#9ca3af', fontSize: 10, margin: 0 }}>{k}</p>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11, color: '#6b7280' }}>
        Started: {outbreak.startDate} &nbsp;·&nbsp;
        <span style={{ fontWeight: 600, color: outbreak.status === 'active' ? '#dc2626' : outbreak.status === 'contained' ? '#d97706' : '#15803d' }}>
          {outbreak.status.toUpperCase()}
        </span>
      </div>
    </div>
  );
}

function FacilityPopup({ facility }: { facility: GeoFacility }) {
  return (
    <div style={{ fontFamily: 'Inter, sans-serif', minWidth: 220 }}>
      <p style={{ fontWeight: 700, fontSize: 14, color: '#111827', margin: '0 0 4px' }}>
        {facility.type === 'vet_center' ? '🏥' : '🧪'} {facility.name}
      </p>
      <p style={{ fontSize: 12, color: '#6b7280', margin: '0 0 4px' }}>{facility.district}</p>
      <p style={{ fontSize: 11, color: '#9ca3af', margin: '0 0 4px' }}>{facility.address}</p>
      <p style={{ fontSize: 12, color: '#166534', fontWeight: 600, margin: 0 }}>📞 {facility.phone}</p>
      <span style={{
        display: 'inline-block', marginTop: 6, fontSize: 10, fontWeight: 600,
        padding: '1px 6px', borderRadius: 3,
        background: facility.type === 'vet_center' ? '#f0fdf4' : '#eff6ff',
        color: facility.type === 'vet_center' ? '#166534' : '#1d4ed8',
        border: `1px solid ${facility.type === 'vet_center' ? '#bbf7d0' : '#bfdbfe'}`,
      }}>
        {facility.type === 'vet_center' ? 'Veterinary Centre' : 'Laboratory'}
      </span>
    </div>
  );
}
