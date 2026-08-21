/**
 * Placeholder structure for the Pantry tab's two-page spread. Fields
 * shown match PantryItemCreate/PantryItemOut exactly (name, quantity,
 * unit) -- no category or low-stock indicator, since the backend
 * doesn't store either. Wiring to real GET/POST /personas/{id}/pantry
 * calls happens once useChat-style data hooks are built (next step
 * after this shell); this is structure only.
 */
export function PantryLeftPage() {
  return (
    <div>
      <h2 className="font-display text-2xl font-semibold mb-1" style={{ color: "var(--color-ink)" }}>
        Your Pantry
      </h2>
      <p className="text-sm italic mb-4" style={{ color: "var(--color-ink-soft)" }}>
        Here's what you have in your kitchen.
      </p>
      <div
        className="rounded-md border border-dashed p-6 text-center text-sm"
        style={{ borderColor: "var(--color-parchment-shadow)", color: "var(--color-ink-soft)" }}
      >
        Pantry items will list here once wired to the backend.
      </div>
    </div>
  );
}

export function PantryRightPage() {
  return (
    <div>
      <h2 className="font-display text-2xl font-semibold mb-1" style={{ color: "var(--color-ink)" }}>
        Add to Pantry
      </h2>
      <p className="text-sm italic mb-4" style={{ color: "var(--color-ink-soft)" }}>
        Add items you bought at the store or found in your kitchen.
      </p>
      <div className="space-y-3">
        <input
          type="text"
          placeholder="Item name, e.g. Red Lentils"
          disabled
          className="w-full rounded border px-3 py-2 text-sm bg-transparent"
          style={{ borderColor: "var(--color-parchment-shadow)", color: "var(--color-ink)" }}
        />
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Quantity"
            disabled
            className="flex-1 rounded border px-3 py-2 text-sm bg-transparent"
            style={{ borderColor: "var(--color-parchment-shadow)", color: "var(--color-ink)" }}
          />
          <input
            type="text"
            placeholder="Unit"
            disabled
            className="flex-1 rounded border px-3 py-2 text-sm bg-transparent"
            style={{ borderColor: "var(--color-parchment-shadow)", color: "var(--color-ink)" }}
          />
        </div>
        <button
          disabled
          className="w-full rounded-full py-2 text-sm font-semibold opacity-60"
          style={{ backgroundColor: "var(--color-accent)", color: "var(--color-parchment)" }}
        >
          Add to Pantry
        </button>
      </div>
    </div>
  );
}
