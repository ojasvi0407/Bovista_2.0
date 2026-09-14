import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { AuthApi, type TokenPair } from './api/auth';
import { api, ApiError } from './api/client';
import { frontendRoleFor } from './auth-state';
import { TRANSLATIONS } from './mockData';
import LoginGate from './screens/LoginGate';
import AdminApp from './screens/admin/AdminApp';
import FarmerApp from './screens/farmer/FarmerApp';
import GovApp from './screens/government/GovApp';
import LabApp from './screens/lab/LabApp';
import ParavetApp from './screens/paravet/ParavetApp';
import VetApp from './screens/vet/VetApp';
import type { Lang, Role } from './types';

type Principal = { user_id: string; display_name: string; roles: string[]; location_path: string | null };
type Workspace = Record<string, unknown[]>;

export interface AppCtx {
  role: Role | null;
  user: Principal | null;
  lang: Lang;
  isOnline: boolean;
  workspace: Workspace;
  workspaceLoading: boolean;
  workspaceError: string | null;
  t: (key: string) => string;
  setLang: (language: Lang) => void;
  reloadWorkspace: () => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AppCtx>({
  role: null, user: null, lang: 'en', isOnline: true, workspace: {}, workspaceLoading: false, workspaceError: null,
  t: (key) => key, setLang: () => {}, reloadWorkspace: async () => {}, logout: () => {},
});

export const useApp = () => useContext(Ctx);

const auth = new AuthApi(api);
const tokenKeys = { access: 'pashumitra.access_token', refresh: 'pashumitra.refresh_token', device: 'pashumitra.device_id' };

function deviceId(): string {
  const saved = sessionStorage.getItem(tokenKeys.device);
  if (saved) return saved;
  const created = crypto.randomUUID();
  sessionStorage.setItem(tokenKeys.device, created);
  return created;
}

function saveTokens(pair: TokenPair) {
  sessionStorage.setItem(tokenKeys.access, pair.access_token);
  sessionStorage.setItem(tokenKeys.refresh, pair.refresh_token);
}

function clearTokens() {
  sessionStorage.removeItem(tokenKeys.access);
  sessionStorage.removeItem(tokenKeys.refresh);
}

async function workspaceFor(role: Role): Promise<Workspace> {
  const collect = async (key: string, path: string) => [key, await api.get<unknown[]>(path)] as const;
  const paths: Record<Role, Array<[string, string]>> = {
    farmer: [['animals', '/animals'], ['reports', '/disease-reports'], ['vaccinations', '/vaccinations/due'], ['alerts', '/alerts']],
    paravet: [['reports', '/disease-reports'], ['cases', '/cases'], ['outbreaks', '/outbreaks'], ['alerts', '/alerts']],
    vet: [['reports', '/disease-reports'], ['cases', '/cases'], ['outbreaks', '/outbreaks'], ['alerts', '/alerts']],
    lab: [['samples', '/lab/samples'], ['results', '/lab/results']],
    government: [['outbreaks', '/outbreaks'], ['alerts', '/alerts']],
    admin: [['outbreaks', '/outbreaks'], ['alerts', '/alerts']],
  };
  const entries = await Promise.all(paths[role].map(([key, path]) => collect(key, path)));
  if (role === 'government' || role === 'admin') entries.push(['dashboard', [await api.get('/dashboard/summary')]]);
  return Object.fromEntries(entries);
}

export default function App() {
  const [user, setUser] = useState<Principal | null>(null);
  const [lang, setLang] = useState<Lang>('en');
  const [workspace, setWorkspace] = useState<Workspace>({});
  const [workspaceLoading, setWorkspaceLoading] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [booting, setBooting] = useState(true);
  const [busy, setBusy] = useState(false);
  const [staffChallenge, setStaffChallenge] = useState<string | null>(null);

  const role = user ? frontendRoleFor(user.roles) : null;
  const t = (key: string) => TRANSLATIONS[lang]?.[key] ?? TRANSLATIONS.en?.[key] ?? key;

  const loadWorkspace = useCallback(async () => {
    if (!role) return;
    setWorkspaceLoading(true);
    setWorkspaceError(null);
    try { setWorkspace(await workspaceFor(role)); }
    catch (caught) { setWorkspaceError(caught instanceof Error ? caught.message : 'Live data could not be loaded.'); }
    finally { setWorkspaceLoading(false); }
  }, [role]);

  const loadProfile = useCallback(async () => {
    const principal = await api.get<Principal>('/auth/me');
    if (!frontendRoleFor(principal.roles)) throw new Error('This account has no authorized workspace.');
    setUser(principal);
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        if (!sessionStorage.getItem(tokenKeys.access)) return;
        try { await loadProfile(); }
        catch (caught) {
          if (!(caught instanceof ApiError) || caught.status !== 401) throw caught;
          const refreshToken = sessionStorage.getItem(tokenKeys.refresh);
          if (!refreshToken) throw caught;
          saveTokens(await auth.refresh(refreshToken, deviceId()));
          await loadProfile();
        }
      } catch { clearTokens(); }
      finally { setBooting(false); }
    })();
  }, [loadProfile]);

  useEffect(() => { if (user) void loadWorkspace(); }, [loadWorkspace, user]);

  async function farmerOtp(mobileNumber: string, code?: string) {
    setBusy(true);
    try {
      if (!code) {
        await auth.requestFarmerOtp(mobileNumber, deviceId());
        return;
      }
      saveTokens(await auth.verifyFarmerOtp(mobileNumber, code, deviceId()));
      await loadProfile();
    } finally { setBusy(false); }
  }

  async function staffLogin(identifier: string, password: string, code?: string) {
    setBusy(true);
    try {
      if (!code) { setStaffChallenge(await auth.beginStaffLogin(identifier, password)); return; }
      if (!staffChallenge) throw new Error('Start the staff sign-in again.');
      saveTokens(await auth.verifyStaffMfa(staffChallenge, code, deviceId()));
      setStaffChallenge(null);
      await loadProfile();
    } finally { setBusy(false); }
  }

  const logout = useCallback(() => {
    const refreshToken = sessionStorage.getItem(tokenKeys.refresh);
    if (refreshToken) void api.post('/auth/logout', { refresh_token: refreshToken }).catch(() => undefined);
    clearTokens();
    setUser(null);
    setWorkspace({});
  }, []);

  const ctx = useMemo<AppCtx>(() => ({
    role, user, lang, isOnline: navigator.onLine, workspace, workspaceLoading, workspaceError, t, setLang, reloadWorkspace: loadWorkspace, logout,
  }), [lang, loadWorkspace, logout, role, t, user, workspace, workspaceError, workspaceLoading]);

  if (booting) return <main className="min-h-screen grid place-items-center bg-[#f7f9f7] text-sm text-gray-600">Loading secure session…</main>;
  if (!user) return <LoginGate busy={busy} onFarmerOtp={farmerOtp} onStaffLogin={staffLogin} />;
  if (!role) return <main className="min-h-screen grid place-items-center bg-[#f7f9f7] text-sm text-red-700">No authorized workspace is assigned to this account.</main>;

  const screens: Record<Role, React.ReactNode> = {
    farmer: <FarmerApp />, paravet: <ParavetApp />, vet: <VetApp />, lab: <LabApp />, government: <GovApp />, admin: <AdminApp />,
  };
  return <Ctx.Provider value={ctx}>{screens[role]}</Ctx.Provider>;
}
