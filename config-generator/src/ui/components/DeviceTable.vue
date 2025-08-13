<template>
  <table v-if="devices.length" class="table">
    <thead>
      <tr>
        <th>ID</th>
        <th>Name</th>
        <th>Usage</th>
        <th>Domain</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="device in devices" :key="device.id">
        <td>{{ device.id }}</td>
        <td>{{ device.name }}</td>
        <td>{{ device.usage }}</td>
        <td>{{ device.domain }}</td>
      </tr>
    </tbody>
  </table>
</template>

<script lang="ts" setup>
import type { ResolvedDevice } from '../../domain/services/DeviceResolver';

defineProps<{ devices: ResolvedDevice[] }>();
</script>
