import React from 'react';
import type { RiskLevel } from '../types';

// ── Risk Badge ──────────────────────────────────────────────────────────────
const RISK_CONFIG = {
  low:      { label: 'Low Risk',      icon: '↓', textClass: 'text-green-700',  bgClass: 'bg-green-50',  borderClass: 'border-green-200' },
  medium:   { label: 'Moderate Risk', icon: '~', textClass: 'text-amber-700',  bgClass: 'bg-amber-50',  borderClass: 'border-amber-200' },
  high:     { label: 'High Risk',     icon: '!', textClass: 'text-red-700',    bgClass: 'bg-red-50',    borderClass: 'border-red-200' },
  critical: { label: 'Critical',      icon: '!!', textClass: 'text-red-900',   bgClass: 'bg-orange-50', borderClass: 'border-red-300' },
};

export function RiskBadge({ level, score, compact }: { level: RiskLevel; score?: number; compact?: boolean }) {
  const c = RISK_CONFIG[level];
  if (compact) {
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold border ${c.textClass} ${c.bgClass} ${c.borderClass}`} role="status" aria-label={c.label}>
        <span aria-hidden="true">{c.icon}</span> {c.label}
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded text-sm font-semibold border ${c.textClass} ${c.bgClass} ${c.borderClass}`} role="status">
      <span className="font-mono text-xs" aria-hidden="true">{c.icon}</span>
      <span>{c.label}</span>
      {score !== undefined && <span className="font-mono opacity-70">({score})</span>}
    </span>
  );
}

