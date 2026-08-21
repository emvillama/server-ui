import type { RecipeStructuredOutput } from "../types";

interface RecipeSpreadProps {
  recipe: RecipeStructuredOutput;
}

/**
 * Left page: title + ingredients. Right page: steps. No sub-tabs
 * (Ingredients/Steps/Notes/Nutrition/Substitutions) -- deliberately
 * simple, matching exactly what Favorite stores (title, ingredients,
 * steps). See the Phase Recipe Recommender devlog, Frontend > Context,
 * for why the richer reference-photo layout was rejected.
 */
export function RecipeLeftPage({ recipe }: RecipeSpreadProps) {
  return (
    <div>
      <h2 className="font-display text-2xl font-semibold mb-4" style={{ color: "var(--color-ink)" }}>
        {recipe.title}
      </h2>
      <h3 className="font-display text-sm uppercase tracking-wide mb-2" style={{ color: "var(--color-ink-soft)" }}>
        Ingredients
      </h3>
      <ul className="space-y-1 text-sm">
        {recipe.ingredients.map((ingredient, i) => (
          <li key={i} style={{ color: "var(--color-ink)" }}>
            • {ingredient}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function RecipeRightPage({ recipe }: RecipeSpreadProps) {
  return (
    <div>
      <h3 className="font-display text-sm uppercase tracking-wide mb-2" style={{ color: "var(--color-ink-soft)" }}>
        Steps
      </h3>
      <ol className="space-y-2 text-sm list-decimal list-inside">
        {recipe.steps.map((step, i) => (
          <li key={i} style={{ color: "var(--color-ink)" }}>
            {step}
          </li>
        ))}
      </ol>
    </div>
  );
}