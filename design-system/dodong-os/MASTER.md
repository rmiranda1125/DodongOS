# Dodong OS — Design System (MASTER)

> Canonical, permanent visual system for **Dodong OS**. Any Claude session doing
> UI/UX work reads this file **first**, then checks
> `design-system/dodong-os/pages/<page>.md` for page-specific overrides.
>
> Enforcement rules live in the `dodong-ui` skill (`.claude/skills/dodong-ui/SKILL.md`).
> Design intelligence source: `ui-ux-pro-max` skill (`--design-system`,
> variance 4 / motion 2 / density 8). Where those two conflict, **this file and
> the repository architecture win.**

---

## 0. Status

- Version: 1.0 (established before the UI implementation pass)
- Stack (mandatory, do not change): **Django Templates + HTMX + Bootstrap 5.3 + minimal vanilla JS**. Alpine.js only for tiny local UI state Bootstrap/HTMX cannot do cleanly. No Tailwind / React / Vue / Angular / SPA / Node build tooling for UI.
- Token file: `backend/static/css/dodong.css` (this document is its specification / source of truth).
- Not yet applied system-wide — this file defines the target; the implementation pass follows.

---

## 1. Product design principles

Dodong OS is an **internal business operations console** = CRM + AI assistant +
lead-sourcing workspace. Desktop-heavy, with usable tablet/mobile.

Character: **professional, calm, trustworthy, modern, compact, data-oriented, operational.**

| Do | Don't |
|---|---|
| Flat, 2D surfaces; hairline borders; at most one soft shadow tier | Gradients, glassmorphism, 3D, neumorphism, heavy shadows |
| Strong information hierarchy via size / weight / spacing | Rainbow status colors; color as the only signal |
| Medium-high density; screens that fit without needless scrolling | Marketing-hero sections, oversized headings, spacious SaaS cards |
| Bootstrap Icons, used to reinforce meaning | Emoji as structural/navigation icons |
| Motion only for feedback / state change / loading (120–180ms) | Decorative or continuous motion, parallax, GSAP, page-entrance choreography |
| A card exists only when it groups a distinct information unit | Nested cards, a card per paragraph |

**Design dials:** variance **4/10** (balanced-modern; no brutalism/bento),
motion **2/10** (subtle), density **8/10** (dense/dashboard).

A UI change is acceptable only if it improves comprehension, task completion,
scanning speed, error prevention, confidence, accessibility, responsive
usability, or visual consistency — **without degrading behavior or safety.**

---

## 2. Color tokens

Style: **Flat Design**. Palette: professional blue + deal green on near-white
surfaces with a dark sidebar. Light theme is canonical; a dark theme is a
future, out-of-scope addition (scaffolding via `data-bs-theme` is allowed).

Defined once on `:root` in `dodong.css`. Prefer the semantic `--dodong-*`
token; never put a raw hex in a template.

| Token | Value | Role | Contrast note |
|---|---|---|---|
| `--dodong-bg` | `#f4f6f9` | app background (soft gray) | — |
| `--dodong-surface` | `#ffffff` | cards, panels, tables | — |
| `--dodong-surface-alt` | `#fafbfc` | card headers, table head, subtle fills | — |
| `--dodong-border` | `#e4e7ec` | hairline borders, dividers | visible on both surface and bg |
| `--dodong-fg` | `#0f172a` | primary text | ~17:1 on white ✓ AAA |
| `--dodong-muted` | `#475569` | metadata, helper, secondary | ~7.5:1 on white ✓ AAA — **not** `#999` |
| `--dodong-accent` | `#2563eb` | primary actions, links, active nav, focus ring | white text on it ≈ 4.9:1 ✓ AA |
| `--dodong-accent-fg` | `#ffffff` | text/icon on accent | — |
| `--dodong-success` | `#198754` | won / completed / succeeded / imported / high | fill + white text (badge, large/bold); for **success text on white** use `--dodong-success-text` `#0f7a45` |
| `--dodong-warning` | `#b45309` | pending / running / new / reviewed / due-soon / AI fallback | text on white ≈ 4.6:1 ✓; badge uses amber fill w/ dark text |
| `--dodong-danger` | `#dc2626` | failed / overdue / rejected / lost / errors | text on white ≈ 4.5:1 ✓ AA |
| `--dodong-info` | `#0e7490` | contacted / qualified / proposal / in-progress / informational | text on white ≈ 4.7:1 ✓ |
| `--dodong-sidebar-bg` | `#1f2430` | left sidebar / offcanvas | white/`#cdd3df` text ✓ |
| `--dodong-sidebar-fg` | `#cdd3df` | sidebar link text | ≈ 9:1 on sidebar-bg ✓ |
| `--dodong-sidebar-fg-active` | `#ffffff` | active/hover sidebar link | — |

