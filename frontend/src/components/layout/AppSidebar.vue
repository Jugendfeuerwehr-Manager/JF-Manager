<template>
  <!-- Mobile: PrimeVue Sidebar -->
  <Sidebar
    v-model:visible="sidebarVisible"
    position="left"
    class="w-20rem"
    @update:visible="$emit('update:visible', $event)"
  >
    <template #header>
      <div class="flex align-items-center gap-2">
        <i class="pi pi-users text-primary text-2xl"></i>
        <span class="text-xl font-bold gradient-text">JF-Manager</span>
      </div>
    </template>
    
    <Menu :model="menuItems" class="w-full border-none">
      <template #item="{ item, props }">
        <router-link v-if="item.route" v-slot="{ href, navigate, isActive }" :to="item.route" custom>
          <a :href="href" v-bind="props.action" @click="navigate" :class="{ 'active-menu-item': isActive }">
            <i :class="item.icon"></i>
            <span class="ml-2">{{ item.label }}</span>
          </a>
        </router-link>
        <a v-else :href="item.url" :target="item.target" v-bind="props.action">
          <i :class="item.icon"></i>
          <span class="ml-2">{{ item.label }}</span>
        </a>
      </template>
    </Menu>
  </Sidebar>

  <!-- Desktop: Fixed Sidebar (collapsible) -->
  <aside v-if="!isMobile" :class="['sidebar', { 'sidebar-collapsed': isCollapsed }]">
    <!-- Toggle Button -->
    <div class="sidebar-toggle-container">
      <Button
        :icon="isCollapsed ? 'pi pi-angle-right' : 'pi pi-angle-left'"
        text
        rounded
        size="small"
        class="sidebar-toggle-btn"
        @click="toggleCollapsed"
        aria-label="Toggle Sidebar"
      />
    </div>

    <!-- Menu Items -->
    <nav class="sidebar-nav">
      <template v-for="item in menuItems" :key="item.label">
        <router-link
          v-if="item.route"
          :to="item.route"
          class="sidebar-item"
          active-class="sidebar-item-active"
          :title="isCollapsed ? item.label : ''"
        >
          <i :class="['pi', item.icon]"></i>
          <span v-if="!isCollapsed" class="sidebar-item-label">{{ item.label }}</span>
        </router-link>
        <Divider v-else-if="item.separator" class="my-2" />
      </template>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import Sidebar from 'primevue/sidebar';
import Menu from 'primevue/menu';
import Button from 'primevue/button';
import Divider from 'primevue/divider';

interface MenuItem {
  label?: string;
  icon?: string;
  route?: string;
  separator?: boolean;
}

interface Props {
  visible: boolean;
  isMobile: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
}>();

const route = useRoute();
const isCollapsed = ref(false);
const sidebarVisible = computed({
  get: () => props.visible,
  set: (value: boolean) => emit('update:visible', value)
});

const menuItems: MenuItem[] = [
  { label: 'Dashboard', icon: 'pi pi-home', route: '/dashboard' },
  { separator: true },
  { label: 'Mitglieder', icon: 'pi pi-users', route: '/members' },
  { label: 'Eltern', icon: 'pi pi-user', route: '/parents' },
  { separator: true },
  { label: 'Inventar', icon: 'pi pi-box', route: '/inventory' },
  { label: 'Bestellungen', icon: 'pi pi-shopping-cart', route: '/orders' },
  { separator: true },
  { label: 'Dienstbuch', icon: 'pi pi-book', route: '/servicebook' },
  { label: 'Qualifikationen', icon: 'pi pi-check-circle', route: '/qualifications' },
  { separator: true },
  { label: 'Einstellungen', icon: 'pi pi-cog', route: '/settings' },
];

const toggleCollapsed = () => {
  isCollapsed.value = !isCollapsed.value;
  // Save preference to localStorage
  localStorage.setItem('sidebarCollapsed', String(isCollapsed.value));
};

// Restore collapsed state from localStorage
const savedState = localStorage.getItem('sidebarCollapsed');
if (savedState !== null) {
  isCollapsed.value = savedState === 'true';
}

// Close mobile sidebar on route change
watch(() => route.path, () => {
  if (props.isMobile && props.visible) {
    emit('update:visible', false);
  }
});
</script>

<style scoped>
.sidebar-header {
  display: flex;
  align-items: center;
  padding: 1.5rem 1rem;
  border-bottom: 1px solid var(--surface-border);
  gap: 0.75rem;
}

.sidebar-header i {
  font-size: 1.75rem;
  color: var(--primary-color);
}

.desktop-sidebar {
  position: fixed;
  left: 0;
  top: 70px;
  bottom: 0;
  width: 16rem;
  background: var(--surface-card);
  border-right: 1px solid var(--surface-border);
  overflow-y: auto;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.05);
}

:deep(.p-menu) {
  padding: 1rem 0.75rem;
  background: transparent;
}

:deep(.p-menuitem) {
  margin-bottom: 0.25rem;
}

:deep(.p-menuitem-link) {
  padding: 0.875rem 1rem;
  border-radius: 8px;
  transition: all 0.2s ease;
  font-weight: 500;
}

:deep(.p-menuitem-link:hover) {
  background: var(--primary-50);
  transform: translateX(4px);
}

:deep(.p-menuitem-link i) {
  font-size: 1.1rem;
  width: 1.5rem;
}

:deep(.bg-primary-50) {
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.1) 0%, transparent 100%);
  border-left: 3px solid var(--primary-500);
  color: var(--primary-500);
  font-weight: 600;
}

:deep(.p-menu-separator) {
  margin: 0.75rem 0.5rem;
  border-top: 1px solid var(--surface-border);
}

/* Mobile Drawer Styles */
:deep(.p-drawer .p-drawer-content) {
  background: var(--surface-card);
}

:deep(.p-drawer .p-menu) {
  padding: 0.5rem;
}
</style>
