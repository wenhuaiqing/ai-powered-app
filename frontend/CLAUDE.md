# Frontend conventions

React 18.3 + Vite 5 + React Router 7. Reapit-themed.

## Layout

```
frontend/
├── package.json
├── vite.config.js
├── index.html
└── src/
    ├── main.jsx                       Entry: ThemeProvider + BrowserRouter + App
    ├── App.jsx                        Sidebar + Header + <Routes> + <UnifiedOrb>
    ├── navigation.js                  Auto-discovers pages via import.meta.glob
    ├── config.js                      API_BASE_URL
    ├── context/ThemeContext.jsx       Purple/teal palette + dark mode
    ├── components/
    │   ├── common/
    │   │   ├── HeaderBar.jsx
    │   │   ├── SidebarNav.jsx
    │   │   ├── PlasmaOrb.jsx          Lifted from mcnab-data-app, re-skinned
    │   │   ├── UnifiedOrb.jsx         Streaming agent UI (SSE)
    │   │   └── PagePlaceholder.jsx
    │   └── agents/
    │       ├── AgentTrace.jsx         Renders the streamed SSE timeline
    │       ├── ToolCallCard.jsx
    │       └── AgentBadge.jsx
    └── pages/<Section>/<Page>.jsx     One file per route, auto-discovered
```

## Patterns

- **Auto-discovery** — `pages/<Section>/<Page>.jsx` becomes the URL `/<section-slug>`.
  `Home/Dashboard.jsx` is the index ("/"). The sidebar comes from `navigation.js`
  which maps each section to an icon + display order.
- **Theme tokens** — every styled element reads from `useTheme().t`. Primary
  `t.accent` is Reapit indigo `#4E56EA` (the CTA / button / arrow colour
  used on reapit.com.au); `t.accent2` is teal `#0BAAB2` (a darkened sibling
  of the logomark's `#98C1C2`) for AI badges and the second gradient stop.
  `t.dot.red` is the brand red `#D1263D` and `t.dot.yellow` is the brand
  orange `#FD9E1D`. The slate `#4A5A6B` is only inside the logo SVG itself.
- **Inline styles** — matches mcnab-data-app's pattern. No CSS-in-JS dep.
- **Icons** — `lucide-react`. Property-native: Building2, Users, Calculator,
  Scale, LineChart, Home.
- **Pill CTAs** — `borderRadius: 999`. Cards: 10-14px.
- **SSE streaming** — `UnifiedOrb` reads `/orb/chat` using `fetch` +
  `ReadableStream` + manual SSE parsing. No EventSource (it can't POST).
- **Agent trace** — tool_result events are merged into the preceding tool_call
  card so each tool call shows as one block with the result preview attached.
- **No frontend tests yet** — the backend Tier-1 suite is the safety net for
  Phase 1.

## Run

```powershell
npm install
npm run dev    # :5173 with Vite proxy -> backend :8000
```
