<script setup lang="ts">
// Loading skeleton for project detail
</script>

<template>
  <div class="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto">
    <!-- Header skeleton -->
    <div 
      class="swarm-header-card mb-8 animate-pulse"
      style="background: var(--swarm-bg-secondary);"
    >
      <div class="flex items-start justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-5">
          <div class="w-16 h-16 rounded-2xl" style="background: var(--swarm-bg-tertiary);" />
          <div>
            <div class="h-8 w-48 rounded-lg mb-3" style="background: var(--swarm-bg-tertiary);" />
            <div class="h-4 w-32 rounded" style="background: var(--swarm-bg-tertiary);" />
          </div>
        </div>
        <div class="h-8 w-24 rounded-full" style="background: var(--swarm-bg-tertiary);" />
      </div>
      <div class="mt-6 pt-5" style="border-top: 1px solid var(--swarm-border-light);">
        <div class="flex gap-3">
          <div class="h-10 w-20 rounded-lg" style="background: var(--swarm-bg-tertiary);" />
          <div class="h-10 w-24 rounded-lg" style="background: var(--swarm-bg-tertiary);" />
          <div class="h-10 w-28 rounded-lg" style="background: var(--swarm-bg-tertiary);" />
        </div>
      </div>
    </div>

    <!-- Metadata Grid skeleton -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 animate-pulse">
      <div 
        v-for="i in 4" 
        :key="i" 
        class="swarm-stat-card"
        style="background: var(--swarm-bg-secondary);"
      >
        <div class="h-3 w-16 rounded mb-3" style="background: var(--swarm-bg-tertiary);" />
        <div class="h-6 w-24 rounded" style="background: var(--swarm-bg-tertiary);" />
      </div>
    </div>

    <!-- Progress Section skeleton -->
    <div class="swarm-section mb-6 animate-pulse" style="background: var(--swarm-bg-secondary);">
      <div class="swarm-section-header">
        <div class="swarm-section-icon" style="background: var(--swarm-bg-tertiary);">
          <div class="w-4 h-4" />
        </div>
        <div class="h-5 w-24 rounded" style="background: var(--swarm-bg-tertiary);" />
      </div>
      <div 
        class="rounded-xl p-5"
        style="background: var(--swarm-bg-primary); border: 1px solid var(--swarm-border-light);"
      >
        <div class="space-y-3">
          <div class="h-4 w-full rounded" style="background: var(--swarm-bg-tertiary);" />
          <div class="h-4 w-3/4 rounded" style="background: var(--swarm-bg-tertiary);" />
          <div class="h-4 w-5/6 rounded" style="background: var(--swarm-bg-tertiary);" />
          <div class="h-4 w-2/3 rounded" style="background: var(--swarm-bg-tertiary);" />
        </div>
      </div>
    </div>

    <!-- Iterations skeleton -->
    <div class="swarm-section animate-pulse" style="background: var(--swarm-bg-secondary);">
      <div class="swarm-section-header !border-b-0 !pb-0 !mb-5">
        <div class="swarm-section-icon" style="background: var(--swarm-bg-tertiary);">
          <div class="w-4 h-4" />
        </div>
        <div class="h-5 w-24 rounded" style="background: var(--swarm-bg-tertiary);" />
      </div>
      <div class="space-y-3">
        <div 
          v-for="i in 3" 
          :key="i" 
          class="swarm-card"
          style="background: var(--swarm-bg-card);"
        >
          <div class="flex items-center gap-5">
            <div class="h-6 w-12 rounded" style="background: var(--swarm-bg-tertiary);" />
            <div class="h-4 w-16 rounded" style="background: var(--swarm-bg-tertiary);" />
            <div class="h-6 w-20 rounded-full" style="background: var(--swarm-bg-tertiary);" />
            <div class="h-4 w-12 rounded" style="background: var(--swarm-bg-tertiary);" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
