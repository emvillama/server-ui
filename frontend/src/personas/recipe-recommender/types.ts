/**
 * Types specific to the Recipe Recommender persona's UI -- not shared
 * with other personas. Generic types (Persona, ChatMessage, etc.) live
 * in src/types/persona.ts instead.
 */

/** The four spine-tab destinations, in the locked nav order. */
export type PersonaTab = "chat" | "pantry" | "favorites" | "options";

/**
 * Shape of ChatResponse.structured_output specifically when this
 * persona's return_recipe tool fires. Mirrors the tool's schema in
 * backend/services/tool_registry.py exactly.
 */
export interface RecipeStructuredOutput {
  title: string;
  ingredients: string[];
  steps: string[];
}