---
name: Warm Minimalism
colors:
  surface: '#fbf8ff'
  surface-dim: '#dad9e3'
  surface-bright: '#fbf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f2fd'
  surface-container: '#eeedf7'
  surface-container-high: '#e8e7f1'
  surface-container-highest: '#e3e1ec'
  on-surface: '#1a1b22'
  on-surface-variant: '#3e484e'
  inverse-surface: '#2f3038'
  inverse-on-surface: '#f1effa'
  outline: '#6e797e'
  outline-variant: '#bdc8ce'
  surface-tint: '#006782'
  primary: '#006782'
  on-primary: '#ffffff'
  primary-container: '#14a0c8'
  on-primary-container: '#003140'
  inverse-primary: '#63d4fe'
  secondary: '#5d5f5f'
  on-secondary: '#ffffff'
  secondary-container: '#dfe0e0'
  on-secondary-container: '#616363'
  tertiary: '#5d5f5f'
  on-tertiary: '#ffffff'
  tertiary-container: '#939494'
  on-tertiary-container: '#2b2d2d'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#bbe9ff'
  primary-fixed-dim: '#63d4fe'
  on-primary-fixed: '#001f29'
  on-primary-fixed-variant: '#004d63'
  secondary-fixed: '#e2e2e2'
  secondary-fixed-dim: '#c6c6c7'
  on-secondary-fixed: '#1a1c1c'
  on-secondary-fixed-variant: '#454747'
  tertiary-fixed: '#e2e2e2'
  tertiary-fixed-dim: '#c6c6c7'
  on-tertiary-fixed: '#1a1c1c'
  on-tertiary-fixed-variant: '#454747'
  background: '#fbf8ff'
  on-background: '#1a1b22'
  surface-variant: '#e3e1ec'
typography:
  display:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  h1:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  h2:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  h3:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: '0'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: '0'
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1'
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  xxl: 64px
  container-max: 1280px
  gutter: 24px
---

## Brand & Style

This design system is built on the philosophy of **Warm Minimalism**. It moves away from the cold, clinical tech aesthetics of the past toward an environment that feels approachable yet highly disciplined. The target audience consists of power users and professionals who require a high-density, productive interface that doesn't sacrifice emotional comfort.

The visual language balances breathable whitespace with high-end editorial precision. By utilizing a soft neutral foundation paired with a vibrant, intelligent accent, the UI evokes a sense of "calm competence." It is designed to feel like a premium physical workspace—clean, organized, and tactfully illuminated.

## Colors

The palette transitions the interface from a cold blue-grey to a sophisticated, warm neutral foundation. 

- **Foundation:** The primary background uses a soft off-white (#fafafa), providing a warm, non-glare canvas that reduces eye strain.
- **Surfaces:** Interactive containers and content cards use a pure white (#ffffff) to create "islands of focus."
- **Accents:** "AI Blue" (#14a0c8) is reserved for meaningful interaction points, including primary action buttons, active state indicators, and model-specific metadata tags.
- **Hierarchy:** Subtle borders (#e5e7eb) replace heavy fills to define structure, ensuring the interface remains light and airy while maintaining clear information architecture.

## Typography

This design system leverages **Inter** exclusively for its utilitarian precision and exceptional legibility at small sizes. 

To achieve a "professional yet warm" feel, the system uses refined weights rather than heavy bolding. Headlines utilize Semi-Bold (600) with tighter letter spacing for a premium, editorial look. Body text prioritizes readability with a generous 1.5x to 1.6x line height. For metadata and labels, Medium (500) and Semi-Bold (600) weights are used at smaller scales to maintain clarity without overwhelming the visual field.

## Layout & Spacing

The layout philosophy follows a **fixed-grid system** for complex dashboards and a **centered-column approach** for focused reading experiences. 

A strict 4px base unit ensures mathematical harmony across all components. Content should be grouped into logical "surface containers" with 24px of internal padding. Between major sections, use 40px (xl) or 64px (xxl) to enforce the "Minimalist" aesthetic, allowing the user's eyes to rest. Navigation and sidebars should occupy fixed widths, while the primary content area expands to a maximum of 1280px to maintain line-length integrity.

## Elevation & Depth

Depth in this design system is communicated through **low-contrast outlines** and **tonal layering** rather than traditional shadows. 

The background level (#fafafa) sits at the lowest elevation. Interactive cards and containers (#ffffff) are elevated visually by a 1px border (#e5e7eb). For hover states or modals, use a "soft-focus" shadow—extremely diffused, using a 10-15% opacity of a warm neutral rather than pure black. This prevents the "floating" clinical look and keeps the UI feeling grounded and tactile.

## Shapes

The shape language is defined as **Soft (Level 1)**. 

Standard components (buttons, input fields, tags) utilize a 0.25rem (4px) radius. Larger containers like cards use a 0.5rem (8px) radius. This subtle rounding avoids the harshness of sharp corners while steering clear of the overly "bubbly" or "playful" appearance of high-radius systems. The result is a crisp, architectural silhouette that feels modern and professional.

## Components

- **Buttons:** Primary actions utilize the AI Blue (#14a0c8) with white text. Secondary actions use the white surface with the standard #e5e7eb border. Use a Medium weight for button labels to ensure they stand out.
- **Model Tags & Status Dots:** Use AI Blue for active AI processes. Status dots should be small (8px) and accompanied by label-sm typography.
- **Input Fields:** Use a white fill with a 1px border (#e5e7eb). On focus, the border transitions to AI Blue with a subtle 2px outer glow of the same color at 10% opacity.
- **Cards:** White backgrounds, subtle grey borders, and no default shadow. Content within cards should follow the 24px internal padding rule.
- **Chips:** Used for filtering or categories; they should feature a light grey stroke and a transparent background, becoming AI Blue with white text only when selected.
- **Refinement Rails:** Vertical sidebars should use the background color (#fafafa) to visually recede, allowing the primary white workspace to take center stage.