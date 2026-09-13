import { FormEvent, useState } from 'react';

type Props = {
  busy: boolean;
  onFarmerOtp: (mobileNumber: string, code?: string) => Promise<void>;
  onStaffLogin: (identifier: string, password: string, code?: string) => Promise<void>;
};

export default function LoginGate({ busy, onFarmerOtp, onStaffLogin }: Props) {
  const [mode, setMode] = useState<'farmer' | 'staff'>('farmer');
  const [otpSent, setOtpSent] = useState(false);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mobileNumber, setMobileNumber] = useState('');
  const [staffIdentifier, setStaffIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      if (mode === 'farmer') {
        await onFarmerOtp(mobileNumber, otpSent ? code : undefined);
        setOtpSent(true);
      } else {
        await onStaffLogin(staffIdentifier, password, mfaRequired ? code : undefined);
        setMfaRequired(true);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Sign in could not be completed.');
    }
  }

  function chooseMode(next: 'farmer' | 'staff') {
    setMode(next);
    setError(null);
    setCode('');
    setOtpSent(false);
    setMfaRequired(false);
  }

  const codeRequired = mode === 'farmer' ? otpSent : mfaRequired;
  return (
    <main className="min-h-screen bg-[#f7f9f7] grid place-items-center px-4 py-8">
      <section className="w-full max-w-md rounded-2xl border border-[#d1d9d1] bg-white p-6 shadow-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 grid size-12 place-items-center rounded-xl bg-[#166534] text-2xl">🐄</div>
          <h1 className="font-display text-2xl font-bold text-gray-900">PashuSwasthya</h1>
          <p className="mt-1 text-sm text-gray-500">Government livestock health system</p>
        </div>

        <div className="mb-6 grid grid-cols-2 rounded-lg bg-[#f1f5f1] p-1" role="tablist" aria-label="Sign-in type">
          {(['farmer', 'staff'] as const).map((choice) => (
            <button
              aria-selected={mode === choice}
              className={`rounded-md px-3 py-2 text-sm font-semibold ${mode === choice ? 'bg-white text-[#166534] shadow-sm' : 'text-gray-500'}`}
              key={choice}
              onClick={() => chooseMode(choice)}
              role="tab"
              type="button"
            >
              {choice === 'farmer' ? 'Farmer OTP' : 'Staff sign in'}
            </button>
          ))}
        </div>

        <form className="space-y-4" onSubmit={submit}>
          {mode === 'farmer' ? (
            <label className="block text-sm font-medium text-gray-700">
              Mobile number
              <input
                autoComplete="tel"
                className="mt-1 w-full rounded-lg border border-[#c8d0c8] px-3 py-2.5 outline-none focus:border-[#166534] focus:ring-2 focus:ring-green-100"
                disabled={busy || otpSent}
                onChange={(event) => setMobileNumber(event.target.value)}
                placeholder="+91 98765 43210"
                required
                type="tel"
                value={mobileNumber}
              />
            </label>
          ) : (
            <>
              <label className="block text-sm font-medium text-gray-700">
                Staff ID or email
                <input className="mt-1 w-full rounded-lg border border-[#c8d0c8] px-3 py-2.5 outline-none focus:border-[#166534] focus:ring-2 focus:ring-green-100" disabled={busy || mfaRequired} onChange={(event) => setStaffIdentifier(event.target.value)} required value={staffIdentifier} />
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Password
                <input autoComplete="current-password" className="mt-1 w-full rounded-lg border border-[#c8d0c8] px-3 py-2.5 outline-none focus:border-[#166534] focus:ring-2 focus:ring-green-100" disabled={busy || mfaRequired} minLength={8} onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
              </label>
            </>
          )}

          {codeRequired && (
            <label className="block text-sm font-medium text-gray-700">
              {mode === 'farmer' ? 'One-time password' : 'Authenticator code'}
              <input autoComplete="one-time-code" className="mt-1 w-full rounded-lg border border-[#c8d0c8] px-3 py-2.5 tracking-[0.3em] outline-none focus:border-[#166534] focus:ring-2 focus:ring-green-100" disabled={busy} inputMode="numeric" maxLength={12} onChange={(event) => setCode(event.target.value)} required value={code} />
            </label>
          )}

          {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</p>}
          <button className="w-full rounded-lg bg-[#166534] px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-green-300" disabled={busy} type="submit">
            {busy ? 'Please wait…' : codeRequired ? 'Verify and continue' : mode === 'farmer' ? 'Send OTP' : 'Continue'}
          </button>
        </form>
        <p className="mt-5 text-center text-xs text-gray-500">Access is limited to your assigned role and geographic scope.</p>
      </section>
    </main>
  );
}
