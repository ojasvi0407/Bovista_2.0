import { useState } from 'react';
import { useApp } from '../../App';
import LiveWorkspaceStatus from '../../components/LiveWorkspaceStatus';
import {
  Card, CardHeader, StatCard, Btn, RiskBadge, StatusBadge, Table, TR, TD,
  AlertBanner, EmptyState, OfflineBanner, SectionHeader, FormField,
  Input, Select, Textarea, ProgressSteps, Timeline,
} from '../../components/ui';
import { mockAnimals, mockReports, mockVaccinations, SYMPTOMS, DISTRICTS } from '../../mockData';
import type { WizardData } from '../../types';

type Screen = 'dashboard' | 'animals' | 'animal_detail' | 'wizard' | 'report_status' | 'vaccinations' | 'treatments' | 'alerts';

const NAV = [
  { id: 'dashboard',   icon: '⊞',  label: 'Home' },
  { id: 'animals',     icon: '🐄',  label: 'Animals' },
  { id: 'wizard',      icon: '+',   label: 'Report' },
  { id: 'vaccinations',icon: '💉',  label: 'Vaccines' },
  { id: 'alerts',      icon: '🔔',  label: 'Alerts' },
] as const;

export default function FarmerApp() {
  const { t, lang, isOnline, logout } = useApp();
  const [screen, setScreen] = useState<Screen>('dashboard');
  const [selectedAnimalId, setSelectedAnimalId] = useState<string | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [isOffline] = useState(false);
  const [pendingSync] = useState(1);

  const farmer = { name: 'Ramesh Patel', village: 'Bhadaj', district: 'Ahmedabad', id: 'f1' };
  const myReports = mockReports.filter(r => r.farmerId === 'f1');

  return (
    <div className="min-h-screen bg-[#f7f9f7] flex flex-col max-w-lg mx-auto">
      {/* Header */}
      <header className="bg-[#166534] text-white px-4 py-3 sticky top-0 z-40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="text-xl">🐄</div>
            <div>
              <span className="font-display font-700 text-base">
                {lang === 'en' ? 'PashuMitra' : lang === 'hi' ? 'पशुमित्र' : 'પશુમિત્ર'}
              </span>
              <div className="text-green-200 text-xs">{farmer.name} · {farmer.village}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${isOnline ? 'bg-green-700 text-green-100' : 'bg-amber-600 text-amber-100'}`}>
              {isOnline ? '● Online' : '○ Offline'}
            </span>
            <button onClick={logout} className="text-green-200 hover:text-white text-xs px-2 py-1 rounded hover:bg-white/10" aria-label="Log out">↩</button>
          </div>
        </div>
      </header>

      {!isOnline && <OfflineBanner pendingCount={pendingSync} />}

      {/* Critical Alert */}
      {screen === 'dashboard' && (
        <div className="px-4 pt-3">
          <AlertBanner type="warning" title="FMD Alert: Daskroi Block"
            message="8 cases reported nearby. Check your herd and report any symptoms." />
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 overflow-y-auto pb-20">
        {screen === 'dashboard' && <FarmerDashboard setScreen={setScreen} setSelectedReportId={setSelectedReportId} myReports={myReports} />}
        {screen === 'animals' && <AnimalsList setScreen={setScreen} setSelectedAnimalId={setSelectedAnimalId} />}
        {screen === 'animal_detail' && <AnimalDetail animalId={selectedAnimalId} setScreen={setScreen} />}
        {screen === 'wizard' && <DiseaseWizard setScreen={setScreen} isOffline={isOffline} />}
        {screen === 'report_status' && <ReportStatus reportId={selectedReportId} setScreen={setScreen} />}
        {screen === 'vaccinations' && <Vaccinations />}
        {screen === 'treatments' && <Treatments />}
        {screen === 'alerts' && <AlertsScreen setScreen={setScreen} setSelectedReportId={setSelectedReportId} />}
      </main>

      {/* Bottom nav */}
      <nav className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-lg bg-white border-t border-[#d1d9d1] flex z-40" role="navigation">
        {NAV.map(n => (
          <button key={n.id} onClick={() => setScreen(n.id as Screen)}
            aria-current={screen === n.id || (screen === 'animal_detail' && n.id === 'animals') ? 'page' : undefined}
            className={`flex-1 flex flex-col items-center py-2.5 gap-0.5 text-xs transition-colors focus:outline-none
              ${screen === n.id ? 'text-[#166534] font-semibold' : 'text-gray-500'}`}>
            <span className={`text-lg leading-none ${n.id === 'wizard' ? 'bg-[#166534] text-white w-10 h-10 rounded-full flex items-center justify-center text-xl -mt-5 shadow-lg border-4 border-[#f7f9f7]' : ''}`}>
              {n.icon}
            </span>
            <span>{n.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}

// ── Dashboard ──────────────────────────────────────────────────────────────
function FarmerDashboard({ setScreen, setSelectedReportId, myReports }: any) {
  const { workspace } = useApp();
  const liveAnimals = workspace.animals ?? [];
  const liveReports = workspace.reports ?? [];
  const liveVaccinations = workspace.vaccinations ?? [];
  const liveAlerts = workspace.alerts ?? [];
  return (
    <div className="px-4 py-4 space-y-5">
      <LiveWorkspaceStatus />
      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="My Animals" value={liveAnimals.length} sub="registered in your scope" accent="green" />
        <StatCard label="Active Reports" value={liveReports.length} sub="visible to you" accent="amber" />
        <StatCard label="Vaccines Due" value={liveVaccinations.length} sub="scheduled or overdue" accent="blue" />
        <StatCard label="Alerts" value={liveAlerts.length} sub="active notifications" accent="red" />
      </div>

      {/* Quick actions */}
      <Card>
        <CardHeader title="Quick Actions" />
        <div className="p-4 grid grid-cols-2 gap-2">
          <Btn variant="primary" size="lg" fullWidth onClick={() => setScreen('wizard')}>
            <span>🚨</span> Report Disease
          </Btn>
          <Btn variant="secondary" size="lg" fullWidth onClick={() => setScreen('animals')}>
            <span>🐄</span> View Animals
          </Btn>
          <Btn variant="secondary" size="lg" fullWidth onClick={() => setScreen('vaccinations')}>
            <span>💉</span> Vaccinations
          </Btn>
          <Btn variant="secondary" size="lg" fullWidth onClick={() => setScreen('alerts')}>
            <span>🔔</span> View Alerts
          </Btn>
        </div>
      </Card>

      {/* Recent reports */}
      <div>
        <SectionHeader title="My Reports" action={
          <Btn variant="ghost" size="sm" onClick={() => setScreen('report_status')}>View all →</Btn>
        } />
        <div className="space-y-2">
          {myReports.slice(0, 3).map((r: any) => (
            <Card key={r.id} className="p-4 cursor-pointer hover:border-green-400 transition-colors"
              onClick={() => { setSelectedReportId(r.id); setScreen('report_status'); }}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs text-gray-500">{r.id}</span>
                    <StatusBadge status={r.status} />
                  </div>
                  <p className="text-sm font-medium text-gray-800 mt-1">{r.species} · {r.affectedCount} affected</p>
                  <p className="text-xs text-gray-500 mt-0.5">{new Date(r.createdAt).toLocaleDateString()}</p>
                </div>
                <RiskBadge level={r.riskLevel} compact />
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Vaccination due */}
      <Card>
        <CardHeader title="Vaccination Reminders" />
        <div className="divide-y divide-[#e9ede9]">
          {mockVaccinations.filter(v => v.status === 'overdue' || v.status === 'due').map(v => (
            <div key={v.id} className="px-4 py-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-800">{v.vaccine}</p>
                <p className="text-xs text-gray-500">{v.animalTag} · Due: {v.dueDate}</p>
              </div>
              <StatusBadge status={v.status} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ── Animals List ────────────────────────────────────────────────────────────
function AnimalsList({ setScreen, setSelectedAnimalId }: any) {
  const [search, setSearch] = useState('');
  const filtered = mockAnimals.filter(a =>
    a.tagId.toLowerCase().includes(search.toLowerCase()) ||
    a.breed.toLowerCase().includes(search.toLowerCase()) ||
    a.species.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="px-4 py-4 space-y-4">
      <SectionHeader title="My Animals" subtitle="24 animals registered" />
      <Input value={search} onChange={setSearch} placeholder="Search by tag, breed, species..." />
      {filtered.length === 0 ? (
        <EmptyState icon="🐄" title="No animals found" description="Try a different search term." />
      ) : (
        <div className="space-y-2">
          {filtered.map(a => (
            <Card key={a.id} className="p-4 cursor-pointer hover:border-green-400 transition-colors"
              onClick={() => { setSelectedAnimalId(a.id); setScreen('animal_detail'); }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="text-2xl">{a.species === 'Cattle' ? '🐄' : a.species === 'Buffalo' ? '🐃' : a.species === 'Goat' ? '🐐' : a.species === 'Camel' ? '🐪' : '🐑'}</div>
                  <div>
                    <p className="font-mono text-xs text-gray-500">{a.tagId}</p>
                    <p className="text-sm font-semibold text-gray-900">{a.species} — {a.breed}</p>
                    <p className="text-xs text-gray-500">{a.sex === 'F' ? 'Female' : 'Male'} · {a.age} · {a.weight}</p>
                  </div>
                </div>
                <StatusBadge status={a.healthStatus} />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Animal Detail ────────────────────────────────────────────────────────────
function AnimalDetail({ animalId, setScreen }: any) {
  const animal = mockAnimals.find(a => a.id === animalId) || mockAnimals[0];
  const reports = mockReports.filter(r => r.species === animal.species && r.farmerId === 'f1');

  return (
    <div className="px-4 py-4 space-y-4">
      <button onClick={() => setScreen('animals')} className="text-sm text-[#166534] font-medium flex items-center gap-1">
        ← Animals
      </button>

      <Card>
        <div className="p-5 flex items-center gap-4">
          <div className="text-5xl">{animal.species === 'Cattle' ? '🐄' : animal.species === 'Buffalo' ? '🐃' : '🐐'}</div>
          <div>
            <p className="font-mono text-xs text-gray-500 mb-1">{animal.tagId}</p>
            <h2 className="font-display font-700 text-xl text-gray-900">{animal.species} — {animal.breed}</h2>
            <StatusBadge status={animal.healthStatus} />
          </div>
        </div>
        <div className="border-t border-[#d1d9d1] px-5 py-4 grid grid-cols-2 gap-3 text-sm">
          {[
            ['Sex', animal.sex === 'F' ? 'Female' : 'Male'],
            ['Age', animal.age],
            ['Weight', animal.weight || '—'],
            ['Last Exam', animal.lastExam],
          ].map(([k, v]) => (
            <div key={k}>
              <p className="text-xs text-gray-500">{k}</p>
              <p className="font-medium text-gray-800">{v}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <CardHeader title="Vaccination History" />
        <div className="divide-y divide-[#e9ede9]">
          {animal.vaccinations.map(v => (
            <div key={v} className="px-4 py-3 flex items-center justify-between">
              <span className="text-sm text-gray-700">{v}</span>
              <StatusBadge status="completed" />
            </div>
          ))}
          {animal.vaccinations.length === 0 && (
            <p className="px-4 py-4 text-sm text-gray-500">No vaccinations recorded.</p>
          )}
        </div>
      </Card>

      {reports.length > 0 && (
        <Card>
          <CardHeader title="Disease Reports" />
          <div className="divide-y divide-[#e9ede9]">
            {reports.map(r => (
              <div key={r.id} className="px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="font-mono text-xs text-gray-500">{r.id}</p>
                  <p className="text-sm text-gray-700">{r.disease || 'Under investigation'}</p>
                </div>
                <StatusBadge status={r.status} />
              </div>
            ))}
          </div>
        </Card>
      )}

      <Btn variant="danger" fullWidth onClick={() => setScreen('wizard')}>
        🚨 Report Health Issue for This Animal
      </Btn>
    </div>
  );
}

// ── Disease Report Wizard ────────────────────────────────────────────────────
const WIZARD_STEPS = ['Animal', 'Symptoms', 'Count', 'Location', 'Environment', 'Photo', 'Review', 'Submit'];

function DiseaseWizard({ setScreen, isOffline }: { setScreen: (s: Screen) => void; isOffline: boolean }) {
  const [step, setStep] = useState(0);
  const [data, setData] = useState<WizardData>({ step: 0 });
  const [submitted, setSubmitted] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const update = (patch: Partial<WizardData>) => setData(d => ({ ...d, ...patch }));

  const handleNext = () => {
    if (step < 7) setStep(s => s + 1);
  };
  const handleBack = () => {
    if (step > 0) setStep(s => s - 1);
    else setScreen('dashboard');
  };

  const handleSaveDraft = () => {
    setIsSaving(true);
    setTimeout(() => { setIsSaving(false); }, 1200);
  };

  const handleSubmit = () => {
    setIsSaving(true);
    setTimeout(() => { setIsSaving(false); setSubmitted(true); }, 1800);
  };

  if (submitted) {
    return (
      <div className="px-4 py-10 flex flex-col items-center text-center gap-4">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center text-4xl">✓</div>
        <h2 className="font-display font-700 text-xl text-gray-900">Report Submitted</h2>
        <p className="text-gray-500 text-sm max-w-xs">
          Your report <strong className="font-mono">RPT-2026-08912</strong> has been submitted.
          {isOffline ? ' It will sync when you\'re back online.' : ' A Para-vet will be assigned within 24 hours.'}
        </p>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800 text-left">
          <p className="font-semibold mb-1">⚠ AI Decision Support Note</p>
          <p>Symptom pattern suggests possible FMD. <strong>This is not a diagnosis.</strong> A qualified veterinarian will review your report and contact you.</p>
        </div>
        <div className="flex gap-3 mt-2">
          <Btn variant="primary" onClick={() => setScreen('report_status')}>Track Report</Btn>
          <Btn variant="secondary" onClick={() => setScreen('dashboard')}>Home</Btn>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-4 pb-2">
        <div className="flex items-center justify-between mb-3">
          <button onClick={handleBack} className="text-[#166534] text-sm font-medium">← Back</button>
          <span className="text-xs text-gray-500 font-mono">Step {step + 1} of 8</span>
          <button onClick={handleSaveDraft} className="text-xs text-gray-500 border border-[#d1d9d1] px-2 py-1 rounded hover:bg-gray-50">
            {isSaving ? '...' : 'Save Draft'}
          </button>
        </div>
        <ProgressSteps steps={WIZARD_STEPS} current={step} />
      </div>

      {isOffline && (
        <div className="px-4 py-2">
          <AlertBanner type="warning" title="Offline" message="Data will be saved locally and synced when connected." />
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {step === 0 && <WizardStep1 data={data} update={update} />}
        {step === 1 && <WizardStep2 data={data} update={update} />}
        {step === 2 && <WizardStep3 data={data} update={update} />}
        {step === 3 && <WizardStep4 data={data} update={update} />}
        {step === 4 && <WizardStep5 data={data} update={update} />}
        {step === 5 && <WizardStep6 data={data} update={update} />}
        {step === 6 && <WizardStep7 data={data} />}
        {step === 7 && <WizardStep8 data={data} isOffline={isOffline} onSubmit={handleSubmit} isSaving={isSaving} />}
      </div>

      {step < 7 && (
        <div className="px-4 pb-24 pt-2 border-t border-[#d1d9d1] bg-white">
          <Btn variant="primary" fullWidth size="lg" onClick={handleNext}>
            {step === 6 ? 'Submit Report' : 'Continue →'}
          </Btn>
        </div>
      )}
    </div>
  );
}

function WizardStep1({ data, update }: { data: WizardData; update: (p: Partial<WizardData>) => void }) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-display font-700 text-lg text-gray-900">Select Animal</h3>
        <p className="text-sm text-gray-500 mt-1">Which animal is showing health problems?</p>
      </div>
      <div className="space-y-2">
        {mockAnimals.filter(a => a.healthStatus !== 'deceased').map(a => (
          <button key={a.id} onClick={() => update({ animalId: a.id, animalTag: a.tagId, species: a.species })}
            className={`w-full text-left p-4 rounded-lg border-2 flex items-center gap-3 transition-colors
              ${data.animalId === a.id ? 'border-[#166534] bg-green-50' : 'border-[#d1d9d1] bg-white hover:border-green-300'}`}>
            <span className="text-3xl">{a.species === 'Cattle' ? '🐄' : a.species === 'Buffalo' ? '🐃' : '🐐'}</span>
            <div>
              <p className="font-mono text-xs text-gray-500">{a.tagId}</p>
              <p className="font-semibold text-gray-800">{a.species} — {a.breed}</p>
              <p className="text-xs text-gray-500">{a.sex === 'F' ? 'Female' : 'Male'} · {a.age}</p>
            </div>
            {data.animalId === a.id && <span className="ml-auto text-[#166534] text-xl">✓</span>}
          </button>
        ))}
        <button onClick={() => update({ animalId: 'other', animalTag: 'New Animal', species: 'Cattle' })}
          className={`w-full text-left p-4 rounded-lg border-2 border-dashed flex items-center gap-3 transition-colors
            ${data.animalId === 'other' ? 'border-[#166534] bg-green-50' : 'border-[#d1d9d1] bg-white hover:border-green-300'}`}>
          <span className="text-3xl">➕</span>
          <div>
            <p className="font-semibold text-gray-700">Unregistered Animal</p>
            <p className="text-xs text-gray-500">Report for an animal not yet in your list</p>
          </div>
        </button>
      </div>
      {data.animalId === 'other' && (
        <div className="space-y-3 bg-gray-50 rounded-lg p-3">
          <FormField label="Species" required>
            <Select value={data.species || ''} onChange={v => update({ species: v })}>
              <option value="">Select species</option>
              {['Cattle', 'Buffalo', 'Goat', 'Sheep', 'Camel'].map(s => <option key={s}>{s}</option>)}
            </Select>
          </FormField>
        </div>
      )}
    </div>
  );
}

function WizardStep2({ data, update }: { data: WizardData; update: (p: Partial<WizardData>) => void }) {
  const toggleSymptom = (s: string) => {
    const curr = data.symptoms || [];
    update({ symptoms: curr.includes(s) ? curr.filter(x => x !== s) : [...curr, s] });
  };
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-display font-700 text-lg text-gray-900">Select Symptoms</h3>
        <p className="text-sm text-gray-500 mt-1">Check all symptoms you have observed. Select as many as apply.</p>
      </div>
      {(data.symptoms?.length || 0) > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-700">
          ⚠ AI is analysing patterns to assist veterinarians — not to diagnose. {data.symptoms?.length} symptom(s) selected.
        </div>
      )}
      <div className="space-y-2">
        {SYMPTOMS.map(s => (
          <button key={s} onClick={() => toggleSymptom(s)}
            className={`w-full text-left p-3.5 rounded-lg border flex items-center gap-3 text-sm transition-colors
              ${(data.symptoms || []).includes(s) ? 'border-[#166534] bg-green-50 text-[#166534] font-medium' : 'border-[#d1d9d1] bg-white text-gray-700 hover:border-green-300'}`}>
            <span className={`w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 ${(data.symptoms || []).includes(s) ? 'bg-[#166534] border-[#166534]' : 'border-gray-300'}`}>
              {(data.symptoms || []).includes(s) && <span className="text-white text-xs">✓</span>}
            </span>
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function WizardStep3({ data, update }: { data: WizardData; update: (p: Partial<WizardData>) => void }) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-display font-700 text-lg text-gray-900">Affected Animals</h3>
        <p className="text-sm text-gray-500 mt-1">Tell us how many animals are affected.</p>
      </div>
      <div className="grid grid-cols-1 gap-4">
        <FormField label="Total animals in your herd" required>
          <Input type="number" value={String(data.totalAnimals || '')} onChange={v => update({ totalAnimals: parseInt(v) || 0 })} placeholder="e.g. 24" />
        </FormField>
        <FormField label="Number showing symptoms" required>
          <Input type="number" value={String(data.affectedCount || '')} onChange={v => update({ affectedCount: parseInt(v) || 0 })} placeholder="e.g. 5" />
        </FormField>
        <FormField label="Deaths (if any)" hint="Enter 0 if no deaths">
          <Input type="number" value={String(data.mortalityCount || '')} onChange={v => update({ mortalityCount: parseInt(v) || 0 })} placeholder="0" />
        </FormField>
      </div>
      {(data.mortalityCount || 0) > 0 && (
        <AlertBanner type="error" title="Mortality reported — priority escalation" message="Your report will be escalated to a veterinarian immediately." />
      )}
    </div>
  );
}

function WizardStep4({ data, update }: { data: WizardData; update: (p: Partial<WizardData>) => void }) {
  const [locating, setLocating] = useState(false);

  const getLocation = () => {
    setLocating(true);
    setTimeout(() => {
      update({ gpsLat: 23.0225, gpsLng: 72.5714, village: data.village || 'Bhadaj' });
      setLocating(false);
    }, 1500);
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-display font-700 text-lg text-gray-900">Location</h3>
        <p className="text-sm text-gray-500 mt-1">Where are the sick animals located?</p>
      </div>
      <Btn variant="secondary" fullWidth size="lg" onClick={getLocation} disabled={locating}>
        {locating ? '⏳ Getting location...' : data.gpsLat ? `✓ GPS: ${data.gpsLat.toFixed(4)}, ${data.gpsLng?.toFixed(4)}` : '📍 Use GPS Location'}
      </Btn>
      <div className="text-center text-xs text-gray-400">or enter manually</div>
      <div className="space-y-3">
        <FormField label="District" required>
          <Select value={data.district || ''} onChange={v => update({ district: v })}>
            <option value="">Select district</option>
            {DISTRICTS.map(d => <option key={d}>{d}</option>)}
          </Select>
        </FormField>
        <FormField label="Block / Taluka" required>
          <Input value={data.block || ''} onChange={v => update({ block: v })} placeholder="e.g. Daskroi" />
        </FormField>
        <FormField label="Village" required>
          <Input value={data.village || ''} onChange={v => update({ village: v })} placeholder="e.g. Bhadaj" />
        </FormField>
      </div>
    </div>
  );
}

function WizardStep5({ data, update }: { data: WizardData; update: (p: Partial<WizardData>) => void }) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-display font-700 text-lg text-gray-900">Environment & History</h3>
        <p className="text-sm text-gray-500 mt-1">This helps veterinarians understand the context.</p>
      </div>
      <FormField label="Water source">
        <Select value={data.waterSource || ''} onChange={v => update({ waterSource: v })}>
          <option value="">Select</option>
          <option>Open pond / tank</option>
          <option>Borewell / handpump</option>
          <option>Canal / river</option>
          <option>Municipal supply</option>
        </Select>
      </FormField>
      <div className="space-y-2">
        {[
          { key: 'recentMovement', label: 'Animals moved or transported recently?', val: data.recentMovement },
          { key: 'newAnimals', label: 'New animals added to herd in last 30 days?', val: data.newAnimals },
        ].map(({ key, label, val }) => (
          <button key={key} onClick={() => update({ [key]: !val })}
            className={`w-full text-left p-4 rounded-lg border flex items-center justify-between text-sm transition-colors
              ${val ? 'border-[#166534] bg-green-50' : 'border-[#d1d9d1] bg-white hover:border-green-300'}`}>
            <span>{label}</span>
            <span className={`px-2 py-0.5 rounded text-xs font-semibold ${val ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{val ? 'Yes' : 'No'}</span>
          </button>
        ))}
      </div>
      <FormField label="Additional observations" hint="Describe anything unusual you noticed">
        <Textarea value={data.notes || ''} onChange={v => update({ notes: v })} placeholder="e.g. Animals near the pond, water looked murky..." rows={4} />
      </FormField>
    </div>
  );
}