Bootstrap mapping: keep using `text-bg-success|danger|warning|info|secondary`
for badge fills (they already ship AA-adjacent). Override
`--bs-primary`, `--bs-link-color`, `--bs-border-color`,
`--bs-body-bg`, `--bs-body-color`, `--bs-table-hover-bg`,
`--bs-focus-ring-color` from the tokens above in `dodong.css` so Bootstrap
components inherit the system.

**Color is never the only signal.** Every status shows text; badges are
pill-shaped with a label; overdue/failed rows also carry an icon.

---

## 3. Typography

System fonts only — **no external font (Poppins/Open Sans) is loaded.** The
`ui-ux-pro-max` heading/body suggestion is honored as *mood* (modern,
professional, clean), not as a dependency.

```css
--dodong-font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, "Noto Sans", sans-serif;
--dodong-font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo,
                    Consolas, "Liberation Mono", monospace;
```

Scale (rem, base 16px → density-tightened):

| Role | Size | Weight | Line-height | Notes |
|---|---|---|---|---|
| Page title (`h1`, `.dodong-page-title`) | 1.5rem | 600 | 1.25 | one per page |
| Section title (`h2`) | 1.25rem | 600 | 1.3 | |
| Card title (`h3` / `.card-header`) | 1.05rem | 600 | 1.35 | |
| Body | 0.95rem (~15px) | 400 | 1.5 | tables/forms baseline; **never** below 0.85rem for meaningful text |
| Metadata / helper (`.text-meta`) | 0.85rem | 400 | 1.45 | `--dodong-muted`, never for critical info |
| Table head | 0.78rem | 600 | 1.2 | uppercase, `letter-spacing: .03em`, `--dodong-muted` |
| Numeric data columns | body size | 400 | — | `font-variant-numeric: tabular-nums` |

`letter-spacing: -0.01em` on headings. Use weight + spacing + hierarchy before
adding color. Long IDs / URLs: `overflow-wrap: anywhere` + `.dodong-truncate`
with full value in `title=`.

---

## 4. Spacing scale (density 8)

Tight, 4px-based. Use these, not ad-hoc values.

```css
--space-1: .25rem;  /*  4px  — icon gap, inline */
--space-2: .5rem;   /*  8px  — inside compact controls */
--space-3: .75rem;  /* 12px  — control padding, tight stacks */
--space-4: 1rem;    /* 16px  — between related components */
--space-5: 1.5rem;  /* 24px  — card padding, between sections */
--space-6: 2rem;    /* 32px  — between major page sections (max default) */
```

Bootstrap: prefer `g-2`/`g-3` grid gutters, `p-3`/`px-3 py-2` card bodies,
`mb-3` between components, `mb-4`/`mb-5` between sections. Avoid `p-5`, `my-5`,
`display-*`, `lead` on operational pages. Dense ≠ cramped — keep grouping clear.

---

## 5. Border, radius, shadow

```css
--dodong-radius: 10px;      /* cards, inputs, offcanvas, modal */
--dodong-radius-sm: 8px;    /* buttons, nav links, small controls */
--dodong-radius-pill: 999px;/* status badges only */
--dodong-border-width: 1px;
--dodong-shadow-sm: 0 1px 2px rgba(15,23,42,.06);   /* resting cards (optional) */
--dodong-shadow-md: 0 8px 24px rgba(15,23,42,.12);  /* modal / popover only */
```

- Cards: `1px solid var(--dodong-border)` + `--dodong-radius`. Shadow is
  optional and at most `--dodong-shadow-sm`. No `shadow-lg`.
- Exactly two shadow tiers exist (`sm` for raised surfaces, `md` for
  true overlays). Never invent shadow values in templates.
