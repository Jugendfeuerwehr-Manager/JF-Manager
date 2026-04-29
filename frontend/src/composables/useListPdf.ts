/**
 * PDF checklist generator for MemberLists using pdfmake.
 */
import type { MemberListDetail } from '@/types/lists'

export function useListPdf() {
  async function generateChecklist(list: MemberListDetail) {
    const [pdfMakeModule, pdfFontsModule] = await Promise.all([
      import('pdfmake/build/pdfmake'),
      import('pdfmake/build/vfs_fonts'),
    ])
    const pdfMake = pdfMakeModule.default
    const pdfFonts = pdfFontsModule.default
    // @ts-expect-error pdfmake vfs
    pdfMake.vfs = pdfFonts.pdfMake?.vfs ?? pdfFonts.vfs

    const now = new Date().toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
    const timeStr = new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })

    // ── Sort entries alphabetically ──────────────────────────────────────
    const entries = [...list.entries].sort((a, b) =>
      a.member.full_name.localeCompare(b.member.full_name, 'de'),
    )

    const checkedCount = entries.filter((e) => e.checked).length
    const totalCount = entries.length

    // ── Table rows ───────────────────────────────────────────────────────
    const tableBody: object[][] = [
      // Header row
      [
        { text: '#', style: 'tableHeader', alignment: 'center' },
        { text: 'Name', style: 'tableHeader' },
        { text: 'Gruppe', style: 'tableHeader' },
        { text: 'Status', style: 'tableHeader' },
        { text: 'Anwesend', style: 'tableHeader', alignment: 'center' },
        { text: 'Notiz', style: 'tableHeader' },
      ],
      // Data rows
      ...entries.map((entry, idx) => [
        { text: String(idx + 1), alignment: 'center', color: '#666' },
        {
          text: entry.member.full_name,
          bold: true,
          color: entry.checked ? '#166534' : '#1e293b',
        },
        { text: entry.member.group?.name ?? '–', color: '#64748b', fontSize: 9 },
        {
          text: entry.member.status?.name ?? '–',
          color: entry.member.status?.color ?? '#64748b',
          fontSize: 9,
        },
        {
          // Checkbox: filled ■ if checked, empty □ if not
          text: entry.checked ? '■' : '□',
          alignment: 'center',
          fontSize: 14,
          color: entry.checked ? '#16a34a' : '#94a3b8',
        },
        { text: entry.notes ?? '', fontSize: 9, color: '#64748b' },
      ]),
    ]

    const docDefinition = {
      pageSize: 'A4',
      pageMargins: [40, 60, 40, 60] as [number, number, number, number],
      header: {
        columns: [
          {
            text: list.name,
            style: 'headerTitle',
            margin: [40, 20, 0, 0],
          },
          {
            text: `Erstellt: ${now} ${timeStr}`,
            alignment: 'right',
            fontSize: 9,
            color: '#94a3b8',
            margin: [0, 24, 40, 0],
          },
        ],
      },
      footer: (currentPage: number, pageCount: number) => {
        return {
          columns: [
            {
              text: list.description || '',
              fontSize: 8,
              color: '#94a3b8',
              margin: [40, 0, 0, 0],
            },
            {
              text: `Seite ${currentPage} von ${pageCount}  |  ${checkedCount}/${totalCount} anwesend`,
              alignment: 'right',
              fontSize: 8,
              color: '#94a3b8',
              margin: [0, 0, 40, 0],
            },
          ],
          margin: [0, 10, 0, 0],
        } as any
      },
      content: [
        // Color accent bar
        {
          canvas: [
            {
              type: 'rect',
              x: 0,
              y: 0,
              w: 515,
              h: 6,
              r: 3,
              color: list.color || '#3B82F6',
            },
          ],
          margin: [0, 0, 0, 12],
        },
        // Sub-header row: description + summary badge
        {
          columns: [
            {
              text: list.description || '',
              fontSize: 10,
              color: '#64748b',
              width: '*',
            },
            {
              text: `${checkedCount} / ${totalCount} anwesend`,
              fontSize: 10,
              bold: true,
              color: '#1e293b',
              alignment: 'right',
              width: 'auto',
            },
          ],
          columnGap: 10,
          margin: [0, 0, 0, 16],
        },
        // Checklist table
        {
          table: {
            headerRows: 1,
            widths: ['auto', '*', 80, 70, 55, 90],
            body: tableBody,
          },
          layout: {
            hLineWidth: (i: number, _node: unknown) => (i === 0 || i === 1 ? 1.5 : 0.5),
            vLineWidth: () => 0,
            hLineColor: (i: number) => (i === 0 || i === 1 ? '#e2e8f0' : '#f1f5f9'),
            fillColor: (rowIndex: number) => {
              if (rowIndex === 0) return '#f8fafc'
              const entry = entries[rowIndex - 1]
              if (entry?.checked) return '#f0fdf4'
              return rowIndex % 2 === 0 ? '#ffffff' : '#fafafa'
            },
            paddingLeft: () => 8,
            paddingRight: () => 8,
            paddingTop: () => 6,
            paddingBottom: () => 6,
          },
        },
      ],
      styles: {
        headerTitle: {
          fontSize: 18,
          bold: true,
          color: '#1e293b',
        },
        tableHeader: {
          fontSize: 9,
          bold: true,
          color: '#64748b',
          fillColor: '#f8fafc',
          textTransform: 'uppercase' as 'uppercase',
        },
      },
      defaultStyle: {
        fontSize: 10,
        font: 'Roboto',
        color: '#1e293b',
      },
    }

    const safeFileName = list.name.replace(/[^a-z0-9äöüÄÖÜß\s_-]/gi, '').trim() || 'Liste'
    pdfMake.createPdf(docDefinition as Parameters<typeof pdfMake.createPdf>[0]).download(
      `${safeFileName}_${now.replace(/\./g, '-')}.pdf`,
    )
  }

  return { generateChecklist }
}
