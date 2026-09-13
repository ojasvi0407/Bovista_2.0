import type { Role } from './types';

const roleMap: Record<string, Role> = {
  ADMIN: 'admin',
  DISTRICT_OFFICER: 'government',
  VETERINARIAN: 'vet',
  PARAVET: 'paravet',
  LAB_TECHNICIAN: 'lab',
  FARMER: 'farmer',
};

const rolePriority = ['ADMIN', 'DISTRICT_OFFICER', 'VETERINARIAN', 'PARAVET', 'LAB_TECHNICIAN', 'FARMER'];

export function frontendRoleFor(roles: string[]): Role | null {
  for (const backendRole of rolePriority) {
    if (roles.includes(backendRole)) return roleMap[backendRole];
  }
  return null;
}
