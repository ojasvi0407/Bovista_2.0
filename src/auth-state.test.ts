import { describe, expect, it } from 'vitest';

import { frontendRoleFor } from './auth-state';

describe('frontendRoleFor', () => {
  it('selects the authorized interface from backend roles rather than a UI choice', () => {
    expect(frontendRoleFor(['FARMER'])).toBe('farmer');
    expect(frontendRoleFor(['VETERINARIAN'])).toBe('vet');
    expect(frontendRoleFor(['DISTRICT_OFFICER', 'VETERINARIAN'])).toBe('government');
  });

  it('rejects a token with no role that has a frontend workspace', () => {
    expect(frontendRoleFor(['UNKNOWN_ROLE'])).toBeNull();
  });
});
