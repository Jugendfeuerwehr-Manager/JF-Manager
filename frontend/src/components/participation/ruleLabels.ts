import type { AgeOp, HasOp, RuleCondition, RuleGroup, RuleKind, ValueCondition, ValueKind } from '@/api/participation'

export const KIND_OPTIONS: Array<{ value: RuleKind, label: string, icon: string }> = [
  { value: 'qualification', label: 'Qualifikation', icon: 'pi pi-verified' },
  { value: 'special_task', label: 'Sonderaufgabe', icon: 'pi pi-briefcase' },
  { value: 'gender', label: 'Geschlecht', icon: 'pi pi-user' },
  { value: 'age', label: 'Alter am Diensttag', icon: 'pi pi-calendar' },
  { value: 'group', label: 'Gruppe', icon: 'pi pi-users' },
  { value: 'status', label: 'Status', icon: 'pi pi-tag' },
  { value: 'department', label: 'Abteilung', icon: 'pi pi-building' },
]

const HAS_OPS: Array<{ value: HasOp, label: string }> = [
  { value: 'has_any', label: 'hat mindestens eine von' },
  { value: 'has_all', label: 'hat alle von' },
  { value: 'has_none', label: 'hat keine von' },
]

export const OP_OPTIONS: Record<RuleKind, Array<{ value: string, label: string }>> = {
  qualification: HAS_OPS,
  special_task: HAS_OPS,
  gender: [{ value: 'in', label: 'ist einer von' }],
  age: [
    { value: 'min', label: 'mindestens' },
    { value: 'max', label: 'höchstens' },
    { value: 'between', label: 'zwischen' },
  ],
  group: [{ value: 'in', label: 'gehört zu einer von' }],
  status: [{ value: 'in', label: 'hat einen von' }],
  department: [{ value: 'in', label: 'gehört zu einer von' }],
}

export const VALUE_PLACEHOLDER: Record<ValueKind, string> = {
  qualification: 'Qualifikationen suchen und wählen',
  special_task: 'Sonderaufgaben suchen und wählen',
  gender: 'Geschlecht wählen',
  group: 'Gruppen suchen und wählen',
  status: 'Status wählen',
  department: 'Abteilungen suchen und wählen',
}

export function newCondition(kind: RuleKind = 'qualification'): RuleCondition {
  if (kind === 'age') return { kind, op: 'min', min: 18 }
  return { kind, op: OP_OPTIONS[kind][0]!.value as ValueCondition['op'], values: [] } as ValueCondition
}

export function changeKind(kind: RuleKind): RuleCondition {
  return newCondition(kind)
}

export function changeOp(condition: RuleCondition, op: string): RuleCondition {
  if (condition.kind !== 'age') return { ...condition, op: op as ValueCondition['op'] }
  const next: RuleCondition = { kind: 'age', op: op as AgeOp }
  if (op !== 'max') next.min = condition.min ?? 18
  if (op !== 'min') next.max = condition.max ?? (condition.min ?? 18)
  return next
}

export const isGroup = (item: RuleCondition | RuleGroup): item is RuleGroup => !('kind' in item)

/** Errors the server reported for a path and everything below it. */
export function errorsFor(errors: Record<string, string>, path: string): Array<{ field: string, message: string }> {
  return Object.entries(errors)
    .filter(([key]) => key === path || key.startsWith(`${path}.`) && !key.startsWith(`${path}.rules`))
    .map(([key, message]) => ({ field: key.slice(path.length + 1), message }))
}
