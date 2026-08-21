/**
 * Placeholder structure for the Options tab -- persona settings, not
 * user account settings. Maps onto GET/PUT /personas/{persona_id} and
 * PersonaUpdate exactly: system_prompt, capabilities (tools, skills,
 * features, knowledge, web_search, vision), params (temperature, etc.),
 * and model. No new backend needed for this tab -- see the Phase Recipe
 * Recommender devlog, Frontend > Context.
 */
export function OptionsLeftPage() {
  return (
    <div>
      <h2 className="font-display text-2xl font-semibold mb-1" style={{ color: "var(--color-ink)" }}>
        Persona Settings
      </h2>
      <p className="text-sm italic mb-4" style={{ color: "var(--color-ink-soft)" }}>
        System prompt and model.
      </p>
      <div className="space-y-3">
        <textarea
          placeholder="System prompt..."
          disabled
          rows={6}
          className="w-full rounded border px-3 py-2 text-sm bg-transparent resize-none"
          style={{ borderColor: "var(--color-parchment-shadow)", color: "var(--color-ink)" }}
        />
        <input
          type="text"
          placeholder="Model, e.g. llama3.1:8b"
          disabled
          className="w-full rounded border px-3 py-2 text-sm bg-transparent"
          style={{ borderColor: "var(--color-parchment-shadow)", color: "var(--color-ink)" }}
        />
      </div>
    </div>
  );
}

export function OptionsRightPage() {
  return (
    <div>
      <h2 className="font-display text-2xl font-semibold mb-1" style={{ color: "var(--color-ink)" }}>
        Capabilities
      </h2>
      <p className="text-sm italic mb-4" style={{ color: "var(--color-ink-soft)" }}>
        Tools, skills, and generation params.
      </p>
      <div
        className="rounded-md border border-dashed p-6 text-center text-sm"
        style={{ borderColor: "var(--color-parchment-shadow)", color: "var(--color-ink-soft)" }}
      >
        Tool/skill toggles and params (temperature, etc.) will render
        here once wired to the backend.
      </div>
    </div>
  );
}
