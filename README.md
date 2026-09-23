# Meal Plan & Shop Agents --- Assignment 3

A three-agent meal-planning and shopping assistant demonstrating
LangGraph state/routing, MCP tools, human-in-the-loop (HITL), SQLite
checkpoints, LangSmith tracing/evaluation, and Streamlit.

## Assignment statement

> My agent helps a meal-planning user create and shop for a
> constraint-aware meal plan in a Streamlit application, replacing the
> manual workflow of searching recipes, checking dietary restrictions
> and nutrition, building a grocery list, and estimating cost. It
> performs the workflow using three specialized agents and two MCP
> capabilities, hands control to a human for recipe/plan and shopping
> decisions or when evidence is incomplete, and is evaluated with
> automated tests, golden validation cases, and LangSmith experiments.

## High-level flow

``` text
Requirements
  ↓
Agent 1 — Meal Planner
  ↓  Recipe MCP / Pinecone
Agent 2 — Nutrition & Safety
  ├─ FAIL → Agent 1 revision
  ├─ NEEDS_REVIEW → Human
  ↓
Meal Review HITL
  ├─ Replace recipe → Agent 1 → Agent 2 → review
  ├─ Modify settings → regenerate → Agent 1 → Agent 2
  ├─ Cancel → reset
  ↓ Approve
Agent 3 — Shopping & Budget
  ↓  Price MCP
Shopping HITL
  ├─ Find cheaper meal → Agent 1 → Agent 2 → Agent 3
  ├─ Cancel → reset
  ↓ Approve
Final Summary → Done → History
```

Source comments use `STEP` labels so code maps visibly to this flow.

## Agents

### Agent 1 --- Meal Planner

Files: `src/agents/meal_planner.py`, `src/mcp_clients/recipe_client.py`,
`mcp_servers/recipe_server.py`.

Uses the Assignment 2 Pinecone recipe corpus to retrieve candidates,
build the plan, avoid same-day duplicate recipes, and replace a specific
meal using free-text feedback. A tested request,
`something more filling`, changed retrieval from a salad to a curry.

### Agent 2 --- Nutrition & Safety

Files: `src/agents/nutrition_safety.py`,
`src/tools/constraint_validator.py`,
`src/tools/ingredient_knowledge.py`.

Validates diet, meal type, protein, exclusions, bounded semantic
relationships (for example tofu → soy and portobello → mushroom), and
ambiguity. Returns `PASS`, `FAIL`, or `NEEDS_REVIEW`.

Safety-critical ingredient relationships are supplied by a bounded tool
rather than unconstrained LLM inference.

### Agent 3 --- Shopping & Budget

Files: `src/agents/shopping_budget.py`, `src/tools/grocery_list.py`,
`src/tools/budget.py`, `src/mcp_clients/price_client.py`,
`mcp_servers/price_server.py`.

Extracts grocery items, uses the Price MCP capability, separates priced
from unavailable items, calculates a known subtotal, checks budget
status, and supports cost-driven meal replacement.

## MCP

Two MCP capabilities are exposed: - **Recipe MCP:** recipe retrieval
backed by Pinecone. - **Price MCP:** synthetic grocery-price lookup from
`data/test_prices.json`.

The project uses MCP 2.x `MCPServer`. An initial `FastMCP`
implementation failed under MCP 2.x and was migrated to the current API.

Missing prices return structured `unavailable` results; the application
never invents prices.

## LangGraph and persistence

`src/graph.py` owns conditional routing, loops, HITL interrupts, and
shared `MealPlanState`.

The first checkpoint implementation used `InMemorySaver`. It worked
within one process but could not resume in a new process. The project
was upgraded to `SqliteSaver` using `data/meal_plan_checkpoints.db`.
Cross-process pause/resume was verified with the same `thread_id`.

## Streamlit UI

`app/streamlit_app.py` uses: - left navigation: Meal Planner, Recipe
Browser, Receipts & Bills placeholder; - center: active workflow; -
right: completed Plan History.

Meal Review supports per-recipe replacement, Modify Settings, Cancel,
and Approve Meal Plan. Shopping Review shows priced and unavailable
items and supports Find Cheaper Meal, Cancel, and Approve Shopping Plan.
Final Summary shows nutrition, expandable full recipes, and a grocery
bill.

