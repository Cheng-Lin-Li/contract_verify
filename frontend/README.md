# contract_verify — Frontend

React + TypeScript + Tailwind single-page app for the 3-month scope: **upload a
contract, view the unified verification report, and work the attorney queue**,
with **English + Japanese** localization. It talks to the FastAPI backend
(`backend/app/api`) over the HTTP contract defined in `src/types.ts`
(mirrors `backend/app/api/schemas.py`).

> The backend API is currently a **skeleton** (handlers raise
> `NotImplementedError`). The frontend is fully implemented against the contract;
> point it at a running API once the 3-month endpoints are built.

## Prerequisites

- Node.js 18+ and npm.

## Install & run (dev)

```bash
cd frontend
npm install
cp .env.example .env          # set VITE_API_URL if the API isn't on :8000
npm run dev                   # http://localhost:5173  (proxies /api -> backend)
```

The Vite dev server proxies `/api` to `VITE_API_URL` (default
`http://localhost:8000`), so the SPA and API share an origin in development.

## Test

```bash
npm test                      # Vitest + Testing Library (jsdom)
```

Component tests live in `src/test/` (ScoreCards, ResultsTable, GateBanner) plus a
client token-storage test.

## Build

```bash
npm run build                 # type-check + production bundle in dist/
npm run preview
```

## Structure

```
frontend/src/
├─ api/client.ts        # typed axios client; one method per endpoint
├─ auth/AuthContext.tsx # current user, login/logout, role helpers
├─ components/          # Layout, ScoreCards, ResultsTable, GateBanner,
│                       #   QueueList, StatusBadge, LanguageSwitcher, ProtectedRoute
├─ hooks/               # useReport, useJobPolling, useQueue
├─ i18n/ + locales/     # i18next config + en.json / ja.json
├─ pages/               # Login, Upload, Report, Queue
├─ types.ts             # mirrors backend/app/api/schemas.py
└─ test/                # Vitest setup + component/client tests
```

## Localization

English and Japanese ship in `src/locales/`. The language switch (top-right)
persists to `localStorage`; add a locale by dropping in `src/locales/<lang>.json`
and registering it in `src/i18n/index.ts`.
