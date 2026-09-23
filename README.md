# Meal Plan & Shop Agents --- Assignment 3

A three-agent meal-planning and shopping assistant demonstrating
LangGraph state/routing, MCP tools, human-in-the-loop (HITL), SQLite
checkpoints, LangSmith tracing/evaluation, Pinecone recipe retrieval,
and Streamlit.

## Project statement

> My agent helps a meal-planning user create and shop for a
> constraint-aware meal plan, replacing the manual workflow of searching
> recipes, checking dietary restrictions and nutrition, building a
> grocery list, estimating cost, and revising choices. Three specialized
> agents use reusable MCP capabilities, while human interrupts retain
> control over preferences, settings, cost revisions, and uncertain
> outcomes.

## Core design principle

**Every user-supplied constraint must have an explicit outcome:
satisfied, unsatisfied, unverifiable, or requiring human review.**

The application does not silently ignore constraints or present
incomplete results as success.

Examples: - impossible recipe constraints → `planning_failure`; - no
valid replacement → `replacement_failure`; - known subtotal above a hard
budget → `budget_failure`; - missing prices prevent budget verification
→ `pricing_unknown`; - uncertain safety evidence → human review.

## High-level flow

``` text
Requirements
    ↓
Agent 1 — Meal Planner
    ↓ Recipe MCP / Pinecone
Plan completeness check
    ├─ incomplete → planning_failure → Modify Settings / Cancel
    ↓
Agent 2 — Nutrition & Safety
    ├─ FAIL → revision
    ├─ NEEDS_REVIEW → human review
    ↓
Meal Review HITL
    ├─ Replace recipe → Agent 1 → Agent 2 → review
    ├─ Modify Settings → regenerate
    ├─ Cancel → reset
    ↓ Approve
Agent 3 — Shopping & Budget
    ↓ Price MCP
Budget/pricing decision
    ├─ OVER_BUDGET → budget_failure → cheaper meal / modify / cancel
    ├─ INCOMPLETE_PRICING → pricing_unknown → partial / modify / cancel
    ↓
Shopping Review HITL
    ├─ Find Cheaper Meal → Agent 1 → Agent 2 → Agent 3 → reprice
    ├─ Cancel → reset
    ↓ Approve
Final Summary → Done → History
```

## Agent 1 --- Meal Planner

Primary file: `src/agents/meal_planner.py`.

Responsibilities: - retrieve candidates through Recipe MCP/Pinecone; -
map breakfast vs shared lunch/dinner dataset categories; - build the
requested day/meal-slot plan; - avoid same-day duplicate recipes; -
detect missing meal slots; - replace one recipe using free-text
feedback; - receive cost-driven replacement requests.

Free-text preferences are added to the semantic retrieval query. A
tested request for `something more filling` changed retrieval from a
salad to a curry. This is semantic embedding retrieval, not a formal
satiety model.

## Agent 2 --- Nutrition & Safety

Primary files: - `src/agents/nutrition_safety.py` -
`src/tools/constraint_validator.py` -
`src/tools/ingredient_knowledge.py`

Validates diet, meal type, minimum protein, exclusions, bounded semantic
ingredient relationships, and uncertainty. Returns `PASS`, `FAIL`, or
`NEEDS_REVIEW`.

### Evaluation improvement

Initial deterministic baseline:

``` text
7/15 = 46.7%
```

After bounded ingredient relationships (e.g. tofu → soy, portobello →
mushroom) and explicit ambiguity handling:

``` text
15/15 = 100%
```

## Agent 3 --- Shopping & Budget

Primary files: - `src/agents/shopping_budget.py` -
`src/tools/grocery_list.py` - `src/tools/budget.py` -
`src/mcp_clients/price_client.py`

Responsibilities: - build grocery list; - call Price MCP; - preserve
unavailable prices; - calculate known subtotal; - enforce budget
outcome; - support cost-driven meal replacement.

### Budget semantics

``` text
$0          → any budget / NO_BUDGET
$0.01–$2.99 → invalid input
$3+         → hard budget constraint
```

Hard-budget outcomes:

``` text
WITHIN_BUDGET      → normal shopping review
OVER_BUDGET        → budget_failure
INCOMPLETE_PRICING → pricing_unknown
```

If known cost alone exceeds the budget, the constraint is already
unsatisfied even if additional prices are missing. If known cost is
within budget but prices are missing, the true total is unverifiable.

## MCP capabilities

