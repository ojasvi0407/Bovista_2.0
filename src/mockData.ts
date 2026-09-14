import type { Animal, DiseaseReport, Sample, OutbreakCluster, VaccinationRecord, User, AuditLog } from './types';

export const DISTRICTS = [
  'Ahmedabad', 'Anand', 'Kheda', 'Gandhinagar', 'Mehsana',
  'Banaskantha', 'Patan', 'Sabarkantha', 'Kutch', 'Rajkot',
  'Surendranagar', 'Bhavnagar', 'Amreli', 'Junagadh', 'Surat', 'Vadodara',
];

export const DISEASES = [
  'Foot and Mouth Disease (FMD)', 'Lumpy Skin Disease (LSD)', 'Black Quarter (BQ)',
  'Hemorrhagic Septicemia (HS)', 'PPR (Peste des Petits Ruminants)', 'Brucellosis',
  'Theileriosis', 'Bovine Mastitis', 'Trypanosomiasis',
];

export const SYMPTOMS = [
  'Fever / High Temperature', 'Loss of appetite', 'Lethargy / Weakness',
  'Nasal discharge', 'Excessive salivation / drooling', 'Blisters on tongue/feet/hooves',
  'Skin nodules / lumps', 'Lameness', 'Difficulty breathing',
  'Swollen lymph nodes', 'Diarrhea', 'Abortion / Stillbirth',
  'Reduced milk production', 'Sudden death', 'Bleeding from body openings',
  'Eye discharge / redness', 'Swollen legs / joints', 'Coughing',
];

export const mockAnimals: Animal[] = [
  { id: 'a1', tagId: 'GJ-AHD-00142', species: 'Cattle', breed: 'Gir', age: '4 yrs', sex: 'F', healthStatus: 'healthy', weight: '340 kg', lastExam: '2026-08-10', vaccinations: ['FMD', 'HS', 'BQ'] },
  { id: 'a2', tagId: 'GJ-AHD-00143', species: 'Cattle', breed: 'Kankrej', age: '2 yrs', sex: 'M', healthStatus: 'sick', weight: '210 kg', lastExam: '2026-09-01', vaccinations: ['FMD'] },
  { id: 'a3', tagId: 'GJ-AHD-00144', species: 'Buffalo', breed: 'Murrah', age: '6 yrs', sex: 'F', healthStatus: 'under_treatment', weight: '480 kg', lastExam: '2026-09-08', vaccinations: ['FMD', 'HS'] },
  { id: 'a4', tagId: 'GJ-AHD-00145', species: 'Goat', breed: 'Sirohi', age: '1 yr', sex: 'F', healthStatus: 'healthy', weight: '28 kg', lastExam: '2026-07-20', vaccinations: ['PPR'] },
  { id: 'a5', tagId: 'GJ-AHD-00146', species: 'Goat', breed: 'Sirohi', age: '1.5 yrs', sex: 'M', healthStatus: 'healthy', weight: '32 kg', lastExam: '2026-07-20', vaccinations: ['PPR'] },
  { id: 'a6', tagId: 'GJ-AHD-00147', species: 'Cattle', breed: 'Gir', age: '5 yrs', sex: 'F', healthStatus: 'healthy', weight: '380 kg', lastExam: '2026-08-15', vaccinations: ['FMD', 'HS', 'BQ', 'LSD'] },
];

