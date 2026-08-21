import { useState } from "react";
import type { ChatMessage } from "./types/persona";
import type { PersonaTab, RecipeStructuredOutput } from "./personas/recipe-recommender/types";
import { PersonaShell } from "./personas/recipe-recommender/components/PersonaShell";
import { RecipeLeftPage, RecipeRightPage } from "./personas/recipe-recommender/pages/RecipeSpread";
import { PantryLeftPage, PantryRightPage } from "./personas/recipe-recommender/pages/PantryPage";
import { FavoritesLeftPage, FavoritesRightPage } from "./personas/recipe-recommender/pages/FavoritesPage";
import { OptionsLeftPage, OptionsRightPage } from "./personas/recipe-recommender/pages/OptionsPage";

/**
 * Root component. Currently mounts the Recipe Recommender persona
 * directly; once a second persona exists, this becomes the actual
 * router -- reading GET /personas, checking capabilities.ui_theme, and
 * mounting the matching persona folder's shell component instead of
 * assuming Recipe Recommender unconditionally.
 *
 * No backend calls yet -- lastUserMessage/lastAiMessage/recipe are local
 * state stubs for now. Wiring this to real GET/POST calls (useChat hook,
 * persona capabilities driving which spine tabs even render) is the next
 * step after this shell is confirmed working.
 */
function App() {
  const [activeTab, setActiveTab] = useState<PersonaTab>("chat");
  const [lastUserMessage, setLastUserMessage] = useState<ChatMessage | null>(null);
  const [lastAiMessage, setLastAiMessage] = useState<ChatMessage | null>(null);
  const [recipe, setRecipe] = useState<RecipeStructuredOutput | null>(null);

  function handleSendMessage(message: string) {
    // Stub only -- real /chat wiring comes in the next step. For now
    // this just proves the input bar, bubble display, and book's
    // closed->open transition work end to end with fake data.
    setLastUserMessage({ role: "user", content: message });
    setLastAiMessage({
      role: "assistant",
      content: "This is a placeholder reply -- real chat wiring comes next.",
    });
    setRecipe({
      title: "Placeholder Recipe",
      ingredients: ["1 cup placeholder", "2 tbsp stub data"],
      steps: ["This will be replaced by a real return_recipe call."],
    });
  }

  // Book is open on every tab except Chat's idle state (no recipe yet).
  const isBookOpen = activeTab !== "chat" || recipe !== null;

  let leftPage = null;
  let rightPage = null;

  if (activeTab === "chat" && recipe) {
    leftPage = <RecipeLeftPage recipe={recipe} />;
    rightPage = <RecipeRightPage recipe={recipe} />;
  } else if (activeTab === "pantry") {
    leftPage = <PantryLeftPage />;
    rightPage = <PantryRightPage />;
  } else if (activeTab === "favorites") {
    leftPage = <FavoritesLeftPage />;
    rightPage = <FavoritesRightPage />;
  } else if (activeTab === "options") {
    leftPage = <OptionsLeftPage />;
    rightPage = <OptionsRightPage />;
  }

  return (
    <PersonaShell
      activeTab={activeTab}
      onTabChange={setActiveTab}
      lastUserMessage={lastUserMessage}
      lastAiMessage={lastAiMessage}
      onSendMessage={handleSendMessage}
      isBookOpen={isBookOpen}
      leftPage={leftPage}
      rightPage={rightPage}
    />
  );
}

export default App;