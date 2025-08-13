<template>
  <div class="container my-4">
    <h1 class="mb-4">TapHome Config Generator</h1>
    <CoreForm @discovered="onDiscovered" />
    <DeviceTable :devices="devices" />
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
import CoreForm from './ui/components/CoreForm.vue';
import DeviceTable from './ui/components/DeviceTable.vue';
import type { Device } from './domain/models/Device';

const devices = ref<Device[]>([]);

function onDiscovered(found: Device[]): void {
  devices.value = found;
}
</script>
