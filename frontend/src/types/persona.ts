/**
 * Types shared across every persona. Anything specific to how one
 * persona's UI is shaped (tab names, that persona's structured-output
 * payload shape, etc.) lives in that persona's own types.ts instead --
 * see src/personas/recipe-recommender/types.ts for an example.
 */

export interface Capabilities {
  vision: boolean;
  tools: string[];
  skills: string[];
  knowledge: boolean;
  web_search: boolean;
  features: string[];
}

export interface OllamaParams {
  temperature?: number | null;
  top_p?: number | null;
  top_k?: number | null;
  num_ctx?: number | null;
  repeat_penalty?: number | null;
  seed?: number | null;
  stop?: string[] | null;
}

export interface Persona {
  id: number;
  name: string;
  system_prompt: string;
  params: OllamaParams;
  capabilities: Capabilities;
  model: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  persona_id: number;
  reply: string;
  model: string;
  // Generic on purpose -- structured_output's real shape depends on
  // which terminal tool (if any) the persona's model called. A persona
  // consuming this should narrow it to its own specific type, the way
  // Recipe Recommender narrows it to RecipeStructuredOutput.
  structured_output: Record<string, unknown> | null;
}

export interface Favorite {
  id: number;
  persona_id: number;
  title: string;
  ingredients: string[];
  steps: string[];
  created_at: string;
}

export interface PantryItem {
  id: number;
  persona_id: number;
  name: string;
  quantity: number | null;
  unit: string | null;
  updated_at: string;
}