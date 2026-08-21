/**
 * Placeholder structure for the Favorites tab. Reference photo's tags,
 * dietary filters, and cook-time slider are omitted -- Favorite only
 * stores title/ingredients/steps, so search here is limited to what
 * that actually supports (title search, in practice). Real data wiring
 * is a later step.
 */
export function FavoritesLeftPage() {
  return (
    <div>
      <h2 className="font-display text-2xl font-semibold mb-1" style={{ color: "var(--color-ink)" }}>
        Find Favorites
      </h2>
      <p className="text-sm italic mb-4" style={{ color: "var(--color-ink-soft)" }}>
        Search your saved recipes.
      </p>
      <input
        type="text"
        placeholder="Search favorites..."
        disabled
        className="w-full rounded border px-3 py-2 text-sm bg-transparent"
        style={{ borderColor: "var(--color-parchment-shadow)", color: "var(--color-ink)" }}
      />
    </div>
  );
}

export function FavoritesRightPage() {
  return (
    <div>
      <h2 className="font-display text-2xl font-semibold mb-1" style={{ color: "var(--color-ink)" }}>
        My Favorites
      </h2>
      <p className="text-sm italic mb-4" style={{ color: "var(--color-ink-soft)" }}>
        Your collection of go-to recipes.
      </p>
      <div
        className="rounded-md border border-dashed p-6 text-center text-sm"
        style={{ borderColor: "var(--color-parchment-shadow)", color: "var(--color-ink-soft)" }}
      >
        Saved recipes will list here once wired to the backend.
      </div>
    </div>
  );
}
