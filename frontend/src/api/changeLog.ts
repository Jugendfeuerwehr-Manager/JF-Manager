import apiClient from './index'
import type { ChangeLogEntry } from '@/types/changeLog'

export const changeLogApi = {
  forRecord(kind: 'member' | 'parent', id: number) {
    return apiClient.get<{ results: ChangeLogEntry[] }>(`/${kind === 'member' ? 'members' : 'parents'}/${id}/change-log/`)
  },
}