- Tables & list groups sit flat inside a bordered card — no per-row shadow.

---

## 6. Application shell

```
┌───────────────────────────────────────────────┐
│  Top bar: brand · (mobile menu) ······ user ▸ │   navbar, bg #1f2430
├──────────┬────────────────────────────────────┤
│ Sidebar  │  Main workspace                    │
│ (dark,   │  ┌ page header ────────────────┐   │
│ sticky,  │  │ title / desc / actions      │   │
│ 240px)   │  └─────────────────────────────┘   │
│ grouped  │  content (cards / tables / forms)  │
│ nav      │                                   │
│ version  │                                   │
└──────────┴────────────────────────────────────┘
```

- `.dodong-shell` = `display:flex; min-height:100vh`.
- `.dodong-sidebar` = fixed `--dodong-sidebar-width: 240px`, `position: sticky; top:0; height:100vh; overflow-y:auto`, `--dodong-sidebar-bg`. Hidden `< lg`.
- `.dodong-main` = `flex:1; min-width:0` (**critical** — lets wide tables scroll instead of pushing the page), padding `var(--space-5)` (`var(--space-4)` `< lg`).
- Mobile (`< lg`): sidebar replaced by a **Bootstrap `offcanvas-start`** opened by a hamburger (`bi-list`) in the top bar. Same `sidebar_nav.html` partial rendered in both. Keyboard-operable (Bootstrap default), usable at 375px.
- No horizontal page scroll anywhere except inside `.table-responsive`.

Templates: `templates/base.html` (shell), `templates/partials/topbar.html`,
`templates/partials/sidebar_nav.html`.

---

## 7. Navigation

Grouped, staff-aware. Render **only** links the current user may use — but
route authorization is enforced server-side regardless (hiding a link is never
a substitute for `@login_required` / `@staff_member_required`).

| Group | Items | Visible to |
|---|---|---|
| CRM | Home, Leads, Pipeline, Tasks & Activity | any authenticated user |
| AI | Dodong Assistant | any authenticated user |
| AI | Knowledge Assistant | staff |
| Growth | Lead Scanner | staff |
| Operations | Automation Runs, Action Audit | staff |
| Administration | Admin (Django) | staff |

- Group label: `.dodong-nav-group` — `0.68rem`, uppercase, `letter-spacing:.06em`, `#8a93a5`.
- Link: `.dodong-nav-link` — flex, `gap: var(--space-2)`, `bi` icon (`1rem`, `opacity:.85`) + label, `padding: .45rem .6rem`, `--dodong-radius-sm`.
- States: hover → `background: rgba(255,255,255,.05)`, text `--dodong-sidebar-fg-active`. **Active** (current page) → `background: rgba(255,255,255,.09)`, white, `font-weight:600`. Active detection by `request.path` prefix.
- Footer: `.dodong-sidebar-footer` — top border, `Dodong OS v{{ DODONG_VERSION }}`, `0.75rem`, `#8a93a5`.
- Icons: `people`, `kanban`, `check2-square`, `stars`, `journal-text`, `radar`, `arrow-repeat`, `shield-check`, `gear`, `house-door`.

---

## 8. Page header

One structure for every major page (`.dodong-page-header`):

```html
<div class="dodong-page-header">
  <div>
    <h1 class="dodong-page-title">Lead Scanner</h1>
    <p class="dodong-page-desc">Review discovered opportunities before importing them into the CRM.</p>
  </div>
  <div class="d-flex gap-2">
    <a class="btn btn-primary btn-sm">Run Scan</a>
    <a class="btn btn-outline-secondary btn-sm">Export CSV</a>
  </div>
</div>
```

- `display:flex; flex-wrap:wrap; gap: var(--space-3); justify-content:space-between; align-items:flex-start; margin-bottom: var(--space-5)`.
- Title = `h1`, description = one calm sentence in `--dodong-muted`.
- **One** primary action max; the rest are `btn-outline-secondary`. On `< sm` the action row wraps below the title full-width.
- No bespoke per-page header layouts.

---

## 9. Cards