Completed history is runtime data in `data/plan_history.json`.

## Project structure

``` text
app/streamlit_app.py
data/challenge_recipes.json
data/validation_golden.csv
data/test_prices.json
evals/validation_eval.py
evals/langsmith_validation_eval.py
mcp_servers/recipe_server.py
mcp_servers/price_server.py
src/agents/meal_planner.py
src/agents/nutrition_safety.py
src/agents/shopping_budget.py
src/mcp_clients/recipe_client.py
src/mcp_clients/price_client.py
src/tools/constraint_validator.py
src/tools/ingredient_knowledge.py
src/tools/grocery_list.py
src/tools/budget.py
src/graph.py
src/state.py
tests/test_validation.py
tests/test_shopping_budget.py
tests/test_full_flow.py
```

## Setup

``` bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Configure Pinecone plus:

``` text
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your-key>
LANGSMITH_PROJECT=meal-plan-agents-assignment3
```

Never commit `.env`.

## Run

``` bash
python -m streamlit run app/streamlit_app.py
```

## Tests

``` bash
python -m pytest -q
```

Verified milestone: **10 passed**.

Tests cover validation, protein/exclusions, review behavior, budget
calculations, incomplete pricing, multi-agent integration, meal-plan
HITL, Agent 3 execution, and shopping-review HITL.

## Agent 2 evaluation

``` bash
python -m evals.validation_eval
```

Deterministic-only baseline: **7/15 = 46.7%**.

Misses included tofu/miso/edamame/tempeh → soy,
shiitake/cremini/portobello → mushroom, and ambiguous dairy phrases.

After bounded ingredient relationships and ambiguity handling: **15/15 =
100%**.

## LangSmith

Tracing showed:

``` text
agent1_retrieve
→ agent1_build_plan
→ agent2_validate
→ meal_plan_review
```

Opening `meal_plan_review` showed it as **interrupted**, confirming the
HITL pause.

Run evaluation:

``` bash
python -m evals.langsmith_validation_eval
```

Dataset: `agent2-nutrition-safety-eval`.

Five representative cases cover semantic soy conflict, semantic mushroom
conflict, explicit safe case, protein failure, and ambiguous evidence.
Verified result: **5/5 `status_match = 1` (100%)**.

## Important iterations / learnings

1.  Deterministic Agent 2 baseline: 46.7%.
2.  Bounded semantic ingredient knowledge + uncertainty: 100% on 15
    golden cases.
3.  `InMemorySaver` could not persist across process restarts.
4.  SQLite checkpointing successfully resumed a thread in a second
    process.
5.  MCP v1 `FastMCP` code failed under installed MCP 2.x; migrated to
    `MCPServer`.
6.  Free-text replacement feedback successfully changed semantic
    retrieval.
7.  Price failures are explicit and excluded from the known subtotal.

## Known limitations

-   One meal slot = one primary recipe; multi-course meals are out of
    scope.
-   Dataset category `lunch/dinner` is shared by lunch and dinner.
-   Grocery prices are synthetic test prices, not live store quotes.
-   Ingredient quantities are not normalized/consolidated.
-   Known subtotal can be incomplete.
-   Recipe-quality heuristics can still improve.
-   Receipts & Bills is reserved for future work.
-   Plan history is local runtime storage, not production multi-user
    persistence.

## Demo checklist

1.  Create a Vegan plan with constraints.
2.  Show Agent 1 creation and Agent 2 validation.
3.  Replace a recipe using `something more filling`.
4.  Approve the meal plan.
5.  Show Agent 3 priced and unavailable items.
6.  Optionally request a cheaper meal.
7.  Approve shopping and show final summary.
8.  Show LangSmith trace with `meal_plan_review` interrupted.
9.  Show LangSmith 5/5 evaluation.

## Git hygiene

Commit source, tests, eval scripts, challenge/golden data, synthetic
price catalog, `.env.example`, and docs.

Do not commit `.env`, `.venv/`, `data/meal_plan_checkpoints.db`,
`data/plan_history.json`, or cache directories.
