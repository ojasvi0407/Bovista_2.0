import { useState } from 'react';
import type { Role, Lang } from '../types';
import { TRANSLATIONS } from '../mockData';
import { Btn } from '../components/ui';

const ROLES: { id: Role; emoji: string; desc: string; desc_hi: string; desc_gu: string; color: string }[] = [
  { id: 'farmer',     emoji: '🌾', desc: 'Report sick animals, track health, get alerts', desc_hi: 'बीमार पशुओं की रिपोर्ट करें, स्वास्थ्य ट्रैक करें', desc_gu: 'બીમાર પ્રાણીઓ રિપોર્ટ, આરોગ્ય ટ્રૅક', color: 'hover:border-green-600' },
  { id: 'paravet',    emoji: '🩺', desc: 'Field visits, sample collection, vaccination drives', desc_hi: 'फील्ड विजिट, नमूना संग्रह, टीकाकरण', desc_gu: 'ફીલ્ડ વિઝિટ, નમૂના સંગ્રહ, રસીકરણ', color: 'hover:border-teal-600' },
  { id: 'vet',        emoji: '🔬', desc: 'Case review, AI-assisted triage, disease management', desc_hi: 'केस समीक्षा, AI ट्राइएज, रोग प्रबंधन', desc_gu: 'કેસ સ​ub​mit, AI ટ્રિઆઝ, રોગ વ્યવ​st​hap​na', color: 'hover:border-blue-600' },
  { id: 'lab',        emoji: '🧪', desc: 'Sample management, test results entry, reporting', desc_hi: 'नमूना प्रबंधन, परीक्षण परिणाम, रिपोर्टिंग', desc_gu: 'નમૂના વ્ય​va​sth​ap​an, ​te​st p​ari​na​m', color: 'hover:border-purple-600' },
  { id: 'government', emoji: '🏛️', desc: 'Disease surveillance, outbreak command, analytics', desc_hi: 'रोग निगरानी, प्रकोप कमांड, विश्लेषण', desc_gu: 'રોગ ​ni​gra​ni, ​pr​ak​op ​ko​man​d', color: 'hover:border-amber-600' },
  { id: 'admin',      emoji: '⚙️', desc: 'User management, system configuration, audit', desc_hi: 'उपयोगकर्ता प्रबंधन, सिस्टम कॉन्फ़िग', desc_gu: 'વ​pa​ra​sh​kar​ta ​vy​av​as​th​ap​an', color: 'hover:border-gray-600' },
];

const descKey: Record<Lang, 'desc' | 'desc_hi' | 'desc_gu'> = { en: 'desc', hi: 'desc_hi', gu: 'desc_gu' };

export default function RoleSelector({ onSelect }: { onSelect: (r: Role) => void }) {
  const [selected, setSelected] = useState<Role | null>(null);
  const [lang, setLang] = useState<Lang>('en');
  const t = (k: string) => TRANSLATIONS[lang]?.[k] ?? TRANSLATIONS['en']?.[k] ?? k;

  return (
    <div className="min-h-screen bg-[#f7f9f7] flex flex-col">
      {/* Header */}
      <header className="bg-[#166534] text-white px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center text-xl">🐄</div>
            <div>
              <h1 className="font-display font-800 text-xl leading-tight">{t('appName')}</h1>
              <p className="text-green-200 text-xs">{t('appSubtitle')}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 bg-white/10 rounded-lg p-1" role="group" aria-label="Language selector">
            {(['en', 'hi'] as Lang[]).map(l => (
              <button key={l} onClick={() => setLang(l)} aria-pressed={lang === l}
                className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${lang === l ? 'bg-white text-[#166534]' : 'text-green-100 hover:bg-white/20'}`}>
                {l === 'en' ? 'EN' : 'हिं'}
              </button>
            ))}
          </div>
        </div>
      </header>


      <main className="flex-1 flex flex-col items-center justify-center px-4 py-10">
        <div className="max-w-3xl w-full">
          <div className="text-center mb-8">
            <h2 className="font-display font-700 text-gray-900 text-2xl">{t('selectRole')}</h2>
            <p className="text-gray-500 text-sm mt-1">
              {lang === 'hi' ? 'अपनी भूमिका चुनकर उचित डैशबोर्ड तक पहुँचें।' :
               'Select your role to access the appropriate dashboard and tools.'}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {ROLES.map(r => (
              <button key={r.id} onClick={() => setSelected(r.id)}
                aria-pressed={selected === r.id}
                className={`text-left p-5 rounded-lg border-2 bg-white transition-all focus:outline-none focus:ring-2 focus:ring-[#166534] focus:ring-offset-2
                  ${selected === r.id ? 'border-[#166534] shadow-md ring-1 ring-[#166534]/20' : `border-[#d1d9d1] ${r.color}`}`}>
                <div className="text-3xl mb-2">{r.emoji}</div>
                <div className="font-display font-600 text-gray-900 text-base">{t(r.id)}</div>
                <div className="text-xs text-gray-500 mt-1 leading-relaxed">{r[descKey[lang]]}</div>
              </button>
            ))}
          </div>

          <div className="mt-6 flex justify-center">
            <Btn variant="primary" size="lg" disabled={!selected}
              onClick={() => selected && onSelect(selected)}>
              {t('continueAs')} {selected ? `— ${t(selected)}` : ''}
            </Btn>
          </div>

          <p className="text-center text-xs text-gray-400 mt-6">
            PashuMitra v2.0 &nbsp;·&nbsp; Smart India Hackathon 2026 &nbsp;·&nbsp; Problem ID: SIH1571
          </p>
        </div>
      </main>
    </div>
  );
}
