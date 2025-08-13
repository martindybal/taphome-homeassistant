import { describe, expect, it } from 'vitest';
import { DeviceResolver } from './DeviceResolver';

describe('DeviceResolver', () => {
  it('maps usage to domain', () => {
    const resolver = new DeviceResolver();
    const result = resolver.resolve({ id: '1', type: 't', usage: 'DoorSensor', name: 'Door' });
    expect(result.domain).toBe('binary_sensor');
  });
});
