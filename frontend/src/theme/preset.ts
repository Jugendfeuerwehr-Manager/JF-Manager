import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'
import { brand, roles, surface } from './palette'

/**
 * JF-Manager PrimeVue preset (DES-01): Aura structure with Feuerwehrrot,
 * a cool neutral surface scale, 8 px based radii and a visible focus ring.
 */
export const JfPreset = definePreset(Aura, {
  primitive: {
    borderRadius: { none: '0', xs: '2px', sm: '4px', md: '8px', lg: '12px', xl: '16px' },
  },
  semantic: {
    primary: brand,
    focusRing: { width: '2px', style: 'solid', color: '{primary.color}', offset: '2px', shadow: 'none' },
    formField: {
      paddingX: '0.75rem',
      paddingY: '0.5rem',
      borderRadius: '{border.radius.md}',
      focusRing: { width: '2px', style: 'solid', color: '{primary.color}', offset: '1px', shadow: 'none' },
    },
    content: { borderRadius: '{border.radius.lg}' },
    colorScheme: {
      light: {
        surface,
        primary: {
          color: roles.light.primary,
          contrastColor: roles.light.onPrimary,
          hoverColor: roles.light.primaryHover,
          activeColor: roles.light.primaryActive,
        },
        highlight: {
          background: '{primary.50}',
          focusBackground: '{primary.100}',
          color: '{primary.800}',
          focusColor: '{primary.900}',
        },
        formField: {
          borderColor: roles.light.controlBorder,
          hoverBorderColor: '{surface.500}',
          color: roles.light.text,
          placeholderColor: '{surface.500}',
          floatLabelColor: '{surface.600}',
          iconColor: '{surface.500}',
        },
        text: {
          color: roles.light.text,
          hoverColor: roles.light.text,
          mutedColor: roles.light.textMuted,
          hoverMutedColor: '{surface.700}',
        },
        content: {
          background: roles.light.card,
          hoverBackground: '{surface.100}',
          borderColor: roles.light.border,
        },
      },
      dark: {
        surface,
        primary: {
          color: roles.dark.primary,
          contrastColor: roles.dark.onPrimary,
          hoverColor: roles.dark.primaryHover,
          activeColor: roles.dark.primaryActive,
        },
        formField: {
          background: roles.dark.ground,
          borderColor: roles.dark.controlBorder,
          hoverBorderColor: '{surface.400}',
          color: roles.dark.text,
          placeholderColor: '{surface.400}',
          iconColor: '{surface.400}',
        },
        text: {
          color: roles.dark.text,
          hoverColor: roles.dark.text,
          mutedColor: roles.dark.textMuted,
          hoverMutedColor: '{surface.300}',
        },
        content: {
          background: roles.dark.card,
          hoverBackground: '{surface.800}',
          borderColor: roles.dark.border,
        },
        overlay: {
          select: { background: roles.dark.card, borderColor: roles.dark.border },
          popover: { background: roles.dark.card, borderColor: roles.dark.border },
          modal: { background: roles.dark.card, borderColor: roles.dark.border },
        },
      },
    },
  },
})