function WizardStep6({ data, update }: { data: WizardData; update: (p: Partial<WizardData>) => void }) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-display font-700 text-lg text-gray-900">Photo Evidence</h3>
        <p className="text-sm text-gray-500 mt-1">Photos help veterinarians assess the condition remotely.</p>
      </div>
      <button
        onClick={() => update({ photoTaken: !data.photoTaken })}
        className={`w-full aspect-video rounded-lg border-2 border-dashed flex flex-col items-center justify-center gap-3 transition-colors
          ${data.photoTaken ? 'border-[#166534] bg-green-50' : 'border-[#d1d9d1] bg-gray-50 hover:border-green-300'}`}>
        {data.photoTaken ? (
          <>
            <span className="text-4xl">✓</span>
            <p className="text-sm font-medium text-[#166534]">Photo captured</p>
            <p className="text-xs text-gray-500">Tap to retake</p>
          </>
        ) : (
          <>
            <span className="text-5xl">📷</span>
            <p className="text-sm font-medium text-gray-700">Take Photo</p>
            <p className="text-xs text-gray-500">Capture affected area, lesions, or whole animal</p>
          </>
        )}
      </button>
      <p className="text-xs text-gray-400 text-center">Photos are optional but highly recommended. Max 5 photos, 10 MB each.</p>
      <Btn variant="ghost" fullWidth onClick={() => update({ photoTaken: false })}>
        Skip this step
      </Btn>
    </div>
  );
}

