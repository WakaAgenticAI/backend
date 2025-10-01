Here’s a **frontend-focused PRD** for **WakaAgent AI — Agentic AI-powered Distribution Management System (ADMS)**, aligned tightly to the modules, stack, and non-functional requirements in your brief (React, Material UI, Redux, MediaRecorder; real-time chat; order tracking; CRM; inventory with AI forecasts; finance & fraud; support; RBAC; accessibility; secure comms; page-load < 3s). &#x20;

---

# 1) Product Summary & Goals (Frontend)

**Goal:** Deliver a responsive, secure, easy-to-use web app enabling non-technical staff to manage orders, customers, inventory (with AI forecasts), finance (incl. fraud alerts), and support, plus a **real-time, multilingual chatbot with voice notes and memory**. Page loads must feel fast (<3s) and work across devices.&#x20;

**Why front-end matters:** It is the control surface over multiple cooperating agents (Order, CRM, Finance, Inventory Forecast, Chatbot) and presents real-time analytics and tracking.&#x20;

**Primary KPIs visible on UI:** Orders/deliveries today, sales, forecasted stockouts, fraud alerts, ticket SLAs.&#x20;

---

# 2) Scope & Non-Functional Requirements

* **Platforms:** Modern Chrome/Edge/Safari/Firefox (last 2 versions); responsive for mobile, tablet, desktop.&#x20;
* **Performance budgets:** FCP ≤ 1.8s, TTI ≤ 3.0s on 4G mid-tier; route chunks ≤ 200KB; images lazy-loaded. **Overall page load < 3s target.**&#x20;
* **Security/compliance:** HTTPS, JWT handling, XSS protections, WCAG accessibility (AA).&#x20;
* **Reliability:** Socket events render within ≤1s; optimistic updates for common operations (order status, ticket replies).

---

# 3) Target Frontend Stack

* **Framework:** React (TypeScript). **UI kit:** Material UI. **State:** Redux Toolkit (+ RTK Query/Thunk). **Realtime:** Socket.IO client. **Media:** MediaRecorder API for voice notes. **Charts:** Recharts. **Forms:** React Hook Form + Zod. **Tables:** TanStack Table. **i18n:** i18next. **Build:** Vite or Next.js (recommended: Next.js for SSR/SEO & edge caching).&#x20;

---

# 4) Information Architecture & Navigation

**Top-level nav:**

1. **Dashboard** — KPIs, alerts, quick actions.&#x20;
2. **Chat** — chatbot + live agent console (text/voice).&#x20;
3. **Orders** — list, create, detail, live tracking.&#x20;
4. **CRM** — customers, profiles, messages/purchase history.&#x20;
5. **Inventory** — products, stock, **AI forecasts**, reorder alerts.&#x20;
6. **Finance** — sales, P\&L, cashflow, **fraud** queue.&#x20;
7. **Support** — tickets, SLAs, chat escalations.&#x20;
8. **Admin** — users, roles (Admin, Sales, Ops, Finance), settings.&#x20;

**Global elements:** Search, notifications/toast center, language switcher (EN/Naija Pidgin + extensible Hausa/Yoruba/Igbo), profile menu, network status indicator.&#x20;

---

# 5) Key Screens & UX Specifications

## 5.1 Dashboard

* **KPI cards:** Orders today, Deliveries in-transit, Sales today, Cashflow delta, Fraud alerts, Reorder alerts. **Real-time updates** via Socket.IO.&#x20;
* **Charts:** Sales trend (area), Inventory health (bar), Forecasted stockouts (table + sparkline).
* **Alert center:** fraud, stock replenishment due; click-through deep links.

## 5.2 Chat (Agent + Bot)

* **Input modes:** text, **voice (record or upload m4a/webm)** → waveform preview → send → show transcript + bot reply; retry & cancel. **MediaRecorder** required.&#x20;
* **Memory cues:** “I remember your last order…” label when RAG is used.
* **Tool actions:** Inline suggestions (Create order / Check stock / Open ticket).
* **Escalation:** “Talk to human” opens Support ticket and joins agent thread.&#x20;

## 5.3 Orders

* **List:** Filters (status, channel, date, risk), quick actions (mark fulfilled, refund).
* **Create order wizard:** Customer → Items (SKU search, qty, pricing) → Summary → Submit.
* **Detail:** Timeline (created/paid/fulfilled), items, payments, shipment tracking, risk flags; **live status** updates.&#x20;

## 5.4 CRM

* **Customer profile:** Contact info, segment, lifetime value, last seen, addresses, purchases, chat threads.
* **Interactions tab:** message history (incl. voice notes) playable inline.&#x20;

## 5.5 Inventory