- `.card` → `1px solid var(--dodong-border)`, `--dodong-radius`. Optional `--dodong-shadow-sm`.
- `.card-header` → `--dodong-surface-alt` bg, `1px` bottom border, `font-weight:600`, `1.05rem`.
- Body padding `var(--space-4)`–`var(--space-5)`; `.dodong-card-tight .card-body` → `1rem 1.15rem`.
- A card must group one distinct information unit. Do **not** nest cards; use `.card-header` + list-group / table / `<dl>` sections inside one card instead.

---

## 10. Tables

Operational collections (leads, tasks, scanner queue, automation runs, action
audit, scanner runs) are **tables**, not card grids.

- Always inside `.card` → `.table-responsive` → `.table.table-hover`.
- `<thead>` with real `<th>`; head style per §3 (uppercase, muted, `white-space:nowrap`).
- `td, th { vertical-align: middle }`. Numeric columns `text-end` + tabular-nums.
- Row hover: `--bs-table-hover-bg: #f6f8fb`.
- Long free text: wrap in `.dodong-truncate` (`max-width: 22rem; ellipsis`) with full text in `title=` — **never** truncate the stored value, only the display.
- Every table ends with a meaningful **action column** (right-aligned) and a proper empty state (§13).
- Bulk actions: allowed as a checkbox column + action bar **only** where the backend already supports it and it stays review-oriented. No bulk AI/CRM mutation.
- Card layout is reserved for items that genuinely need rich review (scanner candidate detail), not for lists.

---

## 11. Forms

- Every input has a **visible `<label for=…>`**. Placeholder is never the only label.
- Helper text (`.form-text`, `--dodong-muted`) when the format isn't obvious.
- Validation errors render **next to the field**, tied with `aria-describedby`; on multi-error submit, a focusable summary at the top links to each field.
- Required fields marked (`*` + `aria-required`).
- Group related inputs (`fieldset`/`legend` or a `.card` section). Split very long forms into progressive sections.
- Controls: `form-control form-control-sm` / `form-select form-select-sm` on dense filter bars; default size in primary create/edit forms. Min height 44px for the primary submit and any touch-critical control.
- Semantic `type=` (`email`, `tel`, `number`, `url`, `date`) and `autocomplete`.
- Filter bars: wrap controls in a `.card.dodong-card-tight` with `row g-2 align-items-end`; each control ≤ `col-md-3`; a `Filter` primary + `Reset` link. Only expose filters the backend supports.

---

## 12. Buttons

| Intent | Class | Use |
|---|---|---|
| Primary action (one per view) | `btn btn-primary` | Ask, Import to CRM, Confirm Action, Save |
| Secondary / navigation / cancel | `btn btn-outline-secondary` | Back, Cancel, Export, Mark reviewed |
| Destructive | `btn btn-outline-danger` (list) / `btn btn-danger` (confirmed destructive) | Reject, Delete |
| Low-emphasis choice | `btn btn-link` / `btn btn-sm btn-outline-*` | inline table actions, "Reset" |

