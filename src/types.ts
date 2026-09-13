export type Role = 'farmer' | 'paravet' | 'vet' | 'lab' | 'government' | 'admin';
export type Lang = 'en' | 'hi' | 'gu';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type ReportStatus =
  | 'submitted' | 'under_review' | 'assigned' | 'sample_collected'
  | 'lab_testing' | 'confirmed' | 'resolved' | 'rejected';
export type SampleStatus = 'collected' | 'in_transit' | 'received' | 'testing' | 'completed' | 'rejected';
export type CaseStatus = 'new' | 'assigned' | 'investigating' | 'sample_sent' | 'confirmed' | 'treated' | 'closed';
export type VaccinationStatus = 'due' | 'completed' | 'overdue' | 'scheduled';

export interface Animal {
  id: string;
  tagId: string;
  species: 'Cattle' | 'Buffalo' | 'Goat' | 'Sheep' | 'Camel';
  breed: string;
  age: string;
  sex: 'M' | 'F';
  healthStatus: 'healthy' | 'sick' | 'under_treatment' | 'deceased';
  weight?: string;
  lastExam: string;
  vaccinations: string[];
}

export interface DiseaseReport {
  id: string;
  farmerId: string;
  farmerName: string;
  farmerPhone: string;
  village: string;
  block: string;
  district: string;
  species: string;
  affectedCount: number;
  mortalityCount: number;
  totalAnimals: number;
  symptoms: string[];
  riskScore: number;
  riskLevel: RiskLevel;
  status: ReportStatus;
  createdAt: string;
  updatedAt: string;
  disease?: string;
  assignedVet?: string;
  assignedParavet?: string;
  aiSuggestion?: string;
  notes?: string;
}

export interface Sample {
  id: string;
  reportId: string;
  collectedBy: string;
  collectedByRole: string;
  collectionDate: string;
  sampleType: string;
  animalTag: string;
  status: SampleStatus;
  labName: string;
  disease: string;
  priority: 'routine' | 'urgent' | 'critical';
  result?: string;
  resultDate?: string;
  testsConducted?: string[];
}

export interface OutbreakCluster {
  id: string;
  disease: string;
  district: string;
  block: string;
  affectedVillages: number;
  affectedAnimals: number;
  mortalityCount: number;
  riskLevel: RiskLevel;
  startDate: string;
  status: 'active' | 'contained' | 'resolved';
  x: number;
  y: number;
}

export interface VaccinationRecord {
  id: string;
  animalTag: string;
  species: string;
  vaccine: string;
  disease: string;
  dueDate: string;
  completedDate?: string;
  status: VaccinationStatus;
  administeredBy?: string;
  nextDose?: string;
}

export interface User {
  id: string;
  name: string;
  role: Role;
  district: string;
  block?: string;
  phone: string;
  email: string;
  status: 'active' | 'inactive' | 'suspended';
  lastLogin: string;
  createdAt: string;
}

export interface AuditLog {
  id: string;
  userId: string;
  userName: string;
  userRole: Role;
  action: string;
  entity: string;
  entityId: string;
  timestamp: string;
  ipAddress: string;
  details?: string;
}

export interface WizardData {
  step: number;
  animalId?: string;
  animalTag?: string;
  species?: string;
  symptoms?: string[];
  affectedCount?: number;
  mortalityCount?: number;
  totalAnimals?: number;
  village?: string;
  block?: string;
  district?: string;
  gpsLat?: number;
  gpsLng?: number;
  waterSource?: string;
  recentMovement?: boolean;
  newAnimals?: boolean;
  notes?: string;
  photoTaken?: boolean;
  isDraft?: boolean;
}
