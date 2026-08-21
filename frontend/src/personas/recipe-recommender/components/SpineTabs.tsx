import { motion } from "framer-motion";
import type { PersonaTab } from "../types";

interface TabConfig {
  id: PersonaTab;
  label: string;
  colorVar: string;
}

// Order and colors are locked design decisions -- see the Phase Recipe
// Recommender devlog, Frontend > Context. Order must never change
// without updating that record: Chat / Pantry / Favorites / Options.
const TABS: TabConfig[] = [
  { id: "chat", label: "Chat", colorVar: "var(--color-tab-chat)" },
  { id: "pantry", label: "Pantry", colorVar: "var(--color-tab-pantry)" },
  { id: "favorites", label: "Favorites", colorVar: "var(--color-tab-favorites)" },
  { id: "options", label: "Options", colorVar: "var(--color-tab-options)" },
];

interface SpineTabsProps {
  activeTab: PersonaTab;
  onChange: (tab: PersonaTab) => void;
}

/**
 * Renders as tabs protruding from the book's right spine, matching the
 * reference photos. Always visible regardless of book open/closed state
 * -- this is the app's primary navigation, not a per-recipe control.
 */
export function SpineTabs({ activeTab, onChange }: SpineTabsProps) {
  return (
    <div className="absolute right-0 top-16 flex flex-col gap-3 translate-x-[85%]">
      {TABS.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <motion.button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className="rounded-r-md px-4 py-3 text-left font-display font-semibold text-sm shadow-md"
            style={{
              backgroundColor: tab.colorVar,
              color: "var(--color-parchment)",
            }}
            animate={{ x: isActive ? 12 : 0 }}
            whileHover={{ x: isActive ? 12 : 6 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
          >
            {tab.label}
          </motion.button>
        );
      })}
    </div>
  );
}