* **Products list:** On hand, reserved, reorder point; **alerts** pinned above the fold.
* **Forecasts view:** 7/30-day demand with MAPE badge; “Create PO” CTA when under threshold. **AI forecast displayed.**&#x20;

## 5.6 Finance

* **Reports:** Sales/P\&L/Cashflow with date presets; “Generate” triggers async job; shows last run and download links.
* **Fraud review:** sortable queue with score + rules triggered; approve/hold/deny.&#x20;

## 5.7 Support

* **Tickets list:** status/priority/SLA countdown.
* **Ticket detail:** chat-style thread; link to originating chat session; canned replies.&#x20;

## 5.8 Admin

* **Users & Roles:** assign Admin/Sales/Ops/Finance; audit login devices; rotate API keys. **RBAC.**&#x20;

**UX states to design for:** loading (skeletons), empty, error (retry), disabled (RBAC), offline (retry queue), long lists (virtualize).

---

# 6) Component Architecture

* **Design tokens:** spacing, radius, typography scale, shadows; light/dark palette supporting WCAG AA contrasts.&#x20;
* **Atoms:** Buttons, Inputs, Selects, Badges, Avatars, Tooltip, Toast, Modal, Tabs.
* **Molecules:** KPI Card, Inline Alert, DataTable, ChartCard, FileDropzone, AudioRecorder, AudioPlayer, Timeline.
* **Organisms:** ChatConsole, OrderWizard, OrderDetailPanel, CustomerProfile, ForecastPanel, FraudQueue, TicketThread.
* **Layouts:** AppShell (topbar + left nav), AuthLayout.

**Specialized components:**

* `AudioRecorder` (MediaRecorder) with 60s limit, VU meter, re-record.&#x20;
* `SocketIndicator` showing real-time connection status.
* `RBACGuard` to hide/disable restricted actions.&#x20;

---

# 7) Data Flow & State Management

* **Redux Toolkit slices:** `auth`, `ui`, `notifications`, `i18n`, and feature slices (`orders`, `crm`, `inventory`, `finance`, `support`, `chat`).&#x20;
* **Server cache:** RTK Query endpoints or React Query alternative.
* **Sockets:** a dedicated `useSocket` hook dispatching slice actions on events (e.g., `ORDER_UPDATED`, `FORECAST_READY`, `FRAUD_ALERT`, `TICKET_CREATED`).
* **Optimistic updates:** order status transitions, ticket replies; rollback on failure.

---

# 8) API Integration Contracts (Frontend expectations)

* **Auth:** JWT in secure storage; refresh flow; 401 interceptor → reauth. **JWT per brief.**&#x20;
* **Chat:** `POST /chat/sessions/{id}/messages` supports text or audio; progress UI while Whisper transcribes; show transcript and LLM response; Socket stream for tokens if available.&#x20;
* **Orders/Inventory/Forecasts/Finance/Support:** paginated lists; detail endpoints; report generation returns `report_id` and later `file_url`. **Matches listed modules.**&#x20;

---

# 9) Internationalization & Locale

* **Languages:** English + Naija Pidgin (baseline); architecture ready for Hausa/Yoruba/Igbo. **Multilingual requirement.**&#x20;
* **Locale formatting:** NGN currency, 24-hour time; right-to-left not required initially.
* **Content model:** message keys with pluralization; translation JSON per module.

---

# 10) Accessibility

* **WCAG AA:** focus outlines, ARIA roles, keyboard shortcuts for power users, screen-reader labels for charts and audio controls. **Accessibility is a stated need.**&#x20;
* **Color contrast:** ensure ≥ 4.5:1 for text; test dark mode.
* **Motion:** respect `prefers-reduced-motion`.

---

# 11) Security (Front-end responsibilities)

* **Transport:** enforce HTTPS; mixed-content blocked. **Per brief.**&#x20;
* **Auth storage:** short-lived access token in memory; refresh in httpOnly cookie or secure storage with rotation; CSRF mitigations for cookie flows.
* **XSS/Injection:** escape user content; sanitize HTML if ever rendered; strict CSP; file upload type/size checks before send. **XSS mitigation is required.**&#x20;

---

# 12) Telemetry & Observability (Client)

* **UX metrics:** route TTI, API error rates, socket reconnects, chat STT latency.
* **Event analytics:** feature usage (voice vs text), conversion from chat → order, fraud triage throughput, support SLA breaches.

---

# 13) Testing Strategy

* **Unit:** components, reducers, hooks (Jest + RTL).
* **Integration:** API hooks with MSW; socket event simulations.
* **E2E:** Playwright (auth, chat flow with audio, create order, forecast view, report download, ticket escalation).
* **Accessibility tests:** axe-core CI gate.
* **Visual regression:** Playwright snapshots for critical pages.

---

# 14) Environments, Config & Deployment

