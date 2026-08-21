import { AnimatePresence, motion } from "framer-motion";
import type { ReactNode } from "react";

interface BookProps {
  /** Closed = just the cover (Chat tab's idle state). Open = two-page
   * spread (every other tab, and Chat once a recipe comes back). */
  isOpen: boolean;
  coverTitle?: string;
  leftPage?: ReactNode;
  rightPage?: ReactNode;
  /** Spine tabs render here so they stay visually attached to the book
   * regardless of open/closed state. */
  spineTabs: ReactNode;
}

/**
 * The book is the single shared container every tab's content lives
 * inside. Only Chat has a real "closed" state (before any recipe);
 * Pantry/Favorites/Options are always rendered open, per the locked
 * design -- see the Phase Recipe Recommender devlog, Frontend > Context.
 */
export function Book({ isOpen, coverTitle, leftPage, rightPage, spineTabs }: BookProps) {
  return (
    <div className="relative w-full max-w-4xl aspect-[16/9]">
      {spineTabs}

      <div
        className="w-full h-full rounded-md shadow-2xl overflow-hidden"
        style={{
          backgroundColor: "var(--color-parchment-dark)",
          border: "1px solid var(--color-wood-light)",
        }}
      >
        <AnimatePresence mode="wait">
          {!isOpen ? (
            <motion.div
              key="cover"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35 }}
              className="w-full h-full flex items-center justify-center"
              style={{ backgroundColor: "var(--color-wood-mid)" }}
            >
              <h1
                className="font-display text-3xl italic text-center px-8"
                style={{ color: "var(--color-parchment)" }}
              >
                {coverTitle ?? "The Recipe Recommender's Cookbook"}
              </h1>
            </motion.div>
          ) : (
            <motion.div
              key="spread"
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.97 }}
              transition={{ duration: 0.35 }}
              className="w-full h-full grid grid-cols-2"
            >
              <div
                className="p-8 overflow-y-auto"
                style={{
                  backgroundColor: "var(--color-parchment)",
                  borderRight: "2px solid var(--color-parchment-shadow)",
                }}
              >
                {leftPage}
              </div>
              <div
                className="p-8 overflow-y-auto"
                style={{ backgroundColor: "var(--color-parchment)" }}
              >
                {rightPage}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
