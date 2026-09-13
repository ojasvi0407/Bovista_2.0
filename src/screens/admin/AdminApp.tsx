import { useState } from 'react';
import { useApp } from '../../App';
import LiveWorkspaceStatus from '../../components/LiveWorkspaceStatus';
import {
  Card, CardHeader, StatCard, Btn, StatusBadge, Table, TR, TD,
  AlertBanner, EmptyState, SectionHeader, FormField, Input, Select, Tabs,
} from '../../components/ui';
import { mockUsers, mockAuditLogs, DISEASES, SYMPTOMS } from '../../mockData';

type Screen = 'dashboard' | 'users' | 'knowledge_base' | 'symptoms' | 'locations' | 'audit_logs';

const SIDEBAR = [
  { id: 'dashboard',      icon: '⊞', label: 'Dashboard' },
  { id: 'users',          icon: '👥', label: 'Users' },
  { id: 'knowledge_base', icon: '📚', label: 'Knowledge Base' },
  { id: 'symptoms',       icon: '🩺', label: 'Symptoms' },
  { id: 'locations',      icon: '📍', label: 'Locations' },
  { id: 'audit_logs',     icon: '🔍', label: 'Audit Logs' },
] as const;

export default function AdminApp() {
  const { logout } = useApp();
  const [screen, setScreen] = useState<Screen>('dashboard');

  return (
    <div className="min-h-screen bg-[#f7f9f7] flex flex-col">
      <header className="bg-[#14532d] text-white px-6 py-3 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="text-xl">⚙️</div>
          <div>
            <span className="font-display font-700 text-base">PashuSwasthya Admin</span>
            <span className="text-green-300 text-xs ml-2">System Administration</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-green-200 hidden sm:block">Admin Kadam · Gandhinagar</span>
          <span className="text-xs bg-green-700 text-green-100 px-2 py-0.5 rounded-full">● All systems OK</span>
          <button onClick={logout} className="text-green-200 text-xs border border-green-700 px-3 py-1.5 rounded hover:bg-white/10">Log out</button>
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
          <div className="p-4 border-t border-[#d1d9d1] space-y-1 text-xs text-gray-400">
            <p>PashuSwasthya v2.0.1</p>
            <p>Build: SIH-2026-09-12</p>
            <p className="text-green-600 font-medium">● All services healthy</p>
          </div>
        </aside>

        <main className="flex-1 overflow-y-auto">
          <div className="max-w-5xl mx-auto px-6 py-6">
            {screen === 'dashboard'      && <AdminDashboard setScreen={setScreen} />}
            {screen === 'users'          && <UsersManagement />}
            {screen === 'knowledge_base' && <KnowledgeBase />}
            {screen === 'symptoms'       && <SymptomsLibrary />}
            {screen === 'locations'      && <LocationsHierarchy />}
            {screen === 'audit_logs'     && <AuditLogsView />}
          </div>
        </main>
      </div>
    </div>
  );
}

