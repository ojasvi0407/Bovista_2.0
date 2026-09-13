import { useState } from 'react';
import { useApp } from '../../App';
import LiveWorkspaceStatus from '../../components/LiveWorkspaceStatus';
import {
  Card, CardHeader, StatCard, Btn, RiskBadge, StatusBadge, Table, TR, TD,
  AlertBanner, EmptyState, OfflineBanner, SectionHeader, FormField, Input, Select, Textarea, Tabs,
} from '../../components/ui';
import { mockReports, mockSamples } from '../../mockData';

type Screen = 'dashboard' | 'field_reports' | 'case_detail' | 'sample_collection' | 'vaccination' | 'offline_queue';

const NAV = [
  { id: 'dashboard',         label: 'Home',      icon: '⊞' },
  { id: 'field_reports',     label: 'Reports',   icon: '📋' },
  { id: 'sample_collection', label: 'Samples',   icon: '🧪' },
  { id: 'vaccination',       label: 'Vaccines',  icon: '💉' },
  { id: 'offline_queue',     label: 'Queue',     icon: '⏳' },
] as const;

export default function ParavetApp() {
  const { t, logout } = useApp();
  const [screen, setScreen] = useState<Screen>('dashboard');
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [isOffline] = useState(false);

  return (
    <div className="min-h-screen bg-[#f7f9f7] flex flex-col max-w-lg mx-auto">
      <header className="bg-[#166534] text-white px-4 py-3 sticky top-0 z-40">
        <div className="flex items-center justify-between">
          <div>
            <span className="font-display font-700 text-base">PashuSwasthya</span>
            <div className="text-green-200 text-xs">Mohan Desai · Para-vet · Daskroi</div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs bg-green-700 text-green-100 px-2 py-0.5 rounded-full">● Online</span>
            <span className="text-xs bg-amber-600 text-white px-2 py-0.5 rounded-full font-mono">2 pending</span>
            <button onClick={logout} className="text-green-200 hover:text-white text-xs px-2 py-1 rounded hover:bg-white/10">↩</button>
          </div>
        </div>
      </header>

      {isOffline && <OfflineBanner pendingCount={2} />}

      <main className="flex-1 overflow-y-auto pb-20">
        {screen === 'dashboard'         && <ParavetDashboard setScreen={setScreen} setSelectedReportId={setSelectedReportId} />}
        {screen === 'field_reports'     && <FieldReports setScreen={setScreen} setSelectedReportId={setSelectedReportId} />}
        {screen === 'case_detail'       && <CaseDetail reportId={selectedReportId} setScreen={setScreen} />}
        {screen === 'sample_collection' && <SampleCollectionForm setScreen={setScreen} />}
        {screen === 'vaccination'       && <VaccinationDrive />}
        {screen === 'offline_queue'     && <OfflineQueue />}
      </main>

      <nav className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-lg bg-white border-t border-[#d1d9d1] flex z-40">
        {NAV.map(n => (
          <button key={n.id} onClick={() => setScreen(n.id as Screen)}
            aria-current={screen === n.id ? 'page' : undefined}
            className={`flex-1 flex flex-col items-center py-2.5 gap-0.5 text-xs transition-colors
              ${screen === n.id ? 'text-[#166534] font-semibold' : 'text-gray-500'}`}>
            <span className="text-lg leading-none">{n.icon}</span>
            <span>{n.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}

function ParavetDashboard({ setScreen, setSelectedReportId }: any) {
  const { workspace } = useApp();
  return (
    <div className="px-4 py-4 space-y-5">
      <LiveWorkspaceStatus />
      <AlertBanner type="error" title="Critical: BQ case — Viramgam" message="RPT-2026-08805 requires immediate field visit. Buffalo mortality reported." />

      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Assigned Cases" value={(workspace.cases ?? []).length} sub="in your assigned scope" accent="amber" />
        <StatCard label="Visible Reports" value={(workspace.reports ?? []).length} sub="field queue" accent="green" />
        <StatCard label="Alerts" value={(workspace.alerts ?? []).length} sub="requires attention" accent="blue" />
        <StatCard label="Outbreaks" value={(workspace.outbreaks ?? []).length} sub="visible to your scope" accent="gray" />
      </div>

      <Card>
        <CardHeader title="Priority Cases" subtitle="Requires field visit today" />
        <div className="divide-y divide-[#e9ede9]">
          {mockReports.filter(r => ['high','critical'].includes(r.riskLevel) && r.status !== 'resolved').map(r => (
            <div key={r.id} className="px-4 py-3 cursor-pointer hover:bg-green-50"
              onClick={() => { setSelectedReportId(r.id); setScreen('case_detail'); }}>
              <div className="flex items-center justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-mono text-xs text-gray-400">{r.id}</p>
                  <p className="text-sm font-semibold text-gray-800 truncate">{r.farmerName} · {r.village}</p>
                  <p className="text-xs text-gray-500">{r.species} · {r.affectedCount} affected</p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <RiskBadge level={r.riskLevel} compact />
                  <StatusBadge status={r.status} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-2 gap-3">
        <Btn variant="primary" fullWidth size="lg" onClick={() => setScreen('sample_collection')}>
          🧪 Collect Sample
        </Btn>
        <Btn variant="secondary" fullWidth size="lg" onClick={() => setScreen('field_reports')}>
          📋 All Reports
        </Btn>
      </div>
    </div>
  );
}

function FieldReports({ setScreen, setSelectedReportId }: any) {
  const [filter, setFilter] = useState('all');
  const filtered = mockReports.filter(r =>
    filter === 'all' || r.riskLevel === filter || r.status === filter
  );

  return (
    <div className="px-4 py-4 space-y-4">
      <SectionHeader title="Field Reports" subtitle="Assigned to your zone" />
      <div className="flex gap-2 overflow-x-auto pb-1">
        {['all','critical','high','medium','assigned','sample_collected'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap border transition-colors
              ${filter === f ? 'bg-[#166534] text-white border-[#166534]' : 'bg-white text-gray-600 border-[#d1d9d1] hover:border-green-400'}`}>
            {f.replace('_', ' ')}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon="📋" title="No reports found" description="Try a different filter." />
      ) : (
        <div className="space-y-2">
          {filtered.map(r => (
            <Card key={r.id} className="p-4 cursor-pointer hover:border-green-400 transition-colors"
              onClick={() => { setSelectedReportId(r.id); setScreen('case_detail'); }}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-mono text-xs text-gray-400">{r.id}</p>
                  <p className="text-sm font-semibold text-gray-800">{r.farmerName}</p>
                  <p className="text-xs text-gray-500">{r.village}, {r.district} · {r.species}</p>
                  <p className="text-xs text-gray-500">Affected: {r.affectedCount} · Deaths: {r.mortalityCount}</p>
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    <StatusBadge status={r.status} />
                  </div>
                </div>
                <RiskBadge level={r.riskLevel} compact />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function CaseDetail({ reportId, setScreen }: any) {
  const report = mockReports.find(r => r.id === reportId) || mockReports[0];
  const [tab, setTab] = useState('details');

  return (
    <div className="space-y-0">
      <div className="px-4 pt-4 pb-2">
        <button onClick={() => setScreen('field_reports')} className="text-sm text-[#166534] font-medium">← Reports</button>
      </div>

      <div className="px-4 pb-3">
        <div className="flex items-start justify-between flex-wrap gap-2">
          <div>
            <p className="font-mono text-xs text-gray-500">{report.id}</p>
            <h2 className="font-display font-700 text-lg text-gray-900">{report.farmerName}</h2>
            <p className="text-sm text-gray-500">{report.village}, {report.block}, {report.district}</p>
            <p className="text-xs text-gray-500 mt-0.5">📞 {report.farmerPhone}</p>
          </div>
          <RiskBadge level={report.riskLevel} score={report.riskScore} />
        </div>
        <div className="flex gap-2 mt-2 flex-wrap">
          <StatusBadge status={report.status} />
          {report.disease && <span className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded">{report.disease}</span>}
        </div>
      </div>

      <Tabs tabs={[{id:'details',label:'Case Details'},{id:'symptoms',label:'Symptoms'},{id:'ai',label:'AI Triage'}]}
        active={tab} onChange={setTab} />

      <div className="px-4 py-4 pb-24">
        {tab === 'details' && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 text-sm">
              {[['Species', report.species], ['Affected', `${report.affectedCount} animals`], ['Deaths', String(report.mortalityCount)], ['Total herd', `${report.totalAnimals}`]].map(([k,v]) => (
                <Card key={k} className="p-3">
                  <p className="text-xs text-gray-400">{k}</p>
                  <p className="font-semibold text-gray-800">{v}</p>
                </Card>
              ))}
            </div>
            <div className="flex gap-2 pt-2">
              <Btn variant="primary" fullWidth onClick={() => setScreen('sample_collection')}>Collect Sample</Btn>
              <Btn variant="secondary" fullWidth>Update Status</Btn>
            </div>
          </div>
        )}
        {tab === 'symptoms' && (
          <div className="space-y-2">
            {report.symptoms.map(s => (
              <div key={s} className="flex items-center gap-2 p-3 bg-green-50 rounded-lg border border-green-100">
                <span className="text-green-600">●</span>
                <span className="text-sm text-gray-700">{s}</span>
              </div>
            ))}
          </div>
        )}
        {tab === 'ai' && (
          <div className="space-y-3">
            <AlertBanner type="warning" title="AI Decision Support — Not a Diagnosis"
              message="For veterinary guidance only. All assessments require professional verification." />
            {report.aiSuggestion && (
              <Card className="p-4 border-l-4 border-l-amber-400">
                <p className="text-xs font-semibold text-amber-700 uppercase mb-1">AI Assessment</p>
                <p className="text-sm text-gray-700">{report.aiSuggestion}</p>
              </Card>
            )}
            <Card className="p-4">
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Risk Score Breakdown</p>
              {[['Symptom pattern match', 82], ['Mortality indicator', 70], ['Geographic cluster', 60], ['Species vulnerability', 75]].map(([k,v]) => (
                <div key={k} className="flex items-center gap-3 mb-2">
                  <span className="text-xs text-gray-500 w-40">{k}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div className={`h-2 rounded-full ${Number(v) >= 70 ? 'bg-red-500' : Number(v) >= 50 ? 'bg-amber-500' : 'bg-green-500'}`} style={{ width: `${v}%` }} />
                  </div>
                  <span className="font-mono text-xs text-gray-600 w-8 text-right">{v}</span>
                </div>
              ))}
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

function SampleCollectionForm({ setScreen }: any) {
  const [form, setForm] = useState({ reportId: 'RPT-2026-08741', animalTag: '', sampleType: '', lab: '', priority: 'routine', notes: '' });
  const [submitted, setSubmitted] = useState(false);

  if (submitted) {
    return (
      <div className="px-4 py-10 flex flex-col items-center text-center gap-4">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center text-3xl">✓</div>
        <h3 className="font-display font-700 text-lg text-gray-900">Sample Recorded</h3>
        <p className="text-sm text-gray-500">Sample <strong className="font-mono">SMP-2026-04212</strong> registered. Please label the sample tube and dispatch to the selected laboratory.</p>
        <Btn variant="primary" onClick={() => setScreen('dashboard')}>Done</Btn>
      </div>
    );
  }

  return (
    <div className="px-4 py-4 space-y-4 pb-8">
      <div className="flex items-center gap-2">
        <button onClick={() => setScreen('dashboard')} className="text-sm text-[#166534] font-medium">← Back</button>
      </div>
      <SectionHeader title="Sample Collection" />
      <Card className="p-4 space-y-4">
        <FormField label="Report ID" required>
          <Select value={form.reportId} onChange={v => setForm(f => ({ ...f, reportId: v }))}>
            {mockReports.map(r => <option key={r.id} value={r.id}>{r.id} — {r.farmerName}</option>)}
          </Select>
        </FormField>
        <FormField label="Animal Tag No." required>
          <Input value={form.animalTag} onChange={v => setForm(f => ({ ...f, animalTag: v }))} placeholder="e.g. GJ-AHD-00142" />
        </FormField>
        <FormField label="Sample Type" required>
          <Select value={form.sampleType} onChange={v => setForm(f => ({ ...f, sampleType: v }))}>
            <option value="">Select type</option>
            <option>Blood (serum)</option>
            <option>Nasal swab</option>
            <option>Epithelial tissue</option>
            <option>Faecal sample</option>
            <option>Milk sample</option>
            <option>Post-mortem tissue</option>
          </Select>
        </FormField>
        <FormField label="Target Laboratory" required>
          <Select value={form.lab} onChange={v => setForm(f => ({ ...f, lab: v }))}>
            <option value="">Select lab</option>
            <option>GBRC Gandhinagar</option>
            <option>NDDB Laboratory, Anand</option>
            <option>SAU Veterinary Lab, Anand</option>
            <option>District Veterinary Lab, Ahmedabad</option>
          </Select>
        </FormField>
        <FormField label="Priority">
          <Select value={form.priority} onChange={v => setForm(f => ({ ...f, priority: v }))}>
            <option value="routine">Routine</option>
            <option value="urgent">Urgent</option>
            <option value="critical">Critical</option>
          </Select>
        </FormField>
        <FormField label="Collection Notes">
          <Textarea value={form.notes} onChange={v => setForm(f => ({ ...f, notes: v }))} placeholder="Sample condition, collection method, storage..." />
        </FormField>
        <Btn variant="primary" fullWidth size="lg" onClick={() => setSubmitted(true)}>
          Register Sample & Generate ID
        </Btn>
      </Card>
    </div>
  );
}

function VaccinationDrive() {
  return (
    <div className="px-4 py-4 space-y-4">
      <SectionHeader title="Vaccination Drive" subtitle="Block: Daskroi · Sep 2026" />
      <div className="grid grid-cols-3 gap-2">
        <StatCard label="Target" value="340" sub="animals" />
        <StatCard label="Done" value="218" sub="64%" accent="green" />
        <StatCard label="Remaining" value="122" sub="this week" accent="amber" />
      </div>
      <Card>
        <CardHeader title="Today's Schedule" />
        <div className="divide-y divide-[#e9ede9]">
          {[
            { village: 'Bhadaj', animals: 22, vaccine: 'FMD', status: 'completed' },
            { village: 'Ranip', animals: 18, vaccine: 'FMD', status: 'in_transit' },
            { village: 'Naroda', animals: 34, vaccine: 'LSD', status: 'scheduled' },
          ].map(v => (
            <div key={v.village} className="px-4 py-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-800">{v.village}</p>
                <p className="text-xs text-gray-500">{v.animals} animals · {v.vaccine}</p>
              </div>
              <StatusBadge status={v.status} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function OfflineQueue() {
  return (
    <div className="px-4 py-4 space-y-4">
      <SectionHeader title="Offline Queue" subtitle="Items pending synchronisation" />
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-700">
        <p className="font-semibold">⚡ 1 item stored offline</p>
        <p className="text-xs mt-0.5">Will sync automatically when internet connection is restored.</p>
      </div>
      <Card className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="font-mono text-xs text-gray-500">DRAFT-0041</p>
            <p className="text-sm font-semibold text-gray-800">Sample Collection Form</p>
            <p className="text-xs text-gray-500">RPT-2026-08790 · Kantilal Mer · Mandvi</p>
            <p className="text-xs text-gray-400 mt-1">Saved: 12 Sep 2026, 09:15</p>
          </div>
          <span className="text-xs bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded">Queued</span>
        </div>
        <Btn variant="secondary" size="sm" className="mt-3">Try Sync Now</Btn>
      </Card>
      <EmptyState icon="✓" title="No other pending items" description="All other data is synced." />
    </div>
  );
}
