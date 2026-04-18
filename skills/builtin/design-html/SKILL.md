---
name: design-html
source: adapted from gstack (MIT License)
trigger: auto+manual
version: 1.0.0
description: "Generate production-ready HTML from design descriptions or mockups. Creates semantic, accessible, responsive HTML/CSS. Use when asked to 'build this page', 'create the HTML', 'convert this design to HTML', 'make this page', 'generate HTML', 'create a landing page', 'build the UI', 'write the HTML for this', 'code this design', 'create a responsive page', or 'HTML from mockup'."
---

# design-html: Generate Production-Ready HTML

Create well-structured, accessible, responsive HTML/CSS from design descriptions or mockups.

## Step 1: Design Input

Determine what design context exists:

1. **Design mockup available:** Read the image/PNG reference
2. **DESIGN.md exists:** Read design tokens (colors, fonts, spacing)
3. **Plan file exists:** Extract UI requirements from the plan
4. **No design context:** Ask the user to describe what they want

Gather:
- Purpose and audience
- Visual feel (dark/light, playful/serious, dense/spacious)
- Content structure (hero, features, pricing, etc.)
- Any reference sites they like

## Step 2: Implementation Spec

Extract or define:
- **Colors:** Primary, secondary, background, text (hex values)
- **Typography:** Font family, sizes for h1-h6, body, captions
- **Spacing scale:** 4px, 8px, 16px, 24px, 32px, 48px
- **Components:** List of all components needed
- **Layout type:** Single column, two-column, grid, flexbox

Output the spec summary before generating.

## Step 3: Generate HTML

Generate production-ready HTML with these requirements:

1. **Semantic HTML:** Use `<header>`, `<main>`, `<nav>`, `<section>`, `<article>`, `<footer>`
2. **Accessibility:**
   - All images have alt text
   - All forms have labels
   - Proper heading hierarchy (h1 → h2 → h3)
   - ARIA attributes where needed
   - Keyboard navigable
3. **Responsive:**
   - Mobile-first CSS
   - Breakpoints at 768px and 1024px
   - Flexible layouts (flexbox/grid)
4. **Performance:**
   - No external dependencies unless necessary
   - Inline critical CSS
   - Optimized images (WebP with fallbacks)
5. **Content:** Use realistic content, not lorem ipsum

## Step 4: Preview

Save to a temporary HTML file and open in browser (or show the code for review).

## Step 5: Refinement Loop

Ask the user: "How does it look? Want to adjust anything?"

Iterate on:
- Layout tweaks
- Color adjustments
- Typography changes
- Content updates
- Responsive behavior

## Step 6: Save

Save the final HTML to the appropriate location:
- `public/index.html` for a landing page
- `templates/` for a template
- `src/components/` for a component

---

## Important Rules

- **Realistic content.** Never use lorem ipsum. Generate content appropriate for the context.
- **Accessible by default.** Every page must work with keyboard and screen reader.
- **Responsive by default.** Mobile-first, then enhance for larger screens.
- **Semantic markup.** Use the right HTML element for the right purpose.
- **No dependencies unless needed.** Prefer vanilla HTML/CSS over framework overhead.

---

## Completion Status

- **DONE** — HTML generated and saved
- **DONE_WITH_CONCERNS** — HTML created but some design aspects could not be fully realized