// ── Status Badge ─────────────────────────────────────────────────────────────
const STATUS_MAP: Record<string, { label: string; className: string }> = {
  submitted:        { label: 'Submitted',        className: 'bg-blue-50 text-blue-700 border-blue-200' },
  under_review:     { label: 'Under Review',     className: 'bg-amber-50 text-amber-700 border-amber-200' },
  assigned:         { label: 'Assigned',         className: 'bg-purple-50 text-purple-700 border-purple-200' },
  sample_collected: { label: 'Sample Collected', className: 'bg-teal-50 text-teal-700 border-teal-200' },
  lab_testing:      { label: 'Lab Testing',      className: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  confirmed:        { label: 'Confirmed',        className: 'bg-red-50 text-red-700 border-red-200' },
  resolved:         { label: 'Resolved',         className: 'bg-green-50 text-green-700 border-green-200' },
  rejected:         { label: 'Rejected',         className: 'bg-gray-100 text-gray-600 border-gray-200' },
  collected:        { label: 'Collected',        className: 'bg-blue-50 text-blue-700 border-blue-200' },
  in_transit:       { label: 'In Transit',       className: 'bg-amber-50 text-amber-700 border-amber-200' },
  received:         { label: 'Received',         className: 'bg-purple-50 text-purple-700 border-purple-200' },
  testing:          { label: 'Testing',          className: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  completed:        { label: 'Completed',        className: 'bg-green-50 text-green-700 border-green-200' },
  active:           { label: 'Active',           className: 'bg-red-50 text-red-700 border-red-200' },
  contained:        { label: 'Contained',        className: 'bg-amber-50 text-amber-700 border-amber-200' },
  new:              { label: 'New',              className: 'bg-blue-50 text-blue-700 border-blue-200' },
  healthy:          { label: 'Healthy',          className: 'bg-green-50 text-green-700 border-green-200' },
  sick:             { label: 'Sick',             className: 'bg-red-50 text-red-700 border-red-200' },
  under_treatment:  { label: 'Under Treatment',  className: 'bg-amber-50 text-amber-700 border-amber-200' },
  deceased:         { label: 'Deceased',         className: 'bg-gray-100 text-gray-500 border-gray-200' },
  due:              { label: 'Due',              className: 'bg-amber-50 text-amber-700 border-amber-200' },
  overdue:          { label: 'Overdue',          className: 'bg-red-50 text-red-700 border-red-200' },
  scheduled:        { label: 'Scheduled',        className: 'bg-blue-50 text-blue-700 border-blue-200' },
  'user-active':    { label: 'Active',           className: 'bg-green-50 text-green-700 border-green-200' },
  'user-inactive':  { label: 'Inactive',         className: 'bg-gray-100 text-gray-500 border-gray-200' },
  'user-suspended': { label: 'Suspended',        className: 'bg-red-50 text-red-700 border-red-200' },
};

export function StatusBadge({ status, prefix }: { status: string; prefix?: string }) {
  const key = prefix ? `${prefix}-${status}` : status;
  const cfg = STATUS_MAP[key] || STATUS_MAP[status] || { label: status, className: 'bg-gray-100 text-gray-600 border-gray-200' };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cfg.className}`}>
      {cfg.label}
    </span>
  );
}

// ── Card ─────────────────────────────────────────────────────────────────────
export function Card({ children, className = '', onClick }: { children: React.ReactNode; className?: string; onClick?: () => void }) {
  return <div onClick={onClick} className={`bg-white border border-[#d1d9d1] rounded-lg ${className}`}>{children}</div>;
}

export function CardHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between px-5 py-4 border-b border-[#d1d9d1]">
      <div>
        <h3 className="font-display font-600 text-gray-900 text-base leading-tight">{title}</h3>
        {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

// ── Stat Card ────────────────────────────────────────────────────────────────
export function StatCard({ label, value, sub, icon, accent }: { label: string; value: string | number; sub?: string; icon?: React.ReactNode; accent?: 'green' | 'red' | 'amber' | 'blue' | 'gray' }) {
  const accents = {
    green: 'border-l-4 border-l-green-600',
    red:   'border-l-4 border-l-red-600',
    amber: 'border-l-4 border-l-amber-500',
    blue:  'border-l-4 border-l-blue-600',
    gray:  '',
  };
  return (
    <Card className={`p-4 ${accent ? accents[accent] : ''}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
          <p className="font-display text-2xl font-700 text-gray-900 mt-1">{value}</p>
          {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
        </div>
        {icon && <div className="text-gray-400 mt-1">{icon}</div>}
      </div>
    </Card>
  );
}

// ── Button ────────────────────────────────────────────────────────────────────
type BtnVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
export function Btn({ children, onClick, variant = 'secondary', disabled, type = 'button', className = '', fullWidth, size = 'md' }: {
  children: React.ReactNode; onClick?: () => void; variant?: BtnVariant;
  disabled?: boolean; type?: 'button' | 'submit'; className?: string;
  fullWidth?: boolean; size?: 'sm' | 'md' | 'lg';
}) {
  const base = 'inline-flex items-center justify-center gap-2 font-medium rounded transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed';
  const sizes = { sm: 'px-3 py-1.5 text-sm', md: 'px-4 py-2 text-sm', lg: 'px-6 py-3 text-base' };
  const variants: Record<BtnVariant, string> = {
    primary:   'bg-[#166534] text-white hover:bg-[#14532d] focus:ring-green-600',
    secondary: 'bg-white text-gray-700 border border-[#d1d9d1] hover:bg-gray-50 focus:ring-gray-400',
    danger:    'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    ghost:     'text-gray-600 hover:bg-gray-100 focus:ring-gray-400',
  };
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={`${base} ${sizes[size]} ${variants[variant]} ${fullWidth ? 'w-full' : ''} ${className}`}>
      {children}
    </button>
  );
}

// ── Table ─────────────────────────────────────────────────────────────────────
export function Table({ headers, children, caption }: { headers: string[]; children: React.ReactNode; caption?: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse" role="table">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr className="border-b border-[#d1d9d1] bg-gray-50">
            {headers.map(h => (
              <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#e9ede9]">{children}</tbody>
      </table>
    </div>
  );
}

export function TR({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) {
  return (
    <tr onClick={onClick} className={`text-gray-700 ${onClick ? 'cursor-pointer hover:bg-green-50' : 'hover:bg-gray-50/50'}`}>
      {children}
    </tr>
  );
}

export function TD({ children, mono, bold }: { children: React.ReactNode; mono?: boolean; bold?: boolean }) {
  return <td className={`px-4 py-3 ${mono ? 'font-mono text-xs' : ''} ${bold ? 'font-semibold' : ''}`}>{children}</td>;
}

// ── Alert Banner ─────────────────────────────────────────────────────────────
export function AlertBanner({ type, title, message, onDismiss }: {
  type: 'info' | 'warning' | 'error' | 'success'; title: string; message?: string; onDismiss?: () => void;
}) {
  const cfg = {
    info:    { bg: 'bg-blue-50 border-blue-200',   text: 'text-blue-800',  icon: 'ℹ' },
    warning: { bg: 'bg-amber-50 border-amber-200', text: 'text-amber-800', icon: '⚠' },
    error:   { bg: 'bg-red-50 border-red-200',     text: 'text-red-800',   icon: '✕' },
    success: { bg: 'bg-green-50 border-green-200', text: 'text-green-800', icon: '✓' },
  }[type];
  return (
    <div role="alert" className={`flex items-start gap-3 px-4 py-3 rounded-lg border ${cfg.bg} ${cfg.text}`}>
      <span className="font-bold text-base mt-0.5" aria-hidden="true">{cfg.icon}</span>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-sm">{title}</p>
        {message && <p className="text-sm mt-0.5 opacity-90">{message}</p>}
      </div>
      {onDismiss && <button onClick={onDismiss} className="opacity-60 hover:opacity-100 text-lg leading-none" aria-label="Dismiss">×</button>}
    </div>
  );
}

// ── Empty State ────────────────────────────────────────────────────────────────
export function EmptyState({ icon, title, description, action }: { icon: string; title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="text-5xl mb-4" aria-hidden="true">{icon}</div>
      <h3 className="font-display font-600 text-gray-700 text-lg">{title}</h3>
      {description && <p className="text-sm text-gray-500 mt-1 max-w-xs">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

// ── Offline Banner ─────────────────────────────────────────────────────────────
export function OfflineBanner({ pendingCount }: { pendingCount?: number }) {
  return (
    <div role="status" className="offline-banner px-4 py-2 flex items-center gap-2 text-amber-900 text-sm font-medium">
      <span aria-hidden="true">⚡</span>
      <span>Offline mode — {pendingCount ? `${pendingCount} item(s) queued for sync` : 'data saved locally'}</span>
    </div>
  );
}

// ── Loading State ──────────────────────────────────────────────────────────────
export function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3" role="status" aria-live="polite">
      <div className="w-8 h-8 border-3 border-[#d1d9d1] border-t-[#166534] rounded-full animate-spin" aria-hidden="true" />
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  );
}

// ── Section Header ─────────────────────────────────────────────────────────────
export function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-end justify-between mb-4">
      <div>
        <h2 className="font-display font-700 text-gray-900 text-xl">{title}</h2>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

// ── Form helpers ──────────────────────────────────────────────────────────────
export function FormField({ label, required, hint, error, children }: {
  label: string; required?: boolean; hint?: string; error?: string; children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-700">
        {label}{required && <span className="text-red-500 ml-1" aria-label="required">*</span>}
      </label>
      {children}
      {hint && !error && <p className="text-xs text-gray-500">{hint}</p>}
      {error && <p className="text-xs text-red-600" role="alert">{error}</p>}
    </div>
  );
}

export function Input({ id, value, onChange, placeholder, type = 'text', disabled }: {
  id?: string; value: string; onChange: (v: string) => void;
  placeholder?: string; type?: string; disabled?: boolean;
}) {
  return (
    <input id={id} type={type} value={value} onChange={e => onChange(e.target.value)}
      placeholder={placeholder} disabled={disabled}
      className="w-full border border-[#d1d9d1] rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#166534] focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
    />
  );
}

export function Select({ value, onChange, children, disabled }: {
  value: string; onChange: (v: string) => void; children: React.ReactNode; disabled?: boolean;
}) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)} disabled={disabled}
      className="w-full border border-[#d1d9d1] rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#166534] focus:border-transparent disabled:bg-gray-50">
      {children}
    </select>
  );
}

export function Textarea({ value, onChange, placeholder, rows = 3 }: {
  value: string; onChange: (v: string) => void; placeholder?: string; rows?: number;
}) {
  return (
    <textarea value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} rows={rows}
      className="w-full border border-[#d1d9d1] rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#166534] focus:border-transparent resize-none"
    />
  );
}

// ── Timeline ──────────────────────────────────────────────────────────────────
export function Timeline({ items }: { items: { date: string; title: string; desc?: string; done?: boolean }[] }) {
  return (
    <ol className="relative border-l border-[#d1d9d1] ml-3">
      {items.map((item, i) => (
        <li key={i} className="mb-5 ml-5">
          <span className={`absolute -left-2.5 flex items-center justify-center w-5 h-5 rounded-full border-2 ${item.done ? 'bg-[#166534] border-[#166534]' : 'bg-white border-[#d1d9d1]'}`}>
            {item.done && <span className="text-white text-xs">✓</span>}
          </span>
          <p className="text-xs text-gray-500 font-mono mb-0.5">{item.date}</p>
          <p className="text-sm font-semibold text-gray-800">{item.title}</p>
          {item.desc && <p className="text-xs text-gray-500 mt-0.5">{item.desc}</p>}
        </li>
      ))}
    </ol>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
export function Tabs({ tabs, active, onChange }: { tabs: { id: string; label: string }[]; active: string; onChange: (id: string) => void }) {
  return (
    <div role="tablist" className="flex border-b border-[#d1d9d1] overflow-x-auto">
      {tabs.map(t => (
        <button key={t.id} role="tab" aria-selected={active === t.id} onClick={() => onChange(t.id)}
          className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[#166534]
            ${active === t.id ? 'border-[#166534] text-[#166534]' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

// ── Progress Steps ─────────────────────────────────────────────────────────────
export function ProgressSteps({ steps, current }: { steps: string[]; current: number }) {
  return (
    <div className="flex items-center overflow-x-auto pb-1" role="list" aria-label="Progress steps">
      {steps.map((step, i) => (
        <React.Fragment key={i}>
          <div role="listitem" className="flex flex-col items-center min-w-[56px]">
            <div className={`wizard-step-dot w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2
              ${i < current ? 'bg-[#166534] border-[#166534] text-white' :
                i === current ? 'bg-white border-[#166534] text-[#166534]' :
                'bg-white border-[#d1d9d1] text-gray-400'}`}
              aria-current={i === current ? 'step' : undefined}>
              {i < current ? '✓' : i + 1}
            </div>
            <span className={`text-[10px] mt-1 text-center leading-tight ${i === current ? 'text-[#166534] font-semibold' : 'text-gray-400'}`}>{step}</span>
          </div>
          {i < steps.length - 1 && (
            <div className={`flex-1 h-0.5 mt-[-14px] min-w-[12px] ${i < current ? 'bg-[#166534]' : 'bg-[#d1d9d1]'}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}
