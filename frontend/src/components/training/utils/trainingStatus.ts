import type { StatusSeverity } from '@/components/common/StatusBadge.vue'
import type { TrainingStatus } from '@/types/training'

export interface TrainingStatusMeta {
  label: string
  severity: StatusSeverity
  /** Distinct symbol per status, so compact views never rely on colour alone. */
  icon: string
}

export const TRAINING_STATUS: Record<TrainingStatus, TrainingStatusMeta> = {
  draft: { label: 'Entwurf', severity: 'neutral', icon: 'pi pi-pencil' },
  published: { label: 'Veröffentlicht', severity: 'info', icon: 'pi pi-megaphone' },
  completed: { label: 'Abgeschlossen', severity: 'success', icon: 'pi pi-check-circle' },
  cancelled: { label: 'Abgesagt', severity: 'danger', icon: 'pi pi-times-circle' },
}

export function trainingStatusMeta(status: TrainingStatus | null | undefined): TrainingStatusMeta {
  return TRAINING_STATUS[status ?? 'draft'] ?? TRAINING_STATUS.draft
}
