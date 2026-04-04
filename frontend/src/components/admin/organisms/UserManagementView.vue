<template>
  <div class="admin-view p-3 md:p-4">
    <div class="mb-4">
      <h1 class="text-3xl font-bold m-0">Benutzerverwaltung</h1>
      <p class="text-color-secondary mt-1 mb-0">Benutzer, Gruppen und Berechtigungen verwalten</p>
    </div>

    <TabView lazy>
      <TabPanel>
        <template #header>
          <i class="pi pi-users mr-2" />
          <span>Benutzer</span>
        </template>
        <UsersPanel />
      </TabPanel>

      <TabPanel>
        <template #header>
          <i class="pi pi-lock mr-2" />
          <span>Gruppen &amp; Berechtigungen</span>
        </template>
        <GroupsPanel />
      </TabPanel>
    </TabView>

  </div>
</template>

<script setup lang="ts">
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import UsersPanel from '@/components/admin/organisms/UsersPanel.vue'
import GroupsPanel from '@/components/admin/organisms/GroupsPanel.vue'
</script>

<style scoped>
.admin-view {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
