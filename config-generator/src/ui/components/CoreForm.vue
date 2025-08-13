<template>
  <form @submit.prevent="loadDiscovery" class="mb-4">
    <div class="row g-3">
      <div class="col-md-4">
        <label class="form-label">API URL</label>
        <input v-model="apiUrl" class="form-control" required />
      </div>
      <div class="col-md-4">
        <label class="form-label">Token</label>
        <input v-model="token" class="form-control" required />
      </div>
      <div class="col-md-2 align-self-end">
        <button class="btn btn-primary w-100" type="submit">Discover</button>
      </div>
    </div>
  </form>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
import { DiscoveryClient } from '../../api/DiscoveryClient';
import { DeviceResolver } from '../../domain/services/DeviceResolver';
import type { ResolvedDevice } from '../../domain/services/DeviceResolver';

const emit = defineEmits<{ (e: 'discovered', devices: ResolvedDevice[]): void }>();

const apiUrl = ref('');
const token = ref('');

async function loadDiscovery(): Promise<void> {
  const client = new DiscoveryClient();
  const resolver = new DeviceResolver();
  const devices = await client.fetch({ apiUrl: apiUrl.value, token: token.value });
  const resolved = devices.map((d) => resolver.resolve(d));
  emit('discovered', resolved);
}
</script>