export const mockReports: DiseaseReport[] = [
  {
    id: 'RPT-2026-08741', farmerId: 'f1', farmerName: 'Ramesh Patel', farmerPhone: '+91-98765-43210',
    village: 'Bhadaj', block: 'Daskroi', district: 'Ahmedabad',
    species: 'Cattle', affectedCount: 8, mortalityCount: 1, totalAnimals: 24,
    symptoms: ['Fever / High Temperature', 'Blisters on tongue/feet/hooves', 'Excessive salivation / drooling', 'Lameness'],
    riskScore: 78, riskLevel: 'high', status: 'lab_testing',
    createdAt: '2026-09-10T08:30:00Z', updatedAt: '2026-09-11T14:00:00Z',
    disease: 'Foot and Mouth Disease (FMD)',
    assignedVet: 'Dr. Anjali Sharma', assignedParavet: 'Mohan Desai',
    aiSuggestion: 'Symptom pattern strongly indicative of FMD. Isolate affected animals immediately. Collect epithelial samples for PCR confirmation.',
  },
  {
    id: 'RPT-2026-08699', farmerId: 'f1', farmerName: 'Ramesh Patel', farmerPhone: '+91-98765-43210',
    village: 'Bhadaj', block: 'Daskroi', district: 'Ahmedabad',
    species: 'Goat', affectedCount: 3, mortalityCount: 0, totalAnimals: 12,
    symptoms: ['Nasal discharge', 'Coughing', 'Eye discharge / redness'],
    riskScore: 35, riskLevel: 'medium', status: 'resolved',
    createdAt: '2026-08-20T10:00:00Z', updatedAt: '2026-08-28T16:00:00Z',
    disease: 'PPR (Peste des Petits Ruminants)',
    assignedVet: 'Dr. Anjali Sharma',
  },
  {
    id: 'RPT-2026-08810', farmerId: 'f2', farmerName: 'Suresh Chauhan', farmerPhone: '+91-97654-32109',
    village: 'Ranip', block: 'Daskroi', district: 'Ahmedabad',
    species: 'Cattle', affectedCount: 4, mortalityCount: 0, totalAnimals: 10,
    symptoms: ['Skin nodules / lumps', 'Fever / High Temperature', 'Swollen lymph nodes'],
    riskScore: 62, riskLevel: 'high', status: 'under_review',
    createdAt: '2026-09-12T06:15:00Z', updatedAt: '2026-09-12T06:15:00Z',
    aiSuggestion: 'Nodular skin lesions with fever - possible Lumpy Skin Disease. Immediate veterinary assessment required.',
  },
  {
    id: 'RPT-2026-08805', farmerId: 'f3', farmerName: 'Bhavna Solanki', farmerPhone: '+91-96543-21098',
    village: 'Viramgam', block: 'Viramgam', district: 'Ahmedabad',
    species: 'Buffalo', affectedCount: 2, mortalityCount: 1, totalAnimals: 6,
    symptoms: ['Sudden death', 'Swollen legs / joints', 'Bleeding from body openings'],
    riskScore: 91, riskLevel: 'critical', status: 'confirmed',
    createdAt: '2026-09-11T18:00:00Z', updatedAt: '2026-09-12T09:00:00Z',
    disease: 'Black Quarter (BQ)',
    assignedVet: 'Dr. Vikram Joshi',
    aiSuggestion: 'Critical: Sudden death with characteristic muscle swelling - strongly suggestive of Black Quarter. Emergency response required.',
  },
  {
    id: 'RPT-2026-08790', farmerId: 'f4', farmerName: 'Kantilal Mer', farmerPhone: '+91-94321-09876',
    village: 'Mandvi', block: 'Mandvi', district: 'Kutch',
    species: 'Camel', affectedCount: 1, mortalityCount: 0, totalAnimals: 4,
    symptoms: ['Fever / High Temperature', 'Nasal discharge', 'Loss of appetite'],
    riskScore: 28, riskLevel: 'low', status: 'assigned',
    createdAt: '2026-09-09T12:00:00Z', updatedAt: '2026-09-10T08:00:00Z',
    assignedParavet: 'Raju Bhatt',
  },
];

export const mockSamples: Sample[] = [
  {
    id: 'SMP-2026-04210', reportId: 'RPT-2026-08741', collectedBy: 'Mohan Desai',
    collectedByRole: 'Para-vet', collectionDate: '2026-09-11T10:30:00Z',
    sampleType: 'Epithelial tissue + Serum', animalTag: 'GJ-AHD-00142',
    status: 'testing', labName: 'GBRC Gandhinagar', disease: 'FMD',
    priority: 'urgent', testsConducted: ['RT-PCR', 'ELISA'],
  },
  {
    id: 'SMP-2026-04198', reportId: 'RPT-2026-08805', collectedBy: 'Dr. Vikram Joshi',
    collectedByRole: 'Veterinarian', collectionDate: '2026-09-12T08:00:00Z',
    sampleType: 'Blood + Muscle tissue', animalTag: 'GJ-AHD-00155',
    status: 'in_transit', labName: 'NDDB Laboratory, Anand', disease: 'BQ',
    priority: 'critical',
  },
  {
    id: 'SMP-2026-04176', reportId: 'RPT-2026-08699', collectedBy: 'Mohan Desai',
    collectedByRole: 'Para-vet', collectionDate: '2026-08-22T09:00:00Z',
    sampleType: 'Nasal swab + Blood', animalTag: 'GJ-AHD-00144',
    status: 'completed', labName: 'GBRC Gandhinagar', disease: 'PPR',
    priority: 'routine', result: 'Positive — PPR virus detected by RT-PCR. Serotype confirmed.',
    resultDate: '2026-08-25T14:30:00Z', testsConducted: ['RT-PCR', 'Virus neutralization test'],
  },
];

