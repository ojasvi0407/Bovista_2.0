import { describe, expect, it, vi } from 'vitest';

import { AuthApi } from './auth';

describe('AuthApi', () => {
  it('sends a farmer OTP request with the device identifier', async () => {
    const post = vi.fn().mockResolvedValue({ accepted: true });
    const auth = new AuthApi({ post } as never);

    await expect(auth.requestFarmerOtp('+919999999999', 'device-1')).resolves.toEqual({
      accepted: true,
    });
    expect(post).toHaveBeenCalledWith('/auth/otp/request', {
      mobile_number: '+919999999999',
      device_id: 'device-1',
    });
  });

  it('converts the staff password step into an MFA challenge', async () => {
    const post = vi.fn().mockResolvedValue({ mfa_required: true, challenge_token: 'challenge' });
    const auth = new AuthApi({ post } as never);

    await expect(auth.beginStaffLogin('vet@example.gov', 'password123')).resolves.toEqual('challenge');
  });
});
