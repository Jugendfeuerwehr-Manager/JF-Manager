<template>
  <div class="categories-management">
    <!-- Header -->
    <div class="section-header">
      <h3>
        <i class="pi pi-tags"></i>
        Kategorien verwalten
      </h3>
      <Button label="Neue Kategorie" icon="pi pi-plus" @click="openCreateDialog" />
    </div>

    <!-- Categories Grid -->
    <div class="categories-grid">
      <Card
        v-for="category in inventoryStore.categories"
        :key="category.id"
        class="category-card"
        @click="openEditDialog(category)"
      >
        <template #content>
          <div class="category-content">
            <div class="category-info">
              <div class="category-name-row">
                <span class="category-name">{{ category.name }}</span>
                <Tag value="G" icon="pi pi-globe" severity="contrast" />
              </div>
              <Tag :value="`${category.item_count || 0} Artikel`" severity="secondary" />
            </div>
            <div class="category-actions">
              <Button
                icon="pi pi-pencil"
                size="small"
                text
                rounded
                @click.stop="openEditDialog(category)"
              />
              <Button
                icon="pi pi-trash"
                size="small"
                text
                rounded
                severity="danger"
                @click.stop="confirmDelete(category)"
              />
            </div>
          </div>
        </template>
      </Card>

      <Card v-if="inventoryStore.categories.length === 0" class="empty-card">
        <template #content>
          <div class="empty-content">
            <i class="pi pi-tags"></i>
            <p>Keine Kategorien gefunden</p>
            <Button label="Kategorie erstellen" icon="pi pi-plus" @click="openCreateDialog" />
          </div>
        </template>
      </Card>
    </div>

    <!-- Category Form Dialog -->
    <CategoryFormDialog
      v-model="showCategoryDialog"
      :category="selectedCategory"
      @success="onCategorySaved"
    />

    <!-- Delete Confirmation -->
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import CategoryFormDialog from '../molecules/CategoryFormDialog.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { Category } from '@/types/inventory'

const inventoryStore = useInventoryStore()
const confirm = useConfirm()
const toast = useToast()

const showCategoryDialog = ref(false)
const selectedCategory = ref<Category | null>(null)

function openCreateDialog() {
  selectedCategory.value = null
  showCategoryDialog.value = true
}

function openEditDialog(category: Category) {
  selectedCategory.value = category
  showCategoryDialog.value = true
}

function confirmDelete(category: Category) {
  const itemCount = category.item_count || 0

  if (itemCount > 0) {
    toast.add({
      severity: 'warn',
      summary: 'Warnung',
      detail: `Die Kategorie "${category.name}" enthält noch ${itemCount} Artikel und kann nicht gelöscht werden.`,
      life: 5000
    })
    return
  }

  confirm.require({
    message: `Möchten Sie die Kategorie "${category.name}" wirklich löschen?`,
    header: 'Kategorie löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    accept: async () => {
      try {
        await inventoryStore.deleteCategory(category.id)
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: 'Kategorie wurde gelöscht',
          life: 3000
        })
      } catch {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'Kategorie konnte nicht gelöscht werden',
          life: 5000
        })
      }
    }
  })
}

function onCategorySaved() {
  showCategoryDialog.value = false
  selectedCategory.value = null
}
</script>

<style scoped>
.categories-management {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}

.category-card {
  cursor: pointer;
  transition: all 0.2s ease;
}

.category-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.category-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.category-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.category-name-row {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.category-name {
  font-weight: 600;
  font-size: 1rem;
}

.category-actions {
  display: flex;
  gap: 0.25rem;
}

.empty-card {
  grid-column: 1 / -1;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  text-align: center;
}

.empty-content i {
  font-size: 3rem;
  color: var(--text-color-secondary);
  margin-bottom: 1rem;
}

.empty-content p {
  margin: 0 0 1rem;
}

@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .categories-grid {
    grid-template-columns: 1fr;
  }
}
</style>
