<template>
  <div>
    <h3>Binary Sensor Config</h3>
    <div class="mb-3">
      <label class="form-label">Device Class</label>
      <input v-model="deviceClass" class="form-control" />
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue';

const deviceClass = ref('');
</script>
