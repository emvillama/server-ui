/**
 * Placeholder for the chef character. The reference photos use a
 * rendered 3D/claymation-style illustration -- a real art asset, not
 * something to fake convincingly in CSS. This renders a simple styled
 * silhouette so the shell's layout and sizing are correct now; swapping
 * in the real asset later just means replacing this file's contents
 * with an <img>, no layout changes needed elsewhere.
 */
export function ChefAvatar() {
  return (
    <div
      className="w-40 h-40 rounded-full flex items-center justify-center text-6xl shadow-lg"
      style={{
        backgroundColor: "var(--color-parchment)",
        border: "4px solid var(--color-wood-light)",
      }}
      role="img"
      aria-label="Chef avatar placeholder"
    >
      🧑‍🍳
    </div>
  );
}
