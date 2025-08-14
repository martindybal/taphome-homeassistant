import type { Device } from '../domain/models/Device';

export interface CoreCredentials {
  token: string;
  apiUrl: string;
  webhookId?: string;
}

export class DiscoveryClient {
  async fetch(core: CoreCredentials): Promise<Device[]> {
    const response = await fetch(`https://api.taphome.com/api/TapHomeApi/v1/discovery?token=${core.token}`);
    if (!response.ok) {
      throw new Error('Failed to fetch discovery');
    }
    const data = await response.json();
    return data.devices as Device[];
  }
}
