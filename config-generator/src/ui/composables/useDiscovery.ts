import { ref } from 'vue';
import { DiscoveryClient } from '../../api/DiscoveryClient';
import { DeviceResolver } from '../../domain/services/DeviceResolver';
import type { ResolvedDevice } from '../../domain/services/DeviceResolver';
import type { CoreCredentials } from '../../api/DiscoveryClient';

export function useDiscovery() {
  const devices = ref<ResolvedDevice[]>([]);
  const loading = ref(false);

  async function discover(core: CoreCredentials): Promise<void> {
    loading.value = true;
    try {
      const client = new DiscoveryClient();
      const resolver = new DeviceResolver();
      const raw = await client.fetch(core);
      devices.value = raw.map((d) => resolver.resolve(d));
    } finally {
      loading.value = false;
    }
  }

  return { devices, loading, discover };
}
