import yaml from 'js-yaml';
import type { ResolvedDevice } from '../../domain/services/DeviceResolver';

export class ConfigurationParser {
  parse(content: string): ResolvedDevice[] {
    const data = yaml.load(content) as Record<string, unknown>;
    const devices = (data.devices as ResolvedDevice[] | undefined) || [];
    return devices;
  }
}
