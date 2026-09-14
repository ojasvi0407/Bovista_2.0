import { useState } from 'react';
import { useApp } from '../../App';
import LiveWorkspaceStatus from '../../components/LiveWorkspaceStatus';
import RiskMapLeaflet from '../../components/RiskMapLeaflet';
import {
  Card, CardHeader, StatCard, Btn, RiskBadge, StatusBadge, Table, TR, TD,
  AlertBanner, SectionHeader, Select, Tabs,
} from '../../components/ui';
import { mockReports, mockOutbreaks, trendData, vaccinationCoverageData, DISTRICTS } from '../../mockData';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

type Screen = 'command' | 'riskmap' | 'outbreaks' | 'trends' | 'vaccination' | 'reports';

const SIDEBAR = [
  { id: 'command',    icon: '🏛️', label: 'Command Center' },
  { id: 'riskmap',    icon: '🗺️', label: 'Risk Map' },
  { id: 'outbreaks',  icon: '🔴', label: 'Outbreaks' },
  { id: 'trends',     icon: '📈', label: 'Disease Trends' },
  { id: 'vaccination',icon: '💉', label: 'Vaccination' },
  { id: 'reports',    icon: '📊', label: 'Reports' },
] as const;

export default function GovApp() {
  const { logout } = useApp();
  const [screen, setScreen] = useState<Screen>('command');

  return (
    <div className="min-h-screen bg-[#f7f9f7] flex flex-col">
      <header className="bg-[#166534] text-white px-6 py-3 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="text-xl">🏛️</div>
          <div>
            <span className="font-display font-700 text-base">PashuMitra</span>
            <span className="text-green-300 text-xs ml-2">Government Surveillance Portal</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-green-200 hidden sm:block">IAS Mihir Bhatt · AHD Gujarat</span>
          <span className="text-xs bg-red-700 text-white px-2 py-0.5 rounded-full font-mono animate-pulse">LIVE</span>
          <button onClick={logout} className="text-green-200 text-xs border border-green-600 px-3 py-1.5 rounded hover:bg-white/10">Log out</button>
        </div>
      </header>

      <div className="flex flex-1">
        <aside className="bg-white border-r border-[#d1d9d1] w-56 flex-shrink-0 hidden lg:flex flex-col sticky top-16 h-[calc(100vh-56px)]">
          <nav className="flex-1 py-4">
            {SIDEBAR.map(s => (
              <button key={s.id} onClick={() => setScreen(s.id as Screen)}
                aria-current={screen === s.id ? 'page' : undefined}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium
                  ${screen === s.id ? 'bg-green-50 text-[#166534] border-r-2 border-[#166534]' : 'text-gray-600 hover:bg-gray-50'}`}>
                <span>{s.icon}</span> {s.label}
              </button>
            ))}
          </nav>
          <div className="p-4 border-t border-[#d1d9d1] text-xs text-gray-400 space-y-0.5">
            <p>Gujarat State</p>
            <p>Data as of: 12 Sep 2026</p>
            <p className="text-green-600 font-medium">● All systems operational</p>
          </div>
        </aside>

        <main className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto px-6 py-6">
            {screen === 'command'    && <CommandCenter setScreen={setScreen} />}
            {screen === 'riskmap'    && <RiskMap />}
            {screen === 'outbreaks'  && <OutbreaksView />}
            {screen === 'trends'     && <DiseaseTrends />}
            {screen === 'vaccination'&& <VaccinationCoverage />}
            {screen === 'reports'    && <GovReports />}
          </div>
        </main>
      </div>
    </div>
  );
}

function CommandCenter({ setScreen }: any) {
  const { workspace } = useApp();
  const summary = workspace.dashboard?.[0] as { totals?: Record<string, number | string> } | undefined;
  const totals = summary?.totals ?? {};
  return (
    <div className="space-y-6">
      <LiveWorkspaceStatus />
      <div className="flex items-start justify-between flex-wrap gap-3">
        <SectionHeader title="Command Center" subtitle="Gujarat State Animal Health — Live Dashboard" />
        <span className="text-xs bg-red-50 text-red-700 border border-red-200 px-3 py-1.5 rounded-lg font-medium">
          ⚠ 3 active outbreaks requiring immediate action
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Active Outbreaks" value={totals.active_outbreaks ?? 0} sub="state-wide" accent="red" />
        <StatCard label="Disease Reports" value={totals.disease_reports ?? 0} sub="authorized period" accent="amber" />
        <StatCard label="Animals Affected" value={totals.total_animals ?? 0} sub="authorized scope" accent="red" />
        <StatCard label="Mortality" value={totals.mortality ?? 0} sub="authorized period" accent="red" />
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="Districts Under Alert" value="4" sub="FMD, LSD, BQ" accent="amber" />
        <StatCard label="Vaccine Coverage (FMD)" value="81%" sub="state average" accent="green" />
        <StatCard label="Active Field Teams" value="28" sub="para-vets + vets" accent="green" />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Critical Outbreak Alerts" action={<Btn variant="ghost" size="sm" onClick={() => setScreen('outbreaks')}>All →</Btn>} />
          <div className="divide-y divide-[#e9ede9]">
            {mockOutbreaks.filter(o => o.status === 'active').map(o => (
              <div key={o.id} className="px-4 py-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <RiskBadge level={o.riskLevel} compact />
                      <span className="font-semibold text-sm text-gray-800">{o.disease}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{o.district} · {o.block} · {o.affectedVillages} villages</p>
                    <p className="text-xs text-gray-500">{o.affectedAnimals} animals · {o.mortalityCount} deaths</p>
                  </div>
                  <span className="text-xs text-gray-400 whitespace-nowrap">{o.startDate}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="Disease Reports — Last 7 Days" />
          <div className="p-4 h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={trendData.slice(-3)} barGap={2}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e9ede9" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="FMD" fill="#dc2626" radius={[2,2,0,0]} />
                <Bar dataKey="LSD" fill="#b45309" radius={[2,2,0,0]} />
                <Bar dataKey="BQ" fill="#7c3aed" radius={[2,2,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title="District Risk Status" subtitle="Updated hourly" />
        <div className="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {[
            { district: 'Ahmedabad', risk: 'high' as const, reports: 12 },
            { district: 'Banaskantha', risk: 'critical' as const, reports: 8 },
            { district: 'Kutch', risk: 'high' as const, reports: 7 },
            { district: 'Anand', risk: 'medium' as const, reports: 5 },
            { district: 'Mehsana', risk: 'medium' as const, reports: 4 },
            { district: 'Rajkot', risk: 'medium' as const, reports: 3 },
            { district: 'Vadodara', risk: 'low' as const, reports: 2 },
            { district: 'Surat', risk: 'low' as const, reports: 1 },
          ].map(({ district, risk, reports }) => (
            <div key={district} className={`p-3 rounded-lg border text-sm
              ${risk === 'critical' ? 'border-red-300 bg-red-50' :
                risk === 'high' ? 'border-red-200 bg-red-50/50' :
                risk === 'medium' ? 'border-amber-200 bg-amber-50/50' :
                'border-green-200 bg-green-50/50'}`}>
              <p className="font-semibold text-gray-800">{district}</p>
              <RiskBadge level={risk} compact />
              <p className="text-xs text-gray-500 mt-1">{reports} reports</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function RiskMap() {
  return (
    <div className="space-y-4" style={{ height: 'calc(100vh - 220px)', minHeight: 600 }}>
      <SectionHeader title="Risk Map" subtitle="Gujarat State — Live Disease Surveillance · OpenStreetMap" />
      <div className="flex-1" style={{ height: 'calc(100% - 60px)' }}>
        <RiskMapLeaflet />
      </div>
    </div>
  );
}

function OutbreaksView() {
  return (
    <div className="space-y-5">
      <SectionHeader title="Outbreak Management" subtitle="All active and recent outbreaks" />
      <div className="grid sm:grid-cols-3 gap-4">
        <StatCard label="Active" value={mockOutbreaks.filter(o=>o.status==='active').length} accent="red" />
        <StatCard label="Contained" value={mockOutbreaks.filter(o=>o.status==='contained').length} accent="amber" />
        <StatCard label="Resolved" value={mockOutbreaks.filter(o=>o.status==='resolved').length} accent="green" />
      </div>
      <Card>
        <Table headers={['ID', 'Disease', 'District', 'Block', 'Villages', 'Animals', 'Deaths', 'Risk', 'Start', 'Status']}>
          {mockOutbreaks.map(o => (
            <TR key={o.id}>
              <TD mono>{o.id}</TD>
              <TD bold>{o.disease}</TD>
              <TD>{o.district}</TD>
              <TD>{o.block}</TD>
              <TD mono>{o.affectedVillages}</TD>
              <TD mono>{o.affectedAnimals}</TD>
              <TD><span className={`font-mono font-bold ${o.mortalityCount > 5 ? 'text-red-600' : 'text-gray-700'}`}>{o.mortalityCount}</span></TD>
              <TD><RiskBadge level={o.riskLevel} compact /></TD>
              <TD mono>{o.startDate}</TD>
              <TD><StatusBadge status={o.status} /></TD>
            </TR>
          ))}
        </Table>
      </Card>
    </div>
  );
}

function DiseaseTrends() {
  const [tab, setTab] = useState('line');
  return (
    <div className="space-y-5">
      <SectionHeader title="Disease Trends" subtitle="April — September 2026 · Gujarat State" />
      <Tabs tabs={[{id:'line',label:'Time Series'},{id:'bar',label:'Monthly Comparison'},{id:'table',label:'Data Table'}]}
        active={tab} onChange={setTab} />

      <Card className="p-5">
        {tab === 'line' && (
          <>
            <p className="text-sm font-semibold text-gray-600 mb-4">Monthly Case Reports by Disease</p>
            <div style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e9ede9" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="FMD" stroke="#dc2626" strokeWidth={2} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="LSD" stroke="#b45309" strokeWidth={2} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="BQ" stroke="#7c3aed" strokeWidth={2} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="PPR" stroke="#0891b2" strokeWidth={2} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="HS" stroke="#166534" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
        {tab === 'bar' && (
          <>
            <p className="text-sm font-semibold text-gray-600 mb-4">Monthly Case Totals by Disease</p>
            <div style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e9ede9" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="FMD" fill="#dc2626" radius={[2,2,0,0]} />
                  <Bar dataKey="LSD" fill="#b45309" radius={[2,2,0,0]} />
                  <Bar dataKey="BQ" fill="#7c3aed" radius={[2,2,0,0]} />
                  <Bar dataKey="PPR" fill="#0891b2" radius={[2,2,0,0]} />
                  <Bar dataKey="HS" fill="#166534" radius={[2,2,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
        {tab === 'table' && (
          <Table headers={['Month', 'FMD', 'LSD', 'BQ', 'PPR', 'HS', 'Total']}>
            {trendData.map(d => (
              <TR key={d.month}>
                <TD bold>{d.month} 2026</TD>
                <TD mono>{d.FMD}</TD>
                <TD mono>{d.LSD}</TD>
                <TD mono>{d.BQ}</TD>
                <TD mono>{d.PPR}</TD>
                <TD mono>{d.HS}</TD>
                <TD mono><strong>{d.FMD+d.LSD+d.BQ+d.PPR+d.HS}</strong></TD>
              </TR>
            ))}
          </Table>
        )}
      </Card>

      <div className="grid sm:grid-cols-2 gap-4">
        {[
          { disease: 'FMD', trend: '↑ 28%', status: 'Increasing', color: 'text-red-600' },
          { disease: 'LSD (Lumpy Skin)', trend: '↓ 12%', status: 'Decreasing', color: 'text-green-600' },
          { disease: 'Black Quarter', trend: '↑ 50%', status: 'Rapidly Increasing', color: 'text-red-700' },
          { disease: 'PPR', trend: '↓ 8%', status: 'Stable', color: 'text-amber-600' },
        ].map(d => (
          <Card key={d.disease} className="p-4">
            <p className="font-semibold text-gray-800">{d.disease}</p>
            <p className={`font-display font-700 text-xl mt-1 ${d.color}`}>{d.trend}</p>
            <p className="text-xs text-gray-500">{d.status} — 30 day comparison</p>
          </Card>
        ))}
      </div>
    </div>
  );
}

function VaccinationCoverage() {
  return (
    <div className="space-y-5">
      <SectionHeader title="Vaccination Coverage" subtitle="Gujarat State · September 2026" />
      <div className="grid sm:grid-cols-3 gap-4">
        <StatCard label="FMD Coverage" value="81%" sub="state average" accent="green" />
        <StatCard label="LSD Coverage" value="63%" sub="below target" accent="amber" />
        <StatCard label="BQ Coverage" value="75%" sub="on track" accent="green" />
      </div>
      <Card>
        <CardHeader title="District-wise Coverage" subtitle="FMD, LSD, BQ vaccines" />
        <div style={{ height: 320 }} className="p-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={vaccinationCoverageData} layout="vertical" barGap={2} barCategoryGap={12}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e9ede9" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={v => `${v}%`} />
              <YAxis type="category" dataKey="district" tick={{ fontSize: 11 }} width={90} />
              <Tooltip formatter={(v) => `${v}%`} />
              <Legend />
              <Bar dataKey="fmd" name="FMD" fill="#166534" radius={[0,2,2,0]} />
              <Bar dataKey="lsd" name="LSD" fill="#b45309" radius={[0,2,2,0]} />
              <Bar dataKey="bq" name="BQ" fill="#1d4ed8" radius={[0,2,2,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="px-4 pb-4">
          <div className="bg-red-50 border border-red-100 rounded p-3 text-xs text-red-700">
            ⚠ Banaskantha and Kutch districts have FMD coverage below 75% — priority vaccination drive recommended.
          </div>
        </div>
      </Card>
    </div>
  );
}

function GovReports() {
  return (
    <div className="space-y-5">
      <SectionHeader title="Surveillance Reports" subtitle="Generate and download official reports" />
      <div className="grid sm:grid-cols-2 gap-4">
        {[
          { title: 'Weekly Surveillance Report', desc: '08-14 Sep 2026 · Gujarat State', icon: '📊', badge: 'Ready' },
          { title: 'Outbreak Situation Report', desc: 'FMD, BQ Active Outbreaks — Sep 2026', icon: '🔴', badge: 'Draft' },
          { title: 'Monthly Disease Bulletin', desc: 'August 2026 — All Districts', icon: '📰', badge: 'Published' },
          { title: 'Vaccination Coverage Report', desc: 'H1 2026 — District-wise Analysis', icon: '💉', badge: 'Ready' },
          { title: 'Mortality & Morbidity Analysis', desc: 'Jan-Aug 2026 · Cause of death breakdown', icon: '📉', badge: 'Ready' },
          { title: 'Annual Disease Surveillance', desc: 'Full Year 2025 — Final Report', icon: '📋', badge: 'Published' },
        ].map(r => (
          <Card key={r.title} className="p-5">
            <div className="flex items-start gap-3">
              <span className="text-3xl">{r.icon}</span>
              <div className="flex-1">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-semibold text-gray-800 text-sm">{r.title}</h3>
                  <span className={`text-xs px-2 py-0.5 rounded font-medium
                    ${r.badge === 'Published' ? 'bg-green-50 text-green-700 border border-green-200' :
                      r.badge === 'Ready' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                      'bg-gray-100 text-gray-500 border border-gray-200'}`}>{r.badge}</span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{r.desc}</p>
                <div className="flex gap-2 mt-3">
                  <Btn variant="secondary" size="sm">Download PDF</Btn>
                  <Btn variant="ghost" size="sm">Share</Btn>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
