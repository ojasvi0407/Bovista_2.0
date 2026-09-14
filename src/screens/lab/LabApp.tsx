import { useState } from 'react';
import { useApp } from '../../App';
import LiveWorkspaceStatus from '../../components/LiveWorkspaceStatus';
import {
  Card, CardHeader, StatCard, Btn, StatusBadge, Table, TR, TD,
  AlertBanner, EmptyState, SectionHeader, FormField, Input, Select, Textarea, Tabs,
} from '../../components/ui';
import { mockSamples } from '../../mockData';
import type { Sample, SampleStatus } from '../../types';

type Screen = 'dashboard' | 'samples' | 'sample_detail' | 'result_entry';

const SIDEBAR = [
  { id: 'dashboard',    icon: '⊞', label: 'Dashboard' },
  { id: 'samples',      icon: '🧪', label: 'Samples' },
  { id: 'result_entry', icon: '✍', label: 'Enter Results' },
] as const;

export default function LabApp() {
  const { logout } = useApp();
  const [screen, setScreen] = useState<Screen>('dashboard');
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-[#f7f9f7] flex flex-col">
      <header className="bg-[#166534] text-white px-6 py-3 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="text-xl">🧪</div>
          <div>
            <span className="font-display font-700 text-base">PashuMitra</span>
            <span className="text-green-300 text-xs ml-2">Laboratory Portal</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-green-200 hidden sm:block">Priya Mehta · GBRC Gandhinagar</span>
          <span className="text-xs bg-amber-600 text-white px-2 py-0.5 rounded-full font-mono">2 pending</span>
          <button onClick={logout} className="text-green-200 text-xs border border-green-600 px-3 py-1.5 rounded hover:bg-white/10">Log out</button>
        </div>
      </header>

      <div className="flex flex-1">
        <aside className="bg-white border-r border-[#d1d9d1] w-48 flex-shrink-0 hidden lg:flex flex-col sticky top-16 h-[calc(100vh-56px)]">
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
        </aside>

        <main className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-6 py-6">
            {screen === 'dashboard'    && <LabDashboard setScreen={setScreen} setSelectedSampleId={setSelectedSampleId} />}
            {screen === 'samples'      && <SamplesList setScreen={setScreen} setSelectedSampleId={setSelectedSampleId} />}
            {screen === 'sample_detail'&& <SampleDetail sampleId={selectedSampleId} setScreen={setScreen} />}
            {screen === 'result_entry' && <ResultEntry setScreen={setScreen} />}
          </div>
        </main>
      </div>

      {/* Mobile nav */}
      <nav className="lg:hidden fixed bottom-0 w-full bg-white border-t border-[#d1d9d1] flex z-40">
        {SIDEBAR.map(s => (
          <button key={s.id} onClick={() => setScreen(s.id as Screen)}
            className={`flex-1 flex flex-col items-center py-2.5 gap-0.5 text-xs ${screen === s.id ? 'text-[#166534] font-semibold' : 'text-gray-500'}`}>
            <span className="text-lg">{s.icon}</span><span>{s.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}

function LabDashboard({ setScreen, setSelectedSampleId }: any) {
  const { workspace } = useApp();
  const samples = workspace.samples ?? [];
  const results = workspace.results ?? [];
  return (
    <div className="space-y-6">
      <LiveWorkspaceStatus />
      <SectionHeader title="Lab Dashboard" subtitle="GBRC Gandhinagar · 12 September 2026" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Samples" value={samples.length} sub="in your lab scope" />
        <StatCard label="In Progress" value={samples.length} sub="live sample queue" accent="blue" />
        <StatCard label="Results" value={results.length} sub="available results" accent="amber" />
        <StatCard label="Completed" value={results.length} sub="results issued" accent="green" />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Pending Action" action={<Btn variant="ghost" size="sm" onClick={() => setScreen('samples')}>All →</Btn>} />
          <div className="divide-y divide-[#e9ede9]">
            {mockSamples.filter(s => s.status !== 'completed').map(s => (
              <div key={s.id} className="px-4 py-3 cursor-pointer hover:bg-green-50"
                onClick={() => { setSelectedSampleId(s.id); setScreen('sample_detail'); }}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-mono text-xs text-gray-400">{s.id}</p>
                    <p className="text-sm font-semibold text-gray-800">{s.disease} — {s.sampleType}</p>
                    <p className="text-xs text-gray-500">{s.collectedBy} · {new Date(s.collectionDate).toLocaleDateString()}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <StatusBadge status={s.status} />
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium border
                      ${s.priority === 'critical' ? 'text-red-700 bg-red-50 border-red-200' :
                        s.priority === 'urgent' ? 'text-amber-700 bg-amber-50 border-amber-200' :
                        'text-gray-500 bg-gray-50 border-gray-200'}`}>
                      {s.priority}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="px-4 py-3 border-t border-[#d1d9d1]">
            <Btn variant="primary" fullWidth onClick={() => setScreen('result_entry')}>✍ Enter Results</Btn>
          </div>
        </Card>

        <Card>
          <CardHeader title="Test Statistics — September 2026" />
          <div className="p-5 space-y-3">
            {[
              { disease: 'FMD', total: 8, positive: 3, pending: 2 },
              { disease: 'LSD', total: 5, positive: 4, pending: 0 },
              { disease: 'PPR', total: 6, positive: 2, pending: 1 },
              { disease: 'BQ', total: 3, positive: 2, pending: 1 },
              { disease: 'HS', total: 4, positive: 1, pending: 0 },
            ].map(({ disease, total, positive, pending }) => (
              <div key={disease} className="flex items-center gap-4">
                <span className="text-sm font-medium text-gray-700 w-16">{disease}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-3 overflow-hidden">
                  <div className="h-3 flex">
                    <div className="bg-red-500 h-full" style={{ width: `${(positive/total)*100}%` }} title="Positive" />
                    <div className="bg-amber-400 h-full" style={{ width: `${(pending/total)*100}%` }} title="Pending" />
                  </div>
                </div>
                <span className="font-mono text-xs text-gray-500 w-20 text-right">{positive}+ / {total} total</span>
              </div>
            ))}
            <div className="flex items-center gap-4 text-xs text-gray-500 mt-2">
              <span className="flex items-center gap-1"><span className="w-3 h-2 bg-red-500 rounded-sm inline-block" />Positive</span>
              <span className="flex items-center gap-1"><span className="w-3 h-2 bg-amber-400 rounded-sm inline-block" />Pending</span>
              <span className="flex items-center gap-1"><span className="w-3 h-2 bg-gray-100 rounded-sm inline-block border border-gray-200" />Negative</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

function SamplesList({ setScreen, setSelectedSampleId }: any) {
  const [statusFilter, setStatusFilter] = useState('all');
  const filtered = mockSamples.filter(s => statusFilter === 'all' || s.status === statusFilter);

  return (
    <div className="space-y-5">
      <SectionHeader title="Samples" subtitle={`${mockSamples.length} total samples`} />
      <Select value={statusFilter} onChange={setStatusFilter}>
        <option value="all">All statuses</option>
        <option value="in_transit">In Transit</option>
        <option value="received">Received</option>
        <option value="testing">Testing</option>
        <option value="completed">Completed</option>
      </Select>
      <Card>
        <Table headers={['Sample ID', 'Report', 'Disease', 'Type', 'Animal', 'Priority', 'Collected By', 'Status', 'Result']}>
          {filtered.map(s => (
            <TR key={s.id} onClick={() => { setSelectedSampleId(s.id); setScreen('sample_detail'); }}>
              <TD mono>{s.id}</TD>
              <TD mono>{s.reportId}</TD>
              <TD bold>{s.disease}</TD>
              <TD>{s.sampleType}</TD>
              <TD mono>{s.animalTag}</TD>
              <TD>
                <span className={`text-xs px-2 py-0.5 rounded font-medium border
                  ${s.priority === 'critical' ? 'text-red-700 bg-red-50 border-red-200' :
                    s.priority === 'urgent' ? 'text-amber-700 bg-amber-50 border-amber-200' :
                    'text-gray-500 bg-gray-50 border-gray-200'}`}>{s.priority}</span>
              </TD>
              <TD>{s.collectedBy}</TD>
              <TD><StatusBadge status={s.status} /></TD>
              <TD>{s.result ? <span className="text-xs font-semibold text-red-700">Positive</span> : <span className="text-xs text-gray-400">—</span>}</TD>
            </TR>
          ))}
        </Table>
        {filtered.length === 0 && <EmptyState icon="🧪" title="No samples match filter" />}
      </Card>
    </div>
  );
}

function SampleDetail({ sampleId, setScreen }: any) {
  const sample = mockSamples.find(s => s.id === sampleId) || mockSamples[0];

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={() => setScreen('samples')} className="text-sm text-[#166534] font-medium hover:underline">← Samples</button>
        <span className="font-mono text-sm text-gray-400">{sample.id}</span>
      </div>

      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="font-display font-700 text-2xl text-gray-900">{sample.disease}</h2>
          <p className="text-gray-500">{sample.sampleType} · {sample.animalTag}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={sample.status} />
          <span className={`text-sm px-2 py-0.5 rounded font-semibold border
            ${sample.priority === 'critical' ? 'text-red-700 bg-red-50 border-red-200' :
              sample.priority === 'urgent' ? 'text-amber-700 bg-amber-50 border-amber-200' :
              'text-gray-500 bg-gray-50 border-gray-200'}`}>{sample.priority}</span>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-5">
        <Card>
          <CardHeader title="Sample Information" />
          <div className="divide-y divide-[#e9ede9]">
            {[
              ['Report ID', sample.reportId],
              ['Animal Tag', sample.animalTag],
              ['Collected By', sample.collectedBy],
              ['Collected On', new Date(sample.collectionDate).toLocaleString()],
              ['Lab', sample.labName],
            ].map(([k, v]) => (
              <div key={k} className="px-4 py-2.5 flex justify-between text-sm">
                <span className="text-gray-500">{k}</span>
                <span className="font-medium font-mono text-gray-700 text-xs">{v}</span>
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-4">
          {sample.testsConducted && (
            <Card className="p-4">
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Tests Conducted</p>
              {sample.testsConducted.map(t => (
                <div key={t} className="flex items-center gap-2 py-1.5 border-b border-[#e9ede9] last:border-0">
                  <span className="text-green-600 text-sm">●</span>
                  <span className="text-sm text-gray-700">{t}</span>
                </div>
              ))}
            </Card>
          )}
          {sample.result ? (
            <Card className="p-4 border-l-4 border-l-red-500">
              <p className="text-xs font-semibold text-red-700 uppercase mb-1">Result</p>
              <p className="text-sm text-gray-800">{sample.result}</p>
              {sample.resultDate && <p className="text-xs text-gray-400 mt-1">Entered: {new Date(sample.resultDate).toLocaleString()}</p>}
            </Card>
          ) : (
            <Btn variant="primary" fullWidth size="lg" onClick={() => setScreen('result_entry')}>
              ✍ Enter Test Result
            </Btn>
          )}
        </div>
      </div>
    </div>
  );
}

function ResultEntry({ setScreen }: any) {
  const [sampleId, setSampleId] = useState('SMP-2026-04210');
  const [result, setResult] = useState<'positive' | 'negative' | 'inconclusive' | ''>('');
  const [findings, setFindings] = useState('');
  const [testsUsed, setTestsUsed] = useState<string[]>([]);
  const [submitted, setSubmitted] = useState(false);

  const toggleTest = (t: string) => setTestsUsed(ts => ts.includes(t) ? ts.filter(x => x !== t) : [...ts, t]);

  if (submitted) {
    return (
      <div className="py-16 flex flex-col items-center text-center gap-4">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center text-3xl">✓</div>
        <h3 className="font-display font-700 text-xl">Result Submitted</h3>
        <p className="text-sm text-gray-500 max-w-xs">Result for <strong className="font-mono">{sampleId}</strong> has been recorded and the veterinarian has been notified.</p>
        <Btn variant="primary" onClick={() => { setSubmitted(false); setScreen('samples'); }}>Back to Samples</Btn>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <button onClick={() => setScreen('samples')} className="text-sm text-[#166534] font-medium hover:underline">← Samples</button>
      </div>
      <SectionHeader title="Enter Test Results" />
      <Card className="p-6 space-y-5">
        <FormField label="Sample ID" required>
          <Select value={sampleId} onChange={setSampleId}>
            {mockSamples.filter(s => s.status !== 'completed').map(s => (
              <option key={s.id} value={s.id}>{s.id} — {s.disease} ({s.sampleType})</option>
            ))}
          </Select>
        </FormField>

        <FormField label="Tests Conducted" required>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {['RT-PCR', 'ELISA', 'AGID', 'Virus Isolation', 'HI Test', 'CFT', 'Rose Bengal Test', 'Microscopy'].map(t => (
              <button key={t} onClick={() => toggleTest(t)}
                className={`text-sm p-2.5 rounded border text-left transition-colors
                  ${testsUsed.includes(t) ? 'border-[#166534] bg-green-50 text-[#166534] font-medium' : 'border-[#d1d9d1] bg-white text-gray-700 hover:border-green-300'}`}>
                {testsUsed.includes(t) && <span className="mr-1">✓</span>}{t}
              </button>
            ))}
          </div>
        </FormField>

        <FormField label="Result" required>
          <div className="grid grid-cols-3 gap-3">
            {(['positive', 'negative', 'inconclusive'] as const).map(r => (
              <button key={r} onClick={() => setResult(r)}
                className={`py-3 rounded-lg border-2 text-sm font-semibold capitalize transition-colors
                  ${result === r
                    ? r === 'positive' ? 'border-red-600 bg-red-50 text-red-700'
                      : r === 'negative' ? 'border-green-600 bg-green-50 text-green-700'
                      : 'border-amber-500 bg-amber-50 text-amber-700'
                    : 'border-[#d1d9d1] bg-white text-gray-600 hover:border-gray-400'}`}>
                {r}
              </button>
            ))}
          </div>
        </FormField>

        {result === 'positive' && (
          <AlertBanner type="error" title="Positive Result — Notifying veterinarian immediately"
            message="The assigned veterinarian will be alerted. Please complete findings below." />
        )}

        <FormField label="Detailed Findings" required hint="Describe test findings, Ct values, titers, etc.">
          <Textarea value={findings} onChange={setFindings} rows={5}
            placeholder="e.g. RT-PCR: Ct value 22.4 (positive threshold <35). FMD virus detected. Serotype pending." />
        </FormField>

        <Btn variant="primary" fullWidth size="lg" disabled={!result || !findings || testsUsed.length === 0}
          onClick={() => setSubmitted(true)}>
          Submit Test Result
        </Btn>
      </Card>
    </div>
  );
}
