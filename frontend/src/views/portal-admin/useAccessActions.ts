import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import type { AccessRecord, PortalInvitation } from '@/api/portalAdmin'
import { usePortalAdminStore, type ActionResult } from '@/stores/portalAdmin'

export type RowAction = 'invite' | 'resend' | 'revoke' | 'suspend' | 'resume' | 'end'

export const actionLabels: Record<RowAction, { label: string, icon: string }> = {
  invite: { label: 'Einladen', icon: 'pi pi-send' },
  resend: { label: 'Erneut senden', icon: 'pi pi-refresh' },
  revoke: { label: 'Widerrufen', icon: 'pi pi-times' },
  suspend: { label: 'Sperren', icon: 'pi pi-ban' },
  resume: { label: 'Entsperren', icon: 'pi pi-lock-open' },
  end: { label: 'Zugang beenden', icon: 'pi pi-user-minus' },
}

/** Which actions apply to a record (members can be invited once the member portal is released). */
export function actionsFor(record: Pick<AccessRecord, 'kind' | 'state' | 'email'>): RowAction[] {
  const canMail = !!record.email
  switch (record.state) {
    case 'none': return canMail ? ['invite'] : []
    case 'expired': return canMail ? ['invite', 'end'] : ['end']
    case 'invited': return ['resend', 'revoke']
    case 'active': return ['suspend', 'end']
    case 'suspended': return ['resume', 'end']
    default: return []
  }
}

const destructive: Partial<Record<RowAction, (name: string) => { header: string, message: string, accept: string }>> = {
  suspend: name => ({ header: 'Zugang sperren?', message: `${name} kann sich nicht mehr anmelden. Alle Sitzungen werden sofort beendet. Du kannst den Zugang später wieder entsperren.`, accept: 'Sperren' }),
  end: name => ({ header: 'Zugang beenden?', message: `Der Portalzugang von ${name} wird beendet. Alle Sitzungen werden sofort beendet. Für einen neuen Zugang ist eine neue Einladung nötig.`, accept: 'Zugang beenden' }),
  revoke: name => ({ header: 'Einladung widerrufen?', message: `Der Einladungslink für ${name} funktioniert danach nicht mehr.`, accept: 'Widerrufen' }),
}

export function useAccessActions() {
  const store = usePortalAdminStore()
  const confirm = useConfirm()
  const toast = useToast()

  function report(result: ActionResult, success: string) {
    if (result.ok) toast.add({ severity: 'success', summary: success, life: 4000 })
    else toast.add({ severity: 'error', summary: 'Aktion nicht möglich', detail: result.message, life: 7000 })
    return result
  }

  function perform(action: RowAction, target: { kind: 'parent' | 'member', id: number, invitationId?: number }): Promise<ActionResult> {
    const subject = target.kind === 'parent' ? { parent: target.id } : { member: target.id }
    switch (action) {
      case 'invite': return store.invite(target.id, target.kind)
      case 'resend': return store.resend(target.invitationId as number)
      case 'revoke': return store.revoke(target.invitationId as number)
      case 'suspend': return store.suspend(subject)
      case 'resume': return store.resume(subject)
      default: return store.endAccess(subject)
    }
  }

  const done: Record<RowAction, string> = {
    invite: 'Einladung gesendet.', resend: 'Einladung erneut gesendet.', revoke: 'Einladung widerrufen.',
    suspend: 'Zugang gesperrt.', resume: 'Zugang entsperrt.', end: 'Zugang beendet.',
  }

  /** Runs the action; destructive ones ask first. `onDone` fires after success. */
  function request(action: RowAction, target: { kind: 'parent' | 'member', id: number, name: string, invitationId?: number }, onDone?: () => void) {
    const run = async () => {
      const result = report(await perform(action, target), done[action])
      if (result.ok) onDone?.()
    }
    const text = destructive[action]?.(target.name)
    if (!text) return run()
    confirm.require({
      header: text.header, message: text.message, icon: 'pi pi-exclamation-triangle',
      rejectProps: { label: 'Abbrechen', severity: 'secondary', outlined: true },
      acceptProps: { label: text.accept, severity: 'danger' },
      accept: () => { void run() },
    })
  }

  function forInvitation(invitation: PortalInvitation, action: 'resend' | 'revoke') {
    request(action, {
      kind: invitation.kind, id: (invitation.parent ?? invitation.member) as number,
      name: invitation.person_name, invitationId: invitation.id,
    })
  }

  return { request, forInvitation, report }
}