### Recipe MCP

Reusable recipe-search capability backed by the Assignment 2 Pinecone
corpus.

### Price MCP

Reproducible synthetic grocery-price lookup backed by
`data/test_prices.json`.

The project uses MCP 2.x `MCPServer`; an earlier `FastMCP`
implementation was migrated after the installed SDK reported the v2 API
change.

## LangGraph and persistence

`src/graph.py` owns shared state, conditional routing, loops, HITL
interrupts, and failure states.

The initial `InMemorySaver` checkpoint worked only within one process.
The final implementation uses `SqliteSaver` with
`data/meal_plan_checkpoints.db`. Cross-process pause/resume using the
same `thread_id` was verified.

## Streamlit UI

Layout: - **Left:** Meal Planner, Recipe Browser, Receipts & Bills
placeholder. - **Center:** active workflow. - **Right:** completed Plan
History.

Planner modes are explicit: - **Configure:** editable defaults and
Create Meal Plan. - **Active:** requirements shown as solid read-only
values. - **Modify:** current settings restored/editable with Update
Meal Plan.

Meal Review supports per-recipe Replace, Modify Settings, Cancel, and
Approve Meal Plan. Shopping handles explicit budget/pricing outcomes and
cost-driven replacement. Final Summary shows nutrition, expandable
recipes, and grocery bill.

## Automated tests

Run:

``` bash
python -m pytest -q
```

Final verified milestone:

``` text
16 passed
```

Coverage includes validation, protein/exclusions, explicit planning
failure, replacement/budget outcomes, incomplete pricing, multi-agent
integration, HITL, Agent 3, and shopping routing.

## LangSmith

Tracing showed:

``` text
agent1_retrieve
→ agent1_build_plan
→ agent2_validate
→ meal_plan_review
```

Opening `meal_plan_review` showed it as **interrupted**, confirming
HITL.

Representative dataset evaluation:

``` text
agent2-nutrition-safety-eval
5/5 status_match = 1
100%
```

Cases cover semantic soy conflict, semantic mushroom conflict, explicit
safe case, protein failure, and ambiguous evidence.

## Final evidence

  Evidence                                                                   Result
  ------------------------------------- -------------------------------------------
  pytest                                                              **16 passed**
  Agent 2 deterministic baseline                                   **7/15 = 46.7%**
  Agent 2 enhanced golden evaluation                               **15/15 = 100%**
  LangSmith representative evaluation                                **5/5 = 100%**
  LangSmith HITL trace                      `meal_plan_review` shown as interrupted
  Persistence                                  SQLite cross-process resume verified
  Unsatisfiable meal request                            explicit `planning_failure`
  Over-budget request                     explicit `budget_failure` + revision loop
  Hard budget with missing prices                        explicit `pricing_unknown`

## Run

``` bash
python -m pip install -r requirements.txt
cp .env.example .env
python -m pytest -q
python -m streamlit run app/streamlit_app.py
```

LangSmith environment:

``` text
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your-key>
LANGSMITH_PROJECT=meal-plan-agents-assignment3
```

## Evaluation commands

``` bash
python -m evals.validation_eval
python -m evals.langsmith_validation_eval
```

## Known limitations

-   one primary recipe per meal slot;
-   source corpus shares lunch/dinner category;
-   synthetic rather than live grocery prices;
-   ingredient quantities are not normalized/consolidated;
-   incomplete prices can make a hard budget unverifiable;
-   semantic preference retrieval is not a formal model of concepts such
    as satiety;
-   Receipts & Bills is reserved for future work;
-   Plan History is local runtime storage.

## Demo checklist

1.  Create a constrained Vegan plan.
2.  Show Agent 1 + Agent 2.
3.  Replace a recipe using `something more filling`.
4.  Approve recipes.
5.  Use a small budget to show explicit `budget_failure`.
6.  Try Cheaper Meal and show Agent 1 → Agent 2 → Agent 3 repricing.
7.  Show final nutrition/recipes/bill.
8.  Briefly show a 100g protein request producing `planning_failure`.
9.  Show LangSmith `meal_plan_review` interrupted trace.
10. Show 5/5 LangSmith evaluation and 16 passing tests.

## Git hygiene

Commit code, tests, eval scripts, challenge/golden data, synthetic price
catalog, `.env.example`, and documentation.

Do not commit `.env`, `.venv/`, `data/meal_plan_checkpoints.db`,
`data/plan_history.json`, or cache directories.