* **ENV vars:**

  ```
  VITE_API_BASE_URL=
  VITE_SOCKET_URL=
  VITE_BUILD_ENV=dev|staging|prod
  VITE_FEATURE_VOICE_CHAT=true
  VITE_DEFAULT_LOCALE=en
  ```
* **CDN & hosting:** Next.js on Vercel (recommended) or static on Netlify with SSR fallback via serverless.
* **Caching:** HTTP caching for static; SWR/RTK Query for data; prefetch adjacent routes.
* **Feature flags:** voice chat, fraud tab, forecast tab (gradual rollouts).

---

# 15) Step-by-Step Implementation Plan

### Sprint 0 — Foundations (Days 1–3)

* Create repo; add lint/format/test; scaffold Next.js (or Vite) + TS + MUI + Redux Toolkit.
* AppShell with protected routes; theme tokens; light/dark mode; i18n skeleton.
* Auth wiring (login screen, token handling, role-based route guards). **RBAC from brief.**&#x20;

### Sprint 1 — Dashboard & Sockets (Days 4–7)

* KPI cards + placeholder charts; connect Socket.IO client; global `SocketIndicator`.
* Notifications center for `FRAUD_ALERT`, `FORECAST_READY`, `TICKET_CREATED`.&#x20;

### Sprint 2 — Chat (Text & Voice) (Week 2)

* Build `AudioRecorder` + `AudioPlayer`; upload to backend; progress & transcript states.
* Chat thread UI with system/user/bot roles; tool suggestions (Create order / Check stock).
* Escalation button → creates ticket and deep-links to Support. **Voice + multilingual chat.**&#x20;

### Sprint 3 — Orders (Week 3)

* Orders list with filters; Order wizard; Order detail with live timeline and tracking.
* Optimistic updates for status changes; error rollback.

### Sprint 4 — CRM (Week 4)

* Customer list & profile; interactions history (incl. voice notes playback).
* Link chat sessions to customers; quick actions: call, message, create order.&#x20;

### Sprint 5 — Inventory & Forecasts (Week 5)

* Product & stock pages; Alerts ribbon; Forecast panel with charts and MAPE.
* “Create PO” or “Set reorder point” actions from forecast insights. **AI forecasting UI.**&#x20;

### Sprint 6 — Finance & Fraud (Week 6)

* Reports generator UI (sales/P\&L/cashflow) with history and downloads.
* Fraud review queue: table, detail drawer, approve/hold/deny. **Fraud module.**&#x20;

### Sprint 7 — Support & Admin (Week 7)

* Tickets list/detail with SLA timers; canned replies; link back to originating chat.
* Admin: users/roles; feature flags; audit feed. **Support & RBAC.**&#x20;

### Sprint 8 — Hardening (Week 8)

* A11y pass, i18n completion, performance tuning; PWA (install + offline shell optional).
* E2E + visual regressions; smoke tests for sockets & audio paths.
* Release checklist; canary rollout.

---

# 16) Acceptance Criteria (per module)

* **Dashboard:** Real-time KPIs and alerts update without refresh; charts render < 1s after data resolve.&#x20;
* **Chat:** Users can record/upload voice, see transcript + response, perform tool actions, and escalate to Support. Multilingual copy switch works.&#x20;
* **Orders:** Users can create, filter, and track orders live; status changes propagate via sockets.&#x20;
* **CRM:** Profiles show messages/purchases; voice notes play inline.&#x20;
* **Inventory:** Forecasts display with error metric and alerting; reorder actions available.&#x20;
* **Finance:** Users can generate and download Sales/P\&L/Cashflow; fraud queue decisions persist.&#x20;
* **Support:** Ticket lifecycle visible; SLA countdown accurate; escalation from chat creates linked ticket.&#x20;
* **Admin/RBAC:** Role restrictions enforced at route and component level.&#x20;
* **NFRs:** Load <3s on 4G mid-tier; keyboard navigation throughout; no obvious XSS vectors.&#x20;

---

# 17) Risks & Mitigations

* **Voice upload size/latency:** cap duration; compress; show progress; background transcript polling.&#x20;
* **Realtime overload:** debounce UI updates; batch socket events; use virtualization for long lists.
* **Multilingual UX quality:** externalized strings + review loop; fallback to English per key.
* **Accessibility drift:** automated axe checks + manual screen-reader tests each sprint.

---

# 18) Open Questions

* Should Dashboard KPIs be user-customizable (drag/drop, save layouts)?
* Do we need PWA install for field agents (offline order capture)?
* Required locales at launch beyond English/Naija Pidgin?

---

If you’d like, I can scaffold a **Next.js + MUI + Redux Toolkit** project (with socket hook, audio recorder, protected routes, and a couple of example pages) so your team can start building against this PRD immediately.
