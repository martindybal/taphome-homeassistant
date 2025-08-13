import type { Device } from '../models/Device';
import { UsageToDomainMapper } from '../mappers/UsageToDomainMapper';

export interface ResolvedDevice extends Device {
  domain?: string;
}

export class DeviceResolver {
  private readonly usageMapper = new UsageToDomainMapper();

  resolve(device: Device): ResolvedDevice {
    const domain = this.usageMapper.map(device.usage);
    return { ...device, domain };
  }
}
