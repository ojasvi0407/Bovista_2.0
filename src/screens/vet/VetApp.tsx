import { useState } from 'react';
import { useApp } from '../../App';
import LiveWorkspaceStatus from '../../components/LiveWorkspaceStatus';
import RiskMapLeaflet from '../../components/RiskMapLeaflet';
import {
  Card, CardHeader, StatCard, Btn, RiskBadge, StatusBadge, Table, TR, TD,
  AlertBanner, EmptyState, SectionHeader, FormField, Input, Select, Textarea, Tabs, Timeline,
} from '../../components/ui';
import { mockReports, mockSamples, mockOutbreaks } from '../../mockData';

type Screen = 'dashboard' | 'cases' | 'case_detail' | 'triage' | 'riskmap' | 'reports' | 'laboratory' | 'outbreaks' | 'treatments';

const SIDEBAR = [
  { id: 'dashboard',   icon: '⊞', label: 'Dashboard' },
  { id: 'cases',       icon: '📋', label: 'Cases' },
  { id: 'triage',      icon: '⚡', label: 'Triage' },
  { id: 'riskmap',     icon: '🗺️', label: 'Risk Map' },
  { id: 'outbreaks',   icon: '🔴', label: 'Outbreaks' },
  { id: 'laboratory',  icon: '🧪', label: 'Laboratory' },
  { id: 'treatments',  icon: '💊', label: 'Treatments' },
  { id: 'reports',     icon: '📊', label: 'Reports' },
] as const;

