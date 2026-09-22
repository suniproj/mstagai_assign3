# Meal Plan Agents — Assignment 3 V1

First implementation slice of the 3-agent system.

## High-level flow
1. Requirements
2. Missing-info HITL
3. **Agent 1 / Recipe MCP** — implemented here
4. Agent 2 Nutrition & Safety
5. Revision loop
6. Human meal-plan approval
7. Agent 3 grocery list
8. Price MCP
9. Budget check
10. Human final approval
11. Finalize

## V1 implements
- shared `MealPlanState`
- reuse of Assignment 2 `meal-plan-rag` Pinecone index
- structured recipe repository + metadata filters
- Recipe MCP server
- Agent 1 candidate-retrieval node
- unit tests for filter construction

Assignment 2's generator is intentionally not reused: agents receive structured
recipe evidence and decide what to do next.

## Setup
```bash
python3.11 -m venv .venv
source .venv/bin/activate
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```
Set the same Pinecone API key used by Assignment 2.

## Test
```bash
.venv/bin/python -m pytest -q
```

## Verify the existing recipe index
```bash
.venv/bin/python -c 'from src.recipe_repository import search_recipes; r=search_recipes("high protein vegan dinner", diet="Vegan", meal_type="lunch/dinner", min_protein=15); print([(x["recipe_name"], x["protein_per_serving"], round(x["similarity_score"],3)) for x in r])'
```

## Run Recipe MCP
```bash
.venv/bin/python -m mcp_servers.recipe_server
```

Next slice: Agent 2, LangGraph routing/revision, HITL/checkpointing, Agent 3,
Price MCP, budget routing, Streamlit, and evaluations.
