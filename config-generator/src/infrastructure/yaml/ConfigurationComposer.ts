import yaml from 'js-yaml';
import type { ResolvedDevice } from '../../domain/services/DeviceResolver';

export class ConfigurationComposer {
  compose(devices: ResolvedDevice[]): string {
    const config = { devices: devices.map((d) => ({ id: d.id, domain: d.domain, name: d.name })) };
    return yaml.dump(config);
  }
}