function WizardStep7({ data }: { data: WizardData }) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-display font-700 text-lg text-gray-900">Review Your Report</h3>
        <p className="text-sm text-gray-500 mt-1">Please review all information before submitting.</p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
        <p className="font-semibold">⚠ AI Triage Note — Decision Support Only</p>
        <p className="mt-1 text-xs">Based on reported symptoms, a risk assessment has been generated for veterinary review. This is <strong>not a diagnosis</strong> and does not replace professional evaluation.</p>
        <p className="mt-1 text-xs font-medium">Suggested: Possible FMD / Viral condition — Risk Score: 72/100 (High)</p>
      </div>

      <Card>
        <div className="divide-y divide-[#e9ede9]">
          {[
            ['Animal', data.animalTag || '—'],
            ['Species', data.species || '—'],
            ['Symptoms', (data.symptoms || []).length ? data.symptoms!.join(', ') : '—'],
            ['Affected', `${data.affectedCount || 0} of ${data.totalAnimals || 0} animals`],
            ['Deaths', String(data.mortalityCount || 0)],
            ['Location', [data.village, data.block, data.district].filter(Boolean).join(', ') || '—'],
            ['GPS', data.gpsLat ? `${data.gpsLat.toFixed(4)}, ${data.gpsLng?.toFixed(4)}` : 'Not captured'],
            ['New animals', data.newAnimals ? 'Yes' : 'No'],
            ['Recent movement', data.recentMovement ? 'Yes' : 'No'],
            ['Photos', data.photoTaken ? 'Attached' : 'None'],
          ].map(([k, v]) => (
            <div key={k} className="px-4 py-2.5 flex items-start justify-between gap-3">
              <span className="text-xs text-gray-500 w-28 flex-shrink-0">{k}</span>
              <span className="text-sm text-gray-800 text-right">{v}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function WizardStep8({ data, isOffline, onSubmit, isSaving }: any) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-display font-700 text-lg text-gray-900">Submit Report</h3>
        <p className="text-sm text-gray-500 mt-1">By submitting, you confirm the information is accurate.</p>
      </div>
      {isOffline && (
        <AlertBanner type="warning" title="Offline submission" message="Your report will be stored locally and submitted automatically when internet is available." />
      )}
      <Card className="p-4 space-y-3">
        <p className="text-sm font-semibold text-gray-800">What happens next?</p>
        <div className="space-y-2">
          {[
            { step: '1', text: 'Your report is received and AI triage is applied' },
            { step: '2', text: 'A Para-vet or Veterinarian is assigned within 24 hours' },
            { step: '3', text: 'Field visit scheduled if needed' },
            { step: '4', text: 'You will receive SMS/app notifications on your report status' },
          ].map(({ step, text }) => (
            <div key={step} className="flex items-start gap-3 text-sm">
              <span className="w-6 h-6 bg-[#166534] text-white rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">{step}</span>
              <span className="text-gray-600">{text}</span>
            </div>
          ))}
        </div>
      </Card>
      <Btn variant="primary" fullWidth size="lg" onClick={onSubmit} disabled={isSaving}>
        {isSaving ? '⏳ Submitting...' : isOffline ? '📱 Save & Queue for Sync' : '🚀 Submit Report'}
      </Btn>
    </div>
  );
}

// ── Report Status ────────────────────────────────────────────────────────────
function ReportStatus({ reportId, setScreen }: any) {
  const report = mockReports.find(r => r.id === reportId) || mockReports[0];
  const timelineItems = [
    { date: '10 Sep 2026, 08:30', title: 'Report Submitted', desc: 'Via mobile app (offline sync)', done: true },
    { date: '10 Sep 2026, 09:15', title: 'AI Triage Completed', desc: `Risk score: ${report.riskScore}/100 (${report.riskLevel})`, done: true },
    { date: '10 Sep 2026, 11:00', title: 'Para-vet Assigned', desc: `Mohan Desai, Daskroi Block`, done: true },
    { date: '11 Sep 2026, 10:30', title: 'Sample Collected', desc: 'Epithelial tissue + serum dispatched to GBRC', done: report.status !== 'under_review' },
    { date: 'Pending', title: 'Lab Results', desc: 'PCR analysis in progress', done: false },
    { date: 'Pending', title: 'Veterinarian Review', desc: 'Awaiting lab confirmation', done: false },
  ];

  return (
    <div className="px-4 py-4 space-y-4">
      <button onClick={() => setScreen('dashboard')} className="text-sm text-[#166534] font-medium flex items-center gap-1">← Dashboard</button>

      <Card>
        <div className="p-4">
          <div className="flex items-start justify-between flex-wrap gap-2">
            <div>
              <p className="font-mono text-xs text-gray-500">{report.id}</p>
              <h3 className="font-display font-700 text-lg text-gray-900 mt-0.5">
                {report.species} — {report.affectedCount} Affected
              </h3>
            </div>
            <RiskBadge level={report.riskLevel} score={report.riskScore} />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusBadge status={report.status} />
            {report.disease && <span className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded">{report.disease}</span>}
          </div>
        </div>
        <div className="border-t border-[#d1d9d1] px-4 py-3 grid grid-cols-2 gap-2 text-sm">
          <div><p className="text-xs text-gray-500">Location</p><p className="font-medium">{report.village}, {report.district}</p></div>
          <div><p className="text-xs text-gray-500">Reported</p><p className="font-medium">{new Date(report.createdAt).toLocaleDateString()}</p></div>
          <div><p className="text-xs text-gray-500">Assigned Vet</p><p className="font-medium">{report.assignedVet || '—'}</p></div>
          <div><p className="text-xs text-gray-500">Para-vet</p><p className="font-medium">{report.assignedParavet || '—'}</p></div>
        </div>
      </Card>

      {report.aiSuggestion && (
        <Card className="p-4 border-l-4 border-l-amber-400">
          <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1">AI Decision Support</p>
          <p className="text-sm text-gray-700">{report.aiSuggestion}</p>
          <p className="text-xs text-gray-400 mt-2">This is decision support for veterinarians, not a diagnosis.</p>
        </Card>
      )}

      <Card>
        <CardHeader title="Progress Timeline" />
        <div className="px-4 py-4">
          <Timeline items={timelineItems} />
        </div>
      </Card>
    </div>
  );
}

// ── Vaccinations ─────────────────────────────────────────────────────────────
function Vaccinations() {
  return (
    <div className="px-4 py-4 space-y-4">
      <SectionHeader title="Vaccinations" subtitle="Schedule and history for your animals" />
      {mockVaccinations.filter(v => v.status === 'overdue').map(v => (
        <AlertBanner key={v.id} type="error" title={`Overdue: ${v.vaccine}`} message={`${v.animalTag} — Due date: ${v.dueDate}`} />
      ))}
      <div className="space-y-2">
        {mockVaccinations.map(v => (
          <Card key={v.id} className="p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-semibold text-sm text-gray-800">{v.vaccine}</p>
                <p className="text-xs text-gray-500 mt-0.5">{v.animalTag} · {v.disease}</p>
                <p className="text-xs text-gray-500">Due: {v.dueDate}{v.completedDate ? ` · Done: ${v.completedDate}` : ''}</p>
                {v.administeredBy && <p className="text-xs text-gray-400">By: {v.administeredBy}</p>}
              </div>
              <StatusBadge status={v.status} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Treatments ────────────────────────────────────────────────────────────────
function Treatments() {
  return (
    <div className="px-4 py-4 space-y-4">
      <SectionHeader title="Active Treatments" />
      <Card className="p-4 border-l-4 border-l-amber-400">
        <p className="text-xs text-amber-700 font-semibold uppercase mb-1">Treatment — Active</p>
        <p className="font-semibold text-gray-800">Anti-viral + Supportive therapy</p>
        <p className="text-xs text-gray-500 mt-1">GJ-AHD-00144 (Buffalo) · Started 08 Sep 2026</p>
        <p className="text-xs text-gray-500">Prescribed by: Dr. Anjali Sharma</p>
        <div className="mt-3 flex gap-2">
          <span className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded border border-amber-200">Day 4 of 10</span>
          <StatusBadge status="under_review" />
        </div>
      </Card>
      <EmptyState icon="💊" title="No other active treatments" description="Your animals are otherwise healthy." />
    </div>
  );
}

// ── Alerts ────────────────────────────────────────────────────────────────────
function AlertsScreen({ setScreen, setSelectedReportId }: any) {
  return (
    <div className="px-4 py-4 space-y-4">
      <SectionHeader title="Alerts & Notifications" />
      {[
        { type: 'error' as const, title: 'FMD Outbreak — Daskroi Block', message: '8 cases confirmed within 5 km. Check your herd. Isolate any symptomatic animals immediately.', date: '12 Sep 2026', action: true },
        { type: 'warning' as const, title: 'Vaccination Overdue', message: 'GJ-AHD-00143 FMD booster was due 15 Sep 2026. Contact your nearest veterinarian.', date: '11 Sep 2026', action: false },
        { type: 'info' as const, title: 'Report Update: RPT-2026-08741', message: 'Sample collected by Para-vet Mohan Desai. Lab results expected in 3-5 days.', date: '11 Sep 2026', action: true },
      ].map((a, i) => (
        <div key={i}>
          <AlertBanner type={a.type} title={a.title} message={a.message} />
          <div className="flex items-center justify-between mt-1 px-1">
            <span className="text-xs text-gray-400">{a.date}</span>
            {a.action && (
              <button onClick={() => { setSelectedReportId('RPT-2026-08741'); setScreen('report_status'); }}
                className="text-xs text-[#166534] font-medium hover:underline">
                View Report →
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
