import type { ApiClient } from './client';

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  access_expires_in: number;
};

type StaffChallenge = { mfa_required: boolean; challenge_token: string };

export class AuthApi {
  constructor(private readonly client: Pick<ApiClient, 'post'>) {}

  requestFarmerOtp(mobileNumber: string, deviceId: string): Promise<{ accepted: boolean }> {
    return this.client.post('/auth/otp/request', {
      mobile_number: mobileNumber,
      device_id: deviceId,
    });
  }

  verifyFarmerOtp(mobileNumber: string, code: string, deviceId: string): Promise<TokenPair> {
    return this.client.post('/auth/otp/verify', {
      mobile_number: mobileNumber,
      code,
      device_id: deviceId,
    });
  }

  async beginStaffLogin(staffIdentifier: string, password: string): Promise<string> {
    const response = await this.client.post<StaffChallenge>('/auth/staff/login', {
      staff_identifier: staffIdentifier,
      password,
    });
    return response.challenge_token;
  }

  verifyStaffMfa(challengeToken: string, code: string, deviceId: string): Promise<TokenPair> {
    return this.client.post('/auth/staff/mfa/verify', {
      challenge_token: challengeToken,
      code,
      device_id: deviceId,
    });
  }

  refresh(refreshToken: string, deviceId: string): Promise<TokenPair> {
    return this.client.post('/auth/refresh', {
      refresh_token: refreshToken,
      device_id: deviceId,
    });
  }
}