export const mockOutbreaks: OutbreakCluster[] = [
  { id: 'OBK-001', disease: 'Foot and Mouth Disease', district: 'Ahmedabad', block: 'Daskroi', affectedVillages: 7, affectedAnimals: 142, mortalityCount: 3, riskLevel: 'high', startDate: '2026-09-05', status: 'active', x: 52, y: 50 },
  { id: 'OBK-002', disease: 'Lumpy Skin Disease', district: 'Anand', block: 'Anand', affectedVillages: 4, affectedAnimals: 68, mortalityCount: 0, riskLevel: 'medium', startDate: '2026-09-08', status: 'active', x: 60, y: 52 },
  { id: 'OBK-003', disease: 'Black Quarter', district: 'Banaskantha', block: 'Danta', affectedVillages: 2, affectedAnimals: 18, mortalityCount: 5, riskLevel: 'critical', startDate: '2026-09-11', status: 'active', x: 30, y: 18 },
  { id: 'OBK-004', disease: 'PPR', district: 'Kutch', block: 'Bhuj', affectedVillages: 6, affectedAnimals: 210, mortalityCount: 8, riskLevel: 'high', startDate: '2026-08-28', status: 'contained', x: 15, y: 28 },
  { id: 'OBK-005', disease: 'Hemorrhagic Septicemia', district: 'Mehsana', block: 'Unjha', affectedVillages: 3, affectedAnimals: 44, mortalityCount: 2, riskLevel: 'medium', startDate: '2026-09-01', status: 'active', x: 45, y: 32 },
  { id: 'OBK-006', disease: 'Brucellosis', district: 'Rajkot', block: 'Gondal', affectedVillages: 5, affectedAnimals: 82, mortalityCount: 0, riskLevel: 'medium', startDate: '2026-08-20', status: 'active', x: 29, y: 56 },
];

export const mockVaccinations: VaccinationRecord[] = [
  { id: 'v1', animalTag: 'GJ-AHD-00142', species: 'Cattle', vaccine: 'Raksha FMD Poly', disease: 'FMD', dueDate: '2026-10-01', status: 'scheduled', nextDose: '2026-04-01' },
  { id: 'v2', animalTag: 'GJ-AHD-00143', species: 'Cattle', vaccine: 'Raksha FMD Poly', disease: 'FMD', dueDate: '2026-09-15', status: 'overdue' },
  { id: 'v3', animalTag: 'GJ-AHD-00144', species: 'Buffalo', vaccine: 'BQ-HS Bivalent', disease: 'BQ + HS', dueDate: '2026-09-20', status: 'due' },
  { id: 'v4', animalTag: 'GJ-AHD-00145', species: 'Goat', vaccine: 'Raksha-PPR', disease: 'PPR', dueDate: '2026-07-15', completedDate: '2026-07-14', status: 'completed', administeredBy: 'Dr. Anjali Sharma' },
  { id: 'v5', animalTag: 'GJ-AHD-00142', species: 'Cattle', vaccine: 'LSD Vaccine', disease: 'Lumpy Skin', dueDate: '2026-11-01', status: 'scheduled' },
];