- Size `btn-sm` in headers, tables, filter bars; default in main forms.
- Always give `hover`, `focus-visible`, `active`, `disabled` states (Bootstrap
  provides them — don't strip). Disabled = `disabled` attr + reduced opacity +
  no pointer.
- Icon-only buttons carry `aria-label` (and a `title`). Icon + text preferred.
- Never rename **Confirm Action** to ambiguous copy. Never auto-submit.

---

## 13. Badges & status

One helper: `templates/partials/status_badge.html` —
`{% include … with value=x kind="lead|task|scanner|qualification|automation|audit" %}`.

- Pill: `.badge.dodong-status` → `border-radius: var(--dodong-radius-pill)`, `font-weight:600`, `padding:.35em .6em`, always shows the **label text**.
- Semantic mapping (color + text, never color alone):

| Semantic | Statuses | Bootstrap fill |
|---|---|---|
| success | won, completed, succeeded, executed, imported, approved, qualification=high | `text-bg-success` |
| danger | lost, failed, rejected, overdue, urgent | `text-bg-danger` |
| warning | pending, running, new, reviewed, due-soon, qualification=medium, AI fallback | `text-bg-warning` |
| info | contacted, qualified, proposal, in_progress | `text-bg-info` |
| neutral | inactive, unknown, closed-informational, qualification=low | `text-bg-secondary` |

- Overdue tasks / failed runs also get a `bi` icon next to the badge.
- Scores: `.dodong-score` (1.5rem, 700) + qualification badge + a
  `.dodong-meter` bar for components. No chart library for this.

---

## 14. Empty states

Never a bare blank table. `.dodong-empty` (centered, `2.5rem 1rem`, muted, a
`bi` glyph on its own line).

| Surface | Copy | Optional next action |
|---|---|---|
| Lead Scanner queue | "No candidates match this view." | run `scan_leads` hint |
| Scanner runs | "No scans have run yet." | — |
| CRM leads | "No leads found." | link to Scanner / clear filters |
| Tasks | "No tasks found." | — |
| Knowledge | "No knowledge documents available." | link to admin |
| Automation | "No automation runs yet." | — |
| Action Audit | "No AI actions have been confirmed yet." | — |
| RAG no-match | "No matching knowledge was found." | — |

---

## 15. Error states

- Semantic Bootstrap `alert` placed **near the action** that caused it.
- Wording is user-facing and actionable: "The action could not be completed.",
  "AI is temporarily unavailable. Showing deterministic results.",
  "No matching knowledge was found."
- Keep useful structured error **codes** where they aid support
  (`NOTE_TOO_LONG`, `CRM_DUPLICATE`, `PROPOSAL_ALREADY_USED`) but never a raw
  traceback, API key, DB credential, env var, or exception repr.
- `role="alert"` / `aria-live` for dynamically inserted errors.

---

## 16. Loading states (HTMX)

- Every HTMX action that isn't instant shows feedback via `hx-indicator`
  targeting a `.dodong-working` span: spinner + text — "Asking Dodong…",
  "Searching knowledge…", "Importing candidate…", "Confirming action…".
- `hx-disabled-elt="find button"` (or the specific button) to block duplicate
  submits while a request is in flight.
- Prefer a lightweight inline indicator; skeletons only for >1s list loads.
- No custom loading framework.

---

## 17. Motion

Level **2/10**. CSS/Bootstrap transitions only, **120–180ms**, `ease` /
`ease-out`. Motion is allowed for: nav/offcanvas open-close, loading
indicators, hover/active/expand state changes, small feedback. **Not** for
page entrances, parallax, bouncing, continuous/decorative motion, or GSAP.
Always wrap non-essential motion in `@media (prefers-reduced-motion: reduce)`
and render the final state immediately.

---

## 18. Responsive behavior

Review every major layout at **375 / 768 / ≥992px**.

- `< lg` (992): sidebar → offcanvas; page-header actions wrap full-width;
  two-column review layouts (`col-lg-*`) stack to one column.
- Tables always scroll inside `.table-responsive`; the **page** never scrolls
  horizontally.
- Forms stack (`col-12` on `< md`); the primary submit stays reachable
  (sticky-safe — no fixed bar hides it).
- Proposal / import confirmation cards stay fully usable and their
  Confirm/Cancel buttons stay visible at 375px (full-width stacked).
- `min-h-100`/`min-vh-100` over `100vh` where full height is needed.

---

## 19. Accessibility (release requirement — higher priority than aesthetics)

- Contrast: body & meaningful text ≥ **4.5:1** (tokens in §2 verified);
  badge/large/bold & non-text UI ≥ 3:1.
- **Color is never the only signal** — pair with text + icon.
- Semantic headings, sequential (`h1` per page → `h2` → `h3`), no skips.
- Every input has a `<label for>`; every icon-only control an `aria-label` +
  `title`; decorative icons `aria-hidden="true"`.
- Real `<th>` + `<thead>` for tables; `scope` where columns/rows both head.
- Full keyboard operability; **visible focus** — `:focus-visible { outline:
  2px solid var(--dodong-accent); outline-offset: 1px }`. Never remove a focus
  ring without an equal visible replacement.
- Sticky topbar / offcanvas must not obscure the focused control
  (`scroll-padding-top`).
- Modals & multi-step flows have a clear Cancel/close (Esc + button).
- `prefers-reduced-motion` respected wherever motion is added.
- Live status changes announced as a complete phrase via one polite
  `aria-live`/`role="status"` region, without moving focus.

---

## 20. HTMX interaction patterns

- HTMX is the default interaction mechanism. Preserve Django CSRF (form
  `{% csrf_token %}` and/or `hx-headers` on `<body>`), server-side validation,
  real URLs, and existing service boundaries.
- Responses that update a region return a **partial template**
  (`app/partials/*.html`), never a full page fragment glued in JS.
- Targets: `hx-target` a stable `id`; `hx-swap="innerHTML"` for content
  regions, `outerHTML` for self-replacing rows.
- `hx-push-url="true"` for list filter/search so back/forward and deep links
  work.
- Do not mirror backend state in JS. Alpine only for local-only toggles
  (a collapsed panel, a disclosure) when Bootstrap can't.
- `htmx:afterSwap` may re-init Bootstrap widgets in the swapped fragment.

---

## 21. Lead Scanner patterns (high priority)

**Queue** (`/scanner/`) — compact table, scannable at a glance:

- Left column: `.dodong-score` number + qualification badge (stacked).
- Company (bold) + opportunity title (`.text-meta .dodong-truncate`) + top
  match reason (`text-success`, `bi-check2`, truncated).
- `source` (`<code>`), work arrangement, compensation, status badge.
- Right: `Review` (`btn-sm btn-outline-primary`).
- Filter bar: Status · Source · Qualification · Minimum score (compact,
  backend-supported only).
- Empty: "No candidates match this view." + `scan_leads` hint.
- High-score rows stand out via the score badge color, **not** row tinting.

**Candidate detail** (`/scanner/<id>/`) — two-column on `≥ lg`, stacks below:

- **Left = Candidate information:** company, opportunity, source + source link
  (`rel="nofollow noopener noreferrer" target="_blank"`), location, work
  arrangement, compensation, times-seen, dedup key; a "Why it matches" card
  with per-component `.dodong-meter` bars + reason list + the *non-authoritative*
  AI note; the original opportunity text (`white-space: pre-wrap`, **escaped** —
  never `|safe`).
- **Right = CRM import preview:** the exact candidate→Lead field mapping, the
  resulting status (`new`), and prominently:
  **`No CRM change has been made yet.`** (`alert-warning`).
  Actions, in emphasis order: `Import to CRM` (`btn-primary`, **not**
  danger-styled; `disabled` when an existing CRM duplicate is detected),
  `Mark reviewed` (`btn-outline-secondary`), `Reject` (`btn-outline-danger`,
  with an optional reason input).
- Discovery must never visually imply a CRM lead already exists.
- Score visualization = number + badge + Bootstrap-progress-style meters +
  reasons. **No chart library.**

---

## 22. CRM patterns

**Lead list** — optimize for scanning. Columns from data already cheap in the
service layer: company, contact, status badge, score/priority, owner (if
present), next task / due date (if present), latest activity date (if present).
No new expensive joins for decoration. Status via badge helper.

**Lead detail** — structured, not one long scroll. Sections (Bootstrap
cards/`<section>`; simple, not SPA tabs): **Overview · Tasks · Activity · Notes
· Actions.** Key actions stay visible. Controlled-write triggers use the
proposal pattern (§27), not inline mutation.

**Tasks** — due state + priority must be instantly readable. Visual order:
overdue/urgent → high → normal → completed. Badge + text + date + icon (not
red/green alone). Overdue noticeable but not alarming (danger badge + `bi`
icon, not a full red row).

---

## 23. Dodong Assistant patterns

- Header: **"Dodong Assistant"** — description "Ask about leads, tasks,
  activities, and pipeline."
- Input: one comfortable single-line/textarea input + a `btn-primary` **Ask**.
- Suggested-query chips (submit existing supported queries only, no new
  intents): Overdue tasks · Priority tasks · Pending tasks · Pipeline summary ·
  Find a lead. Chips are small `btn-outline-secondary`.
- Never surface internal tool names / registry / `write_executor` in user UI.
- Loading: `hx-indicator` "Dodong is checking your CRM…", `hx-disabled-elt`.
- Response (`partials/crm_assistant_response.html`) visually distinguishes:
  **Answer** (prose), **Supporting CRM data** (compact list/table),
  **Warning** (`alert-warning`, e.g. AI fallback), **Error** (`alert-danger`),
  **Proposed action** (→ §27). **Never** raw tool JSON in the normal UI;
  structured diagnostics only in an admin/debug context.

---

## 24. Knowledge Assistant patterns

- Show: Question · Answer · Sources/evidence · AI-fallback warning · no-match state.
- Evidence card (compact): **document title** · source type · short **escaped**
  excerpt. Retrieved content is **DATA** — rendered escaped, never as trusted
  HTML, never `|safe`; do not expose raw chunk internals.
- Fallback (`source == deterministic_fallback`): `alert-warning`
  "AI is temporarily unavailable. Showing retrieved evidence."
- No-match: `alert-info` "No matching knowledge was found."

---

## 25. Automation patterns (`/automation/runs/`)

- Table columns: Started · Status · Checks · Findings · Summary · Detail.
- Status badges: **Succeeded** (success) · **Failed** (danger) · **Running**
  (warning) · AI-fallback → keep the **run** badge **Succeeded** and add a
  small warning note: **"AI unavailable — deterministic summary used."**
- Never label the deterministic run itself failed when only the AI summary failed.
- Show `summary_text` (`white-space: pre-wrap`, capped width), `summary_error`
  as `.text-meta` when present, `error_message` in `text-danger`.
- Empty: "No automation runs yet."

---

## 26. Action Audit patterns (`/assistant/audit/`)

- Clean operational table: Time · Action · Status · Lead · Task · Proposal ID · Error.
- `Executed` / `Failed` badges.
- Proposal ID visually shortened (`…` after 8 chars) with the **full value in
  `title=`**. **Never** render a signed proposal token.
- Empty: "No AI actions have been confirmed yet."

---

## 27. Controlled-write confirmation pattern (safety-critical)

Every AI write proposal card (`partials/create_task_proposal.html`) shows:

1. Heading: **"Proposed CRM Action"**.
2. Action type · target lead/task · **current state** · **proposed change** —
   all four visible, none hidden or abbreviated away.
3. Prominent, unavoidable: **`No CRM change has been made yet.`**
   (`alert-warning`, near the buttons).
4. Buttons: **`Cancel`** (`btn-outline-secondary`) and
   **`Confirm Action`** (`btn-primary`). Confirm is never renamed to ambiguous
   copy; it is a real `POST` form carrying the signed proposal token +
   `{% csrf_token %}`.

Result card (`partials/create_task_result.html`):

- Success **only after** backend re-read verification:
  **"✓ Action completed"** + the actual persisted result + new state.
- Failure: **"Action was not completed"** + safe user-facing reason.
- Never show success optimistically.

UI must **not** weaken: authentication, `@staff_member_required` /
`@login_required`, CSRF, POST-only mutation, signed-proposal verification,
single-use replay protection, expiry, the AI↔ORM boundary, the scanner review
boundary, or the automation/RAG read-only boundary. A prettier UI is never a
reason to bypass a check.

---

## 28. Anti-patterns (reject on sight)

Purple/marketing gradients · glassmorphism · 3D / neumorphism · big hero
sections · `display-*` headings on operational pages · spacious SaaS cards ·
nested cards · rainbow/per-page status colors · color-only status · emoji as
structural icons · raw hex in templates · `< 0.85rem` meaningful text ·
gray-on-gray · decorative/continuous motion · GSAP · parallax · placeholder as
the only label · errors only at the top · removing focus rings · card grid for
a long dataset · raw tool JSON in user UI · exposing internal tool names or
proposal tokens · conversational "Yes" styled to look like Confirm ·
auto-submitting a confirmation · new expensive backend queries just for
dashboard decoration · Tailwind/React/SPA/Node build tooling.

---

## 29. Pre-delivery checklist (per UI change)

Visual: hierarchy clear · spacing on the §4 scale · typography per §3 ·
semantic tokens only · no arbitrary styles.
UX: one obvious primary action · destructive actions differentiated · loading
feedback · empty state · understandable errors.
A11y: labels · keyboard · visible focus · contrast · table semantics ·
meaningful control names · color not sole signal · reduced-motion.
Responsive: 375 / 768 / ≥992 · no catastrophic overflow · confirm/import
reachable.
Architecture: Django templates + HTMX + Bootstrap preserved · permissions
unchanged · no safety boundary weakened · **no migration** (UI work normally
produces none).
Tests: `python manage.py check` · focused view/nav/access tests ·
`python manage.py test` · `python manage.py makemigrations --check`.

Desired final impression: **"Dodong OS feels like a serious business
operations product."**
