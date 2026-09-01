# Page-specific design overrides

Files here override `../MASTER.md` for a single page/surface only.

Naming: `<page-slug>.md` (e.g. `lead-scanner.md`, `dodong-assistant.md`,
`lead-detail.md`).

Retrieval order for any UI task:

1. Read `design-system/dodong-os/MASTER.md`.
2. If `design-system/dodong-os/pages/<page-slug>.md` exists, its rules take
   precedence for that page.
3. Otherwise use MASTER exclusively.

Only create an override when a page genuinely needs to deviate; keep the
deviation minimal and state *why*. MASTER already covers Lead Scanner, CRM,
Dodong Assistant, Knowledge Assistant, Automation, Action Audit and the
controlled-write confirmation pattern inline (§21–§27), so most pages need no
file here.