export const mockUsers: User[] = [
  { id: 'u1', name: 'Ramesh Patel', role: 'farmer', district: 'Ahmedabad', block: 'Daskroi', phone: '+91-98765-43210', email: 'ramesh.p@gmail.com', status: 'active', lastLogin: '2026-09-12T06:00:00Z', createdAt: '2025-03-15T00:00:00Z' },
  { id: 'u2', name: 'Mohan Desai', role: 'paravet', district: 'Ahmedabad', block: 'Daskroi', phone: '+91-97654-32109', email: 'mohan.d@gvs.gov.in', status: 'active', lastLogin: '2026-09-12T07:30:00Z', createdAt: '2025-01-10T00:00:00Z' },
  { id: 'u3', name: 'Dr. Anjali Sharma', role: 'vet', district: 'Ahmedabad', phone: '+91-96543-21098', email: 'anjali.s@ahvd.gov.in', status: 'active', lastLogin: '2026-09-12T08:00:00Z', createdAt: '2024-11-05T00:00:00Z' },
  { id: 'u4', name: 'Priya Mehta', role: 'lab', district: 'Gandhinagar', phone: '+91-94532-10987', email: 'priya.m@gbrc.gov.in', status: 'active', lastLogin: '2026-09-12T09:00:00Z', createdAt: '2025-02-20T00:00:00Z' },
  { id: 'u5', name: 'IAS Mihir Bhatt', role: 'government', district: 'Gandhinagar', phone: '+91-93210-98765', email: 'mihir.b@ahvd.gov.in', status: 'active', lastLogin: '2026-09-11T18:00:00Z', createdAt: '2024-08-01T00:00:00Z' },
  { id: 'u6', name: 'Admin Kadam', role: 'admin', district: 'Gandhinagar', phone: '+91-92109-87654', email: 'admin@pashumitra.gov.in', status: 'active', lastLogin: '2026-09-12T08:30:00Z', createdAt: '2024-06-01T00:00:00Z' },
];

export const mockAuditLogs: AuditLog[] = [
  { id: 'al1', userId: 'u3', userName: 'Dr. Anjali Sharma', userRole: 'vet', action: 'STATUS_UPDATED', entity: 'DiseaseReport', entityId: 'RPT-2026-08741', timestamp: '2026-09-11T14:00:00Z', ipAddress: '103.21.48.12', details: 'Status changed from assigned → sample_collected' },
  { id: 'al2', userId: 'u2', userName: 'Mohan Desai', userRole: 'paravet', action: 'SAMPLE_CREATED', entity: 'Sample', entityId: 'SMP-2026-04210', timestamp: '2026-09-11T10:35:00Z', ipAddress: '106.51.22.8', details: 'Sample collected and dispatched to GBRC' },
  { id: 'al3', userId: 'u1', userName: 'Ramesh Patel', userRole: 'farmer', action: 'REPORT_SUBMITTED', entity: 'DiseaseReport', entityId: 'RPT-2026-08741', timestamp: '2026-09-10T08:30:00Z', ipAddress: '103.18.56.201', details: '8-step wizard completed, offline sync' },
  { id: 'al4', userId: 'u4', userName: 'Priya Mehta', userRole: 'lab', action: 'RESULT_ENTERED', entity: 'Sample', entityId: 'SMP-2026-04176', timestamp: '2026-08-25T14:30:00Z', ipAddress: '59.97.130.4', details: 'PPR positive result entered and verified' },
  { id: 'al5', userId: 'u6', userName: 'Admin Kadam', userRole: 'admin', action: 'USER_CREATED', entity: 'User', entityId: 'u2', timestamp: '2025-01-10T10:00:00Z', ipAddress: '59.97.128.1', details: 'Para-vet account created for Ahmedabad district' },
];

export const trendData = [
  { month: 'Apr', FMD: 12, LSD: 4, BQ: 2, PPR: 18, HS: 6 },
  { month: 'May', FMD: 18, LSD: 8, BQ: 1, PPR: 22, HS: 9 },
  { month: 'Jun', FMD: 14, LSD: 15, BQ: 3, PPR: 15, HS: 7 },
  { month: 'Jul', FMD: 22, LSD: 28, BQ: 5, PPR: 10, HS: 11 },
  { month: 'Aug', FMD: 34, LSD: 42, BQ: 8, PPR: 14, HS: 16 },
  { month: 'Sep', FMD: 28, LSD: 31, BQ: 12, PPR: 8, HS: 10 },
];

export const vaccinationCoverageData = [
  { district: 'Ahmedabad', fmd: 84, lsd: 71, bq: 78 },
  { district: 'Anand', fmd: 91, lsd: 68, bq: 82 },
  { district: 'Kutch', fmd: 72, lsd: 55, bq: 65 },
  { district: 'Banaskantha', fmd: 68, lsd: 44, bq: 70 },
  { district: 'Mehsana', fmd: 88, lsd: 76, bq: 80 },
  { district: 'Rajkot', fmd: 79, lsd: 63, bq: 72 },
];

