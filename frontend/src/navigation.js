// Auto-discovers pages under src/pages/<Section>/<Page>.jsx. Filename becomes
// the URL slug and the sidebar label. Lifted from mcnab-data-app and trimmed
// for the 6-route demo.

import { Building2, Calculator, Home, LineChart, ScaleIcon, Users } from "lucide-react";

const PAGE_MODULES = import.meta.glob("./pages/*/*.jsx", { eager: true });

// Icon + display order per module. Order in this object drives the sidebar.
export const MODULE_META = {
  Home:        { label: "Dashboard",       icon: Home,        order: 0 },
  Properties:  { label: "Properties",      icon: Building2,   order: 1 },
  Pipeline:    { label: "Pipeline",        icon: Users,       order: 2 },
  Valuations:  { label: "Valuations",      icon: Calculator,  order: 3 },
  Compliance:  { label: "Compliance Hub",  icon: ScaleIcon,   order: 4 },
  Insights:    { label: "Market Insights", icon: LineChart,   order: 5 },
};

function slugify(value) {
  return value
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function titleFromName(name) {
  return name
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .trim();
}

export function getRoutes() {
  const routes = [];
  for (const [path, module] of Object.entries(PAGE_MODULES)) {
    const match = path.match(/^\.\/pages\/([^/]+)\/([^/]+)\.jsx$/);
    if (!match) continue;
    const section = match[1];
    const file = match[2];

    // Home/Dashboard.jsx is the index route at "/".
    const isHome = section === "Home" && /dashboard/i.test(file);
    const to = isHome ? "/" : `/${slugify(section)}`;

    const meta = MODULE_META[section] || { label: titleFromName(file), order: 99 };
    routes.push({
      section,
      label: meta.label,
      icon: meta.icon || null,
      order: meta.order ?? 99,
      to,
      component: module.default,
    });
  }
  // De-dup if a section has multiple pages (we only use one per section here).
  const bySection = new Map();
  for (const r of routes) {
    if (!bySection.has(r.section)) bySection.set(r.section, r);
  }
  return [...bySection.values()].sort((a, b) => a.order - b.order);
}