export default function VetApp() {
  const { logout } = useApp();
  const [screen, setScreen] = useState<Screen>('dashboard');
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#f7f9f7] flex flex-col">
      {/* Header */}
      <header className="bg-[#166534] text-white px-6 py-3 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <button onClick={() => setSidebarOpen(o => !o)} className="lg:hidden text-white p-1">☰</button>
          <div className="text-xl">🐄</div>
          <div>
            <span className="font-display font-700 text-base">PashuSwasthya</span>
            <span className="text-green-300 text-xs ml-2">Veterinarian Portal</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="hidden sm:flex items-center gap-1.5 text-sm text-green-200">
            <span className="w-2 h-2 rounded-full bg-green-300" />Dr. Anjali Sharma · Ahmedabad
          </span>
          <span className="text-xs bg-red-700 text-white px-2 py-0.5 rounded-full font-mono">3 critical</span>
          <button onClick={logout} className="text-green-200 hover:text-white text-xs border border-green-600 px-3 py-1.5 rounded hover:bg-white/10">Log out</button>
        </div>
      </header>

      <div className="flex flex-1">
        {/* Sidebar */}
        <aside className={`bg-white border-r border-[#d1d9d1] w-56 flex-shrink-0 flex flex-col
          ${sidebarOpen ? 'fixed inset-y-0 left-0 z-50 pt-16' : 'hidden'} lg:flex lg:sticky lg:top-16 lg:h-[calc(100vh-56px)]`}>
          <nav className="flex-1 py-4 overflow-y-auto">
            {SIDEBAR.map(s => (
              <button key={s.id} onClick={() => { setScreen(s.id as Screen); setSidebarOpen(false); }}
                aria-current={screen === s.id ? 'page' : undefined}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium transition-colors
                  ${screen === s.id ? 'bg-green-50 text-[#166534] border-r-2 border-[#166534]' : 'text-gray-600 hover:bg-gray-50'}`}>
                <span>{s.icon}</span> {s.label}
              </button>
            ))}
          </nav>
          <div className="p-4 border-t border-[#d1d9d1] text-xs text-gray-400">
            <p>Ahmedabad District</p>
            <p>Last sync: Just now</p>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 overflow-y-auto min-w-0">
          <div className="max-w-5xl mx-auto px-6 py-6">
            {screen === 'dashboard' && <VetDashboard setScreen={setScreen} setSelectedReportId={setSelectedReportId} />}
            {screen === 'cases'     && <CasesList setScreen={setScreen} setSelectedReportId={setSelectedReportId} />}
            {screen === 'case_detail' && <CaseDetail reportId={selectedReportId} setScreen={setScreen} />}
            {screen === 'triage'    && <TriageQueue setScreen={setScreen} setSelectedReportId={setSelectedReportId} />}
            {screen === 'riskmap'   && (
              <div className="space-y-4" style={{ height: 'calc(100vh - 200px)', minHeight: 620 }}>
                <div className="flex items-end justify-between">
                  <div>
                    <h2 className="font-display font-700 text-gray-900 text-xl">Risk Map</h2>
                    <p className="text-sm text-gray-500 mt-0.5">Ahmedabad District — Disease Surveillance</p>
                  </div>
                </div>
                <div style={{ height: 'calc(100% - 64px)' }}>
                  <RiskMapLeaflet userDistrict="Ahmedabad" userBlock="Daskroi" />
                </div>
              </div>
            )}
            {screen === 'outbreaks' && <OutbreaksList />}
            {screen === 'laboratory'&& <LaboratoryView />}
            {screen === 'treatments'&& <TreatmentsList />}
            {screen === 'reports'   && <ReportsView />}
          </div>
        </main>
      </div>
    </div>
  );
}

function VetDashboard({ setScreen, setSelectedReportId }: any) {
  const { workspace } = useApp();
  const cases = workspace.cases ?? [];
  const reports = workspace.reports ?? [];
  const outbreaks = workspace.outbreaks ?? [];
  return (
    <div className="space-y-6">
      <LiveWorkspaceStatus />
      <SectionHeader title="Dashboard" subtitle="Ahmedabad District · 12 September 2026" />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Open Cases" value={cases.length} sub="in your assigned scope" accent="red" />
        <StatCard label="Visible Reports" value={reports.length} sub="live queue" accent="amber" />
        <StatCard label="Notifications" value={(workspace.alerts ?? []).length} sub="action notifications" accent="blue" />
        <StatCard label="Active Outbreaks" value={outbreaks.length} sub="district-level" accent="red" />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Critical Priority Queue" action={<Btn variant="ghost" size="sm" onClick={() => setScreen('triage')}>Triage →</Btn>} />
          <div className="divide-y divide-[#e9ede9]">
            {mockReports.filter(r => r.riskLevel === 'critical' || r.riskLevel === 'high').slice(0, 4).map(r => (
              <div key={r.id} className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-green-50"
                onClick={() => { setSelectedReportId(r.id); setScreen('case_detail'); }}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <RiskBadge level={r.riskLevel} compact />
                    <span className="font-mono text-xs text-gray-400">{r.id}</span>
                  </div>
                  <p className="text-sm font-medium text-gray-800 mt-0.5 truncate">{r.farmerName} · {r.village}</p>
                  <p className="text-xs text-gray-500">{r.species} · {r.affectedCount} affected{r.mortalityCount > 0 ? ` · ⚠ ${r.mortalityCount} deaths` : ''}</p>
                </div>
                <StatusBadge status={r.status} />
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <CardHeader title="Active Outbreaks" action={<Btn variant="ghost" size="sm" onClick={() => setScreen('outbreaks')}>All →</Btn>} />
          <div className="divide-y divide-[#e9ede9]">
            {mockOutbreaks.filter(o => o.status === 'active').slice(0, 4).map(o => (
              <div key={o.id} className="px-4 py-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-gray-800">{o.disease}</p>
                    <p className="text-xs text-gray-500">{o.district} · {o.affectedVillages} villages · {o.affectedAnimals} animals</p>
                  </div>
                  <RiskBadge level={o.riskLevel} compact />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title="Recent Sample Results" action={<Btn variant="ghost" size="sm" onClick={() => setScreen('laboratory')}>Lab →</Btn>} />
        <Table headers={['Sample ID', 'Disease', 'Type', 'Lab', 'Status', 'Result']}>
          {mockSamples.map(s => (
            <TR key={s.id}>
              <TD mono>{s.id}</TD>
              <TD>{s.disease}</TD>
              <TD>{s.sampleType}</TD>
              <TD>{s.labName}</TD>
              <TD><StatusBadge status={s.status} /></TD>
              <TD>{s.result ? <span className="text-xs text-red-700 font-medium">Positive</span> : <span className="text-xs text-gray-400">Pending</span>}</TD>
            </TR>
          ))}
        </Table>
      </Card>
    </div>
  );
}

function CasesList({ setScreen, setSelectedReportId }: any) {
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const filtered = mockReports.filter(r =>
    (riskFilter === 'all' || r.riskLevel === riskFilter) &&
    (r.farmerName.toLowerCase().includes(search.toLowerCase()) ||
     r.id.toLowerCase().includes(search.toLowerCase()) ||
     r.village.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-5">
      <SectionHeader title="Cases" subtitle={`${mockReports.length} total reports`} />
      <div className="flex flex-col sm:flex-row gap-3">
        <Input value={search} onChange={setSearch} placeholder="Search by farmer, report ID, location..." />
        <Select value={riskFilter} onChange={setRiskFilter}>
          <option value="all">All risk levels</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </Select>
      </div>
      <Card>
        <Table headers={['Report ID', 'Farmer', 'Location', 'Species', 'Affected', 'Risk', 'Status', 'Date']}>
          {filtered.map(r => (
            <TR key={r.id} onClick={() => { setSelectedReportId(r.id); setScreen('case_detail'); }}>
              <TD mono>{r.id}</TD>
              <TD bold>{r.farmerName}</TD>
              <TD>{r.village}, {r.district}</TD>
              <TD>{r.species}</TD>
              <TD><span className="font-mono text-sm">{r.affectedCount}{r.mortalityCount > 0 ? <span className="text-red-600"> / {r.mortalityCount}†</span> : ''}</span></TD>
              <TD><RiskBadge level={r.riskLevel} compact /></TD>
              <TD><StatusBadge status={r.status} /></TD>
              <TD mono>{new Date(r.createdAt).toLocaleDateString()}</TD>
            </TR>
          ))}
        </Table>
        {filtered.length === 0 && <EmptyState icon="📋" title="No cases match your filter" />}
      </Card>
    </div>
  );
}

function CaseDetail({ reportId, setScreen }: any) {
  const report = mockReports.find(r => r.id === reportId) || mockReports[0];
  const [tab, setTab] = useState('overview');
  const [status, setStatus] = useState(report.status);

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => setScreen('cases')} className="text-sm text-[#166534] font-medium hover:underline">← Cases</button>
        <span className="font-mono text-sm text-gray-400">{report.id}</span>
      </div>

      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="font-display font-700 text-2xl text-gray-900">{report.farmerName}</h2>
          <p className="text-gray-500">{report.village}, {report.block}, {report.district} · 📞 {report.farmerPhone}</p>
          <div className="flex gap-2 mt-2 flex-wrap">
            <StatusBadge status={status} />
            {report.disease && <span className="text-sm bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded">{report.disease}</span>}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <RiskBadge level={report.riskLevel} score={report.riskScore} />
          <Select value={status} onChange={setStatus as any}>
            <option value="under_review">Under Review</option>
            <option value="assigned">Assigned</option>
            <option value="sample_collected">Sample Collected</option>
            <option value="lab_testing">Lab Testing</option>
            <option value="confirmed">Confirmed</option>
            <option value="resolved">Resolved</option>
          </Select>
        </div>
      </div>

      <Tabs tabs={[{id:'overview',label:'Overview'},{id:'symptoms',label:'Symptoms'},{id:'triage',label:'AI Triage'},{id:'history',label:'Timeline'}]}
        active={tab} onChange={setTab} />

      {tab === 'overview' && (
        <div className="grid sm:grid-cols-2 gap-5">
          <Card>
            <CardHeader title="Case Details" />
            <div className="divide-y divide-[#e9ede9]">
              {[['Species', report.species], ['Affected', `${report.affectedCount} animals`], ['Deaths', `${report.mortalityCount}`], ['Total herd', `${report.totalAnimals}`], ['District', report.district], ['Block', report.block], ['Village', report.village]].map(([k,v]) => (
                <div key={k} className="px-4 py-2.5 flex justify-between text-sm">
                  <span className="text-gray-500">{k}</span>
                  <span className="font-medium text-gray-800">{v}</span>
                </div>
              ))}
            </div>
          </Card>
          <div className="space-y-4">
            <Card className="p-4">
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Assigned Staff</p>
              <p className="text-sm text-gray-700">Para-vet: <strong>{report.assignedParavet || 'Unassigned'}</strong></p>
              <p className="text-sm text-gray-700 mt-1">Vet: <strong>{report.assignedVet || 'You'}</strong></p>
            </Card>
            <div className="flex flex-col gap-2">
              <Btn variant="primary" fullWidth>Assign Para-vet for Visit</Btn>
              <Btn variant="secondary" fullWidth>Request Lab Sample</Btn>
              <Btn variant="secondary" fullWidth>Add Clinical Notes</Btn>
            </div>
          </div>
        </div>
      )}

      {tab === 'symptoms' && (
        <Card>
          <CardHeader title={`Reported Symptoms (${report.symptoms.length})`} />
          <div className="p-4 grid sm:grid-cols-2 gap-2">
            {report.symptoms.map(s => (
              <div key={s} className="flex items-center gap-2 p-3 bg-red-50 rounded border border-red-100">
                <span className="text-red-500 text-sm">●</span>
                <span className="text-sm text-gray-700">{s}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {tab === 'triage' && (
        <div className="space-y-4">
          <AlertBanner type="warning" title="AI Decision Support — Not a Clinical Diagnosis"
            message="Risk scores are generated by pattern-matching algorithms. All decisions require clinical judgement from a qualified veterinarian." />
          {report.aiSuggestion && (
            <Card className="p-5 border-l-4 border-l-amber-400">
              <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-2">AI Assessment</p>
              <p className="text-base text-gray-800">{report.aiSuggestion}</p>
            </Card>
          )}
          <Card>
            <CardHeader title="Risk Score Breakdown" subtitle="Explainable AI — factor weights" />
            <div className="p-5 space-y-4">
              {[
                { factor: 'Symptom pattern (FMD match)', weight: 35, score: 88, desc: 'Blisters, salivation, lameness — high correlation' },
                { factor: 'Mortality indicator', weight: 20, score: 60, desc: '1 death in 24 animals — moderate' },
                { factor: 'Geographic cluster proximity', weight: 20, score: 78, desc: '5 reports within 10 km in 7 days' },
                { factor: 'Species & age vulnerability', weight: 15, score: 70, desc: 'Unvaccinated cattle, age 2-4 yrs' },
                { factor: 'Environmental risk', weight: 10, score: 65, desc: 'Open water source, recent animal movement' },
              ].map(({ factor, weight, score, desc }) => (
                <div key={factor}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="font-medium text-gray-700">{factor}</span>
                    <span className="font-mono text-gray-500">{score}/100 · wt {weight}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2.5">
                    <div className={`h-2.5 rounded-full transition-all ${score >= 70 ? 'bg-red-500' : score >= 50 ? 'bg-amber-500' : 'bg-green-500'}`}
                      style={{ width: `${score}%` }} />
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
                </div>
              ))}
              <div className="border-t border-[#d1d9d1] pt-3 flex items-center justify-between">
                <span className="font-semibold text-gray-700">Composite Risk Score</span>
                <span className="font-display font-700 text-xl text-red-600">{report.riskScore} / 100</span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {tab === 'history' && (
        <Card>
          <CardHeader title="Case Timeline" />
          <div className="px-5 py-5">
            <Timeline items={[
              { date: '10 Sep 08:30', title: 'Report submitted by farmer', desc: 'Via mobile app', done: true },
              { date: '10 Sep 09:15', title: 'AI triage applied', desc: `Score: ${report.riskScore}/100 — ${report.riskLevel} risk`, done: true },
              { date: '10 Sep 11:00', title: 'Para-vet assigned', desc: 'Mohan Desai dispatched for field visit', done: true },
              { date: '11 Sep 10:30', title: 'Sample collected', desc: 'Epithelial tissue + serum → GBRC Gandhinagar', done: report.status !== 'under_review' },
              { date: 'Pending', title: 'Lab results expected', desc: 'RT-PCR / ELISA in progress', done: false },
              { date: 'Pending', title: 'Clinical confirmation', desc: 'Awaiting lab report', done: false },
            ]} />
          </div>
        </Card>
      )}
    </div>
  );
}

function TriageQueue({ setScreen, setSelectedReportId }: any) {
  return (
    <div className="space-y-5">
      <SectionHeader title="Explainable Triage Queue" subtitle="AI-scored reports awaiting veterinary review" />
      <AlertBanner type="info" title="AI Decision Support System"
        message="All cases below have been scored by pattern-matching AI. Scores indicate priority for review — not diagnosis. Your clinical judgement overrides any AI assessment." />
      <Card>
        <Table headers={['Priority', 'Report', 'Farmer', 'Location', 'Species', 'Symptoms', 'AI Score', 'Action']}>
          {[...mockReports].sort((a, b) => b.riskScore - a.riskScore).map(r => (
            <TR key={r.id} onClick={() => { setSelectedReportId(r.id); setScreen('case_detail'); }}>
              <TD><RiskBadge level={r.riskLevel} compact /></TD>
              <TD mono>{r.id}</TD>
              <TD bold>{r.farmerName}</TD>
              <TD>{r.village}</TD>
              <TD>{r.species}</TD>
              <TD><span className="text-xs text-gray-500">{r.symptoms.slice(0,2).join(', ')}{r.symptoms.length > 2 ? ` +${r.symptoms.length-2}` : ''}</span></TD>
              <TD>
                <div className="flex items-center gap-2">
                  <div className="w-16 bg-gray-100 rounded-full h-2">
                    <div className={`h-2 rounded-full ${r.riskScore >= 70 ? 'bg-red-500' : r.riskScore >= 40 ? 'bg-amber-500' : 'bg-green-500'}`}
                      style={{ width: `${r.riskScore}%` }} />
                  </div>
                  <span className="font-mono text-sm font-semibold">{r.riskScore}</span>
                </div>
              </TD>
              <TD><Btn variant="ghost" size="sm">Review</Btn></TD>
            </TR>
          ))}
        </Table>
      </Card>
    </div>
  );
}

function OutbreaksList() {
  return (
    <div className="space-y-5">
      <SectionHeader title="Active Outbreaks" subtitle="District and state-level clusters" />
      <div className="grid sm:grid-cols-3 gap-4">
        <StatCard label="Active Outbreaks" value={mockOutbreaks.filter(o => o.status === 'active').length} accent="red" />
        <StatCard label="Animals Affected" value={mockOutbreaks.reduce((s,o) => s+o.affectedAnimals,0)} accent="amber" />
        <StatCard label="Total Mortality" value={mockOutbreaks.reduce((s,o) => s+o.mortalityCount,0)} accent="red" />
      </div>
      <div className="grid gap-4">
        {mockOutbreaks.map(o => (
          <Card key={o.id} className={`p-5 border-l-4 ${o.riskLevel === 'critical' ? 'border-l-red-600' : o.riskLevel === 'high' ? 'border-l-red-400' : 'border-l-amber-400'}`}>
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-display font-600 text-gray-900">{o.disease}</h3>
                  <RiskBadge level={o.riskLevel} compact />
                  <StatusBadge status={o.status} />
                </div>
                <p className="text-sm text-gray-500 mt-1">{o.district} · {o.block}</p>
                <p className="text-xs text-gray-400">Started: {o.startDate}</p>
              </div>
              <div className="grid grid-cols-3 gap-4 text-center">
                {[['Villages', o.affectedVillages], ['Animals', o.affectedAnimals], ['Deaths', o.mortalityCount]].map(([k,v]) => (
                  <div key={k}>
                    <p className="font-display font-700 text-lg text-gray-900">{v}</p>
                    <p className="text-xs text-gray-500">{k}</p>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function LaboratoryView() {
  return (
    <div className="space-y-5">
      <SectionHeader title="Laboratory Samples" subtitle="Tracking samples submitted from your cases" />
      <div className="grid sm:grid-cols-3 gap-4">
        <StatCard label="Total Samples" value={mockSamples.length} />
        <StatCard label="Results Pending" value={mockSamples.filter(s => s.status !== 'completed').length} accent="amber" />
        <StatCard label="Positive Results" value={mockSamples.filter(s => s.result?.includes('Positive')).length} accent="red" />
      </div>
      <Card>
        <Table headers={['Sample ID', 'Report', 'Type', 'Disease', 'Priority', 'Lab', 'Status', 'Result']}>
          {mockSamples.map(s => (
            <TR key={s.id}>
              <TD mono>{s.id}</TD>
              <TD mono>{s.reportId}</TD>
              <TD>{s.sampleType}</TD>
              <TD>{s.disease}</TD>
              <TD>
                <span className={`text-xs px-2 py-0.5 rounded font-medium border
                  ${s.priority === 'critical' ? 'text-red-700 bg-red-50 border-red-200' :
                    s.priority === 'urgent' ? 'text-amber-700 bg-amber-50 border-amber-200' :
                    'text-gray-600 bg-gray-50 border-gray-200'}`}>
                  {s.priority}
                </span>
              </TD>
              <TD>{s.labName}</TD>
              <TD><StatusBadge status={s.status} /></TD>
              <TD>{s.result ? <span className="text-xs text-red-700 font-semibold">Positive</span> : <span className="text-xs text-gray-400">—</span>}</TD>
            </TR>
          ))}
        </Table>
      </Card>
    </div>
  );
}

function TreatmentsList() {
  return (
    <div className="space-y-5">
      <SectionHeader title="Treatment Management" />
      <Card className="p-5 border-l-4 border-l-amber-400">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <span className="text-xs text-amber-700 font-semibold uppercase">Active Treatment Protocol</span>
            <h3 className="font-display font-600 text-lg text-gray-900 mt-1">FMD Supportive Care Protocol</h3>
            <p className="text-sm text-gray-500">Ramesh Patel · GJ-AHD-00143 · Started 10 Sep 2026</p>
          </div>
          <StatusBadge status="under_review" />
        </div>
        <div className="mt-3 grid sm:grid-cols-3 gap-3 text-sm">
          {[['Drug', 'Foot-bath: KMnO4 0.1%'], ['Supportive', 'Vit B complex IM'], ['Duration', '10 days (Day 4)']].map(([k,v]) => (
            <div key={k}><p className="text-xs text-gray-400">{k}</p><p className="font-medium">{v}</p></div>
          ))}
        </div>
      </Card>
      <EmptyState icon="💊" title="No other active treatments" />
    </div>
  );
}

function ReportsView() {
  return (
    <div className="space-y-5">
      <SectionHeader title="Reports" subtitle="Generate and download reports" />
      <div className="grid sm:grid-cols-2 gap-4">
        {[
          { title: 'Weekly Disease Summary', desc: 'District-level summary for week of 08-14 Sep 2026', icon: '📊' },
          { title: 'Outbreak Incident Report', desc: 'FMD Cluster — Daskroi Block', icon: '🔴' },
          { title: 'Vaccination Coverage Report', desc: 'September 2026 — Ahmedabad District', icon: '💉' },
          { title: 'Sample Tracking Report', desc: 'All samples sent to labs, Sep 2026', icon: '🧪' },
        ].map(r => (
          <Card key={r.title} className="p-5">
            <div className="flex items-start gap-3">
              <span className="text-3xl">{r.icon}</span>
              <div>
                <h3 className="font-semibold text-gray-800">{r.title}</h3>
                <p className="text-xs text-gray-500 mt-0.5">{r.desc}</p>
                <Btn variant="secondary" size="sm" className="mt-3">Download PDF</Btn>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