export const TRANSLATIONS: Record<string, Record<string, string>> = {
  en: {
    appName: 'PashuMitra', appSubtitle: 'Livestock Health Surveillance',
    dashboard: 'Dashboard', animals: 'Animals', reportDisease: 'Report Disease',
    alerts: 'Alerts', vaccinations: 'Vaccinations', treatments: 'Treatments',
    fieldReports: 'Field Reports', sampleCollection: 'Sample Collection',
    offlineQueue: 'Offline Queue', cases: 'Cases', triage: 'Triage',
    laboratory: 'Laboratory', outbreaks: 'Outbreaks', riskMap: 'Risk Map',
    commandCenter: 'Command Center', trends: 'Disease Trends',
    users: 'Users', knowledgeBase: 'Knowledge Base', auditLogs: 'Audit Logs',
    submit: 'Submit', cancel: 'Cancel', saveDraft: 'Save Draft',
    next: 'Next', previous: 'Previous', offline: 'Offline',
    syncing: 'Syncing...', online: 'Online',
    selectRole: 'Select Your Role', continueAs: 'Continue',
    farmer: 'Farmer', paravet: 'Para-veterinarian', vet: 'Veterinarian',
    lab: 'Lab Technician', government: 'Government Officer', admin: 'Admin',
  },
  hi: {
    appName: 'पशुस्वास्थ्य', appSubtitle: 'पशुधन स्वास्थ्य निगरानी',
    dashboard: 'डैशबोर्ड', animals: 'पशु', reportDisease: 'रोग रिपोर्ट',
    alerts: 'चेतावनी', vaccinations: 'टीकाकरण', treatments: 'उपचार',
    fieldReports: 'फील्ड रिपोर्ट', sampleCollection: 'नमूना संग्रह',
    offlineQueue: 'ऑफलाइन कतार', cases: 'केस', triage: 'ट्राइएज',
    laboratory: 'प्रयोगशाला', outbreaks: 'प्रकोप', riskMap: 'जोखिम मानचित्र',
    commandCenter: 'कमांड सेंटर', trends: 'रोग प्रवृत्तियां',
    users: 'उपयोगकर्ता', knowledgeBase: 'ज्ञान आधार', auditLogs: 'ऑडिट लॉग',
    submit: 'जमा करें', cancel: 'रद्द करें', saveDraft: 'मसौदा सहेजें',
    next: 'आगे', previous: 'पीछे', offline: 'ऑफलाइन',
    syncing: 'सिंक हो रहा है...', online: 'ऑनलाइन',
    selectRole: 'अपनी भूमिका चुनें', continueAs: 'जारी रखें',
    farmer: 'किसान', paravet: 'पशु-सहायक', vet: 'पशु चिकित्सक',
    lab: 'लैब तकनीशियन', government: 'सरकारी अधिकारी', admin: 'एडमिन',
  },
  gu: {
    appName: 'પશુસ્વાસ્થ્ય', appSubtitle: 'પશુ સ્વાસ્થ્ય નિગ્રાણ',
    dashboard: 'ડૅશબોર્ડ', animals: 'પ્રાણી', reportDisease: 'રોગ રિપોર્ટ',
    alerts: 'ચેતવણી', vaccinations: 'રસીકરણ', treatments: 'સારવાર',
    fieldReports: 'ફીલ્ડ રિપોર્ટ', sampleCollection: 'નમૂના સંગ્રહ',
    offlineQueue: 'ઓફલાઇન કતાર', cases: 'કેસ', triage: 'ટ્રિઆઝ',
    laboratory: 'પ્રયોગશાળા', outbreaks: 'ફાટી નીકળ', riskMap: 'જોખમ નકશો',
    commandCenter: 'કમાન્ડ સેન્ટર', trends: 'રોગ વલણ',
    users: 'વપરાશકર્તા', knowledgeBase: 'જ્ઞાન આધાર', auditLogs: 'ઓડિટ લૉગ',
    submit: 'સ​ub​mit', cancel: 'રદ કરો', saveDraft: 'ડ્રાફ્ટ સાચવો',
    next: 'આગળ', previous: 'પાછળ', offline: 'ઓફલાઇન',
    syncing: 'સિંક થઈ રહ્યું છે...', online: 'ઓનલાઇન',
    selectRole: 'તમારી ભૂમિકા પસંદ કરો', continueAs: 'ચાલુ રાખો',
    farmer: 'ખેડૂત', paravet: 'પેરા-પશુ ચિકિત્સક', vet: 'પશુ ચિકિત્સક',
    lab: 'લેબ ટૅક', government: 'સરકારી અધિકારી', admin: 'એડમિન',
  },
};