function AdminDashboard({ setScreen }: any) {
  const { workspace } = useApp();
  const summary = workspace.dashboard?.[0] as { totals?: Record<string, number | string> } | undefined;
  const totals = summary?.totals ?? {};
  return (
    <div className="space-y-6">
      <LiveWorkspaceStatus />
      <SectionHeader title="System Dashboard" subtitle="PashuSwasthya · Gujarat State · 12 Sep 2026" />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Users" value={mockUsers.length} sub="all roles" />
        <StatCard label="Active Farmers" value="3,284" sub="registered" accent="green" />
        <StatCard label="Disease Reports" value={totals.disease_reports ?? 0} sub="authorized period" accent="blue" />
        <StatCard label="System Uptime" value="99.8%" sub="last 30 days" accent="green" />
      </div>

      {/* System health */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[
          { service: 'API Gateway', status: 'healthy', latency: '42 ms' },
          { service: 'Database (Primary)', status: 'healthy', latency: '8 ms' },
          { service: 'AI Triage Engine', status: 'healthy', latency: '180 ms' },
          { service: 'SMS Gateway', status: 'healthy', latency: '220 ms' },
          { service: 'File Storage', status: 'healthy', latency: '12 ms' },
          { service: 'Notification Service', status: 'degraded', latency: '890 ms' },
        ].map(s => (
          <Card key={s.service} className="p-4 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-gray-800">{s.service}</p>
              <p className="text-xs text-gray-500 font-mono">{s.latency}</p>
            </div>
            <span className={`text-xs px-2 py-1 rounded-full font-semibold border
              ${s.status === 'healthy' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
              {s.status === 'healthy' ? '● Healthy' : '⚠ Degraded'}
            </span>
          </Card>
        ))}
      </div>

      {/* Recent activity */}
      <Card>
        <CardHeader title="Recent System Activity" action={<Btn variant="ghost" size="sm" onClick={() => setScreen('audit_logs')}>All Logs →</Btn>} />
        <div className="divide-y divide-[#e9ede9]">
          {mockAuditLogs.slice(0, 5).map(l => (
            <div key={l.id} className="px-4 py-3 flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{l.action}</span>
                  <span className="text-xs text-gray-500">{l.entity} · {l.entityId}</span>
                </div>
                <p className="text-sm text-gray-700 mt-0.5">{l.userName} <span className="text-gray-400">({l.userRole})</span></p>
                {l.details && <p className="text-xs text-gray-400 mt-0.5 truncate">{l.details}</p>}
              </div>
              <div className="text-right flex-shrink-0">
                <p className="font-mono text-xs text-gray-400">{new Date(l.timestamp).toLocaleDateString()}</p>
                <p className="font-mono text-xs text-gray-300">{l.ipAddress}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function UsersManagement() {
  const [roleFilter, setRoleFilter] = useState('all');
  const [search, setSearch] = useState('');
  const filtered = mockUsers.filter(u =>
    (roleFilter === 'all' || u.role === roleFilter) &&
    (u.name.toLowerCase().includes(search.toLowerCase()) || u.district.toLowerCase().includes(search.toLowerCase()))
  );

  const roleLabels: Record<string, string> = {
    farmer: 'Farmer', paravet: 'Para-vet', vet: 'Veterinarian',
    lab: 'Lab Tech', government: 'Government', admin: 'Admin',
  };

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <SectionHeader title="User Management" subtitle={`${mockUsers.length} registered users`} />
        <Btn variant="primary">+ Add User</Btn>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {['all','farmer','paravet','vet','lab','government'].map(r => (
          <button key={r} onClick={() => setRoleFilter(r)}
            className={`px-3 py-1.5 rounded text-xs font-medium border transition-colors
              ${roleFilter === r ? 'bg-[#166534] text-white border-[#166534]' : 'bg-white text-gray-600 border-[#d1d9d1] hover:border-green-400'}`}>
            {r === 'all' ? 'All' : roleLabels[r]}
          </button>
        ))}
      </div>

      <Input value={search} onChange={setSearch} placeholder="Search by name or district..." />

      <Card>
        <Table headers={['Name', 'Role', 'District', 'Block', 'Phone', 'Status', 'Last Login', 'Actions']}>
          {filtered.map(u => (
            <TR key={u.id}>
              <TD bold>{u.name}</TD>
              <TD>
                <span className="text-xs px-2 py-0.5 rounded bg-green-50 text-green-700 border border-green-200 font-medium">
                  {roleLabels[u.role]}
                </span>
              </TD>
              <TD>{u.district}</TD>
              <TD>{u.block || '—'}</TD>
              <TD mono>{u.phone}</TD>
              <TD><StatusBadge status={u.status} prefix="user" /></TD>
              <TD mono>{new Date(u.lastLogin).toLocaleDateString()}</TD>
              <TD>
                <div className="flex gap-1">
                  <Btn variant="ghost" size="sm">Edit</Btn>
                  <Btn variant="ghost" size="sm">Suspend</Btn>
                </div>
              </TD>
            </TR>
          ))}
        </Table>
        {filtered.length === 0 && <EmptyState icon="👥" title="No users found" />}
      </Card>
    </div>
  );
}

function KnowledgeBase() {
  const [selected, setSelected] = useState(DISEASES[0]);

  const diseaseDetails: Record<string, { agent: string; species: string; incubation: string; transmission: string; prevention: string }> = {
    'Foot and Mouth Disease (FMD)': {
      agent: 'Aphthovirus (Picornaviridae) — Serotypes O, A, C, SAT1-3, Asia1',
      species: 'Cattle, Buffalo, Sheep, Goat, Pigs, Wild cloven-hoofed animals',
      incubation: '1–14 days (average 2–5 days)',
      transmission: 'Direct contact, aerosol, contaminated feed/water/vehicles, fomites',
      prevention: 'Bi-annual FMD vaccination, quarantine, movement restrictions, surveillance',
    },
    'Lumpy Skin Disease (LSD)': {
      agent: 'Capripoxvirus (Poxviridae)',
      species: 'Primarily cattle and water buffalo',
      incubation: '4–14 days',
      transmission: 'Biting insects (mosquitoes, flies, ticks), direct contact',
      prevention: 'LSD vaccination, vector control, quarantine of affected animals',
    },
  };

  const detail = diseaseDetails[selected];

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <SectionHeader title="Disease Knowledge Base" subtitle={`${DISEASES.length} diseases registered`} />
        <Btn variant="primary">+ Add Disease</Btn>
      </div>

      <div className="grid lg:grid-cols-3 gap-5">
        <Card className="lg:col-span-1">
          <CardHeader title="Diseases" />
          <div className="divide-y divide-[#e9ede9] max-h-[500px] overflow-y-auto">
            {DISEASES.map(d => (
              <button key={d} onClick={() => setSelected(d)}
                className={`w-full text-left px-4 py-3 text-sm hover:bg-green-50 transition-colors
                  ${selected === d ? 'bg-green-50 text-[#166534] font-semibold border-r-2 border-[#166534]' : 'text-gray-700'}`}>
                {d}
              </button>
            ))}
          </div>
        </Card>

        <Card className="lg:col-span-2 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display font-700 text-lg text-gray-900">{selected}</h3>
            <Btn variant="secondary" size="sm">Edit</Btn>
          </div>
          {detail ? (
            <div className="space-y-3">
              {[
                ['Causative Agent', detail.agent],
                ['Susceptible Species', detail.species],
                ['Incubation Period', detail.incubation],
                ['Transmission Routes', detail.transmission],
                ['Prevention & Control', detail.prevention],
              ].map(([k, v]) => (
                <div key={k} className="border-b border-[#e9ede9] pb-3 last:border-0">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{k}</p>
                  <p className="text-sm text-gray-700 mt-1">{v}</p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState icon="📚" title="No details available" description="Click Edit to add information for this disease." />
          )}
        </Card>
      </div>
    </div>
  );
}

function SymptomsLibrary() {
  const [search, setSearch] = useState('');
  const filtered = SYMPTOMS.filter(s => s.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <SectionHeader title="Symptoms Library" subtitle={`${SYMPTOMS.length} symptoms registered`} />
        <Btn variant="primary">+ Add Symptom</Btn>
      </div>
      <Input value={search} onChange={setSearch} placeholder="Search symptoms..." />
      <Card>
        <Table headers={['#', 'Symptom Name', 'Category', 'Disease Associations', 'Actions']}>
          {filtered.map((s, i) => (
            <TR key={s}>
              <TD mono>{i + 1}</TD>
              <TD bold>{s}</TD>
              <TD><span className="text-xs text-gray-500">General</span></TD>
              <TD><span className="text-xs text-gray-400">FMD, LSD, HS, BQ...</span></TD>
              <TD><Btn variant="ghost" size="sm">Edit</Btn></TD>
            </TR>
          ))}
        </Table>
        {filtered.length === 0 && <EmptyState icon="🩺" title="No symptoms match search" />}
      </Card>
    </div>
  );
}

function LocationsHierarchy() {
  const [tab, setTab] = useState('districts');
  const blocks: Record<string, string[]> = {
    'Ahmedabad': ['Daskroi', 'Dholka', 'Viramgam', 'Sanand', 'Bavla', 'Detroj-Rampura', 'Mandal'],
    'Anand': ['Anand', 'Borsad', 'Petlad', 'Khambhat', 'Umreth', 'Tarapur'],
    'Kutch': ['Bhuj', 'Mandvi', 'Mundra', 'Anjar', 'Rapar', 'Nakhatrana'],
  };

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <SectionHeader title="Location Hierarchy" subtitle="State → District → Block → Village" />
        <Btn variant="primary">+ Add Location</Btn>
      </div>
      <Tabs tabs={[{id:'districts',label:'Districts'},{id:'blocks',label:'Blocks'}]} active={tab} onChange={setTab} />
      {tab === 'districts' && (
        <Card>
          <Table headers={['District', 'Blocks', 'Villages', 'Para-vets', 'Vets', 'Actions']}>
            {[
              { name: 'Ahmedabad', blocks: 7, villages: 384, pvets: 42, vets: 8 },
              { name: 'Anand', blocks: 6, villages: 243, pvets: 28, vets: 5 },
              { name: 'Kutch', blocks: 6, villages: 618, pvets: 35, vets: 4 },
              { name: 'Banaskantha', blocks: 9, villages: 765, pvets: 44, vets: 6 },
              { name: 'Mehsana', blocks: 8, villages: 455, pvets: 38, vets: 7 },
            ].map(d => (
              <TR key={d.name}>
                <TD bold>{d.name}</TD>
                <TD mono>{d.blocks}</TD>
                <TD mono>{d.villages}</TD>
                <TD mono>{d.pvets}</TD>
                <TD mono>{d.vets}</TD>
                <TD><Btn variant="ghost" size="sm">View</Btn></TD>
              </TR>
            ))}
          </Table>
        </Card>
      )}
      {tab === 'blocks' && (
        <Card>
          <Table headers={['Block', 'District', 'Villages', 'Para-vet', 'Actions']}>
            {Object.entries(blocks).flatMap(([dist, bls]) =>
              bls.map((b, idx) => (
                <TR key={`${dist}-${b}`}>
                  <TD bold>{b}</TD>
                  <TD>{dist}</TD>
                  <TD mono>{30 + (idx * 7) % 40}</TD>
                  <TD>{b === 'Daskroi' ? 'Mohan Desai' : '—'}</TD>
                  <TD><Btn variant="ghost" size="sm">Edit</Btn></TD>
                </TR>
              ))
            )}
          </Table>
        </Card>
      )}
    </div>
  );
}

function AuditLogsView() {
  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('all');
  const filtered = mockAuditLogs.filter(l =>
    (actionFilter === 'all' || l.action.includes(actionFilter)) &&
    (l.userName.toLowerCase().includes(search.toLowerCase()) || l.entityId.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-5">
      <SectionHeader title="Audit Logs" subtitle="All system activity — immutable record" />
      <div className="flex flex-col sm:flex-row gap-3">
        <Input value={search} onChange={setSearch} placeholder="Search by user, entity ID..." />
        <Select value={actionFilter} onChange={setActionFilter}>
          <option value="all">All actions</option>
          <option value="REPORT">Report actions</option>
          <option value="SAMPLE">Sample actions</option>
          <option value="USER">User actions</option>
          <option value="RESULT">Result actions</option>
        </Select>
      </div>
      <Card>
        <Table headers={['Timestamp', 'User', 'Role', 'Action', 'Entity', 'Entity ID', 'IP', 'Details']}>
          {filtered.map(l => (
            <TR key={l.id}>
              <TD mono>{new Date(l.timestamp).toLocaleString()}</TD>
              <TD bold>{l.userName}</TD>
              <TD>
                <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 font-medium">{l.userRole}</span>
              </TD>
              <TD>
                <span className="font-mono text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">{l.action}</span>
              </TD>
              <TD>{l.entity}</TD>
              <TD mono>{l.entityId}</TD>
              <TD mono>{l.ipAddress}</TD>
              <TD><span className="text-xs text-gray-500 max-w-[200px] block truncate">{l.details || '—'}</span></TD>
            </TR>
          ))}
        </Table>
        {filtered.length === 0 && <EmptyState icon="🔍" title="No logs match your search" />}
      </Card>
    </div>
  );
}
