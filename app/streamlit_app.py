import json
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from langgraph.types import Command

from src.graph import meal_plan_graph
from src.recipe_repository import search_recipes

HISTORY_FILE = Path("data/plan_history.json")
st.set_page_config(page_title="Meal Plan & Shop", layout="wide")

def initialize_session():
    """Initialize UI state without disturbing an active workflow."""
    defaults = {
        "page": "Meal Planner",
        "thread_id": f"meal-plan-{uuid.uuid4()}",
        "graph_result": None,
        "replacement_target": None,
        "show_cost_replacement": False,
        "history_plan_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def graph_config():
    return {"configurable": {"thread_id": st.session_state.thread_id}}

def reset_to_default_planner():
    st.session_state.thread_id = f"meal-plan-{uuid.uuid4()}"
    st.session_state.graph_result = None
    st.session_state.replacement_target = None
    st.session_state.show_cost_replacement = False
    st.session_state.history_plan_id = None
    st.session_state.page = "Meal Planner"

def get_interrupt(result):
    interrupts = result.get("__interrupt__", [])
    return interrupts[0].value if interrupts else None

def resume_graph(payload):
    st.session_state.graph_result = meal_plan_graph.invoke(
        Command(resume=payload),
        config=graph_config(),
    )
    st.session_state.replacement_target = None
    st.session_state.show_cost_replacement = False
    st.rerun()

def load_history():
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE) as history_file:
        return json.load(history_file)

def save_history(result):
    history = load_history()
    record = {
        "plan_id": f"plan-{uuid.uuid4()}",
        "created_at": datetime.now().isoformat(timespec="minutes"),
        "diet": result.get("diet"),
        "days": result.get("days"),
        "meal_slots": result.get("meal_slots", []),
        "meal_plan": result.get("draft_meal_plan", []),
        "priced_grocery_list": result.get("priced_grocery_list", []),
        "estimated_total": result.get("estimated_total"),
        "budget": result.get("budget"),
        "budget_status": result.get("budget_status"),
        "pricing_errors": result.get("pricing_errors", []),
    }
    history.insert(0, record)
    with open(HISTORY_FILE, "w") as history_file:
        json.dump(history, history_file, indent=2)

def show_left_navigation():
    with st.sidebar:
        st.header("Meal Plan & Shop")
        if st.button("Meal Planner", use_container_width=True):
            st.session_state.page = "Meal Planner"
            st.session_state.history_plan_id = None
            st.rerun()
        if st.button("Recipe Browser", use_container_width=True):
            st.session_state.page = "Recipe Browser"
            st.session_state.history_plan_id = None
            st.rerun()
        st.button(
            "Receipts & Bills",
            use_container_width=True,
            disabled=True,
            help="Reserved for the next application capability.",
        )

def show_history_panel():
    st.subheader("Plan History")
    history = load_history()
    if not history:
        st.caption("No completed plans yet.")
        return

    for plan in history[:10]:
        label = f"{plan.get('days', '?')}-Day {plan.get('diet', 'Meal')} Plan"
        if st.button(label, key=f"history-{plan['plan_id']}", use_container_width=True):
            st.session_state.history_plan_id = plan["plan_id"]
            st.rerun()
        st.caption(
            f"{plan['created_at'].replace('T', ' ')} · "
            f"${plan.get('estimated_total', 0):.2f} known"
        )

def show_agent_progress(result):
    st.subheader("Agent Workflow")
    columns = st.columns(3)
    columns[0].success(
        "Agent 1 — Meal Planner ✓"
        if result.get("draft_meal_plan")
        else "Agent 1 — Waiting"
    )
    columns[1].success(
        "Agent 2 — Safety ✓"
        if result.get("validation_status") == "PASS"
        else "Agent 2 — Waiting"
    )
    columns[2].success(
        "Agent 3 — Shopping ✓"
        if result.get("grocery_list")
        else "Agent 3 — Waiting"
    )

def show_meal_plan(meal_plan, allow_replacement=False):
    st.subheader("Meal Plan")
    for day_number in sorted({meal["day"] for meal in meal_plan}):
        st.markdown(f"### Day {day_number}")
        for meal in [item for item in meal_plan if item["day"] == day_number]:
            recipe = meal["recipe"]
            details_column, action_column = st.columns([4, 1])
            with details_column:
                st.markdown(
                    f"**{meal['meal_slot'].title()} — {recipe['recipe_name']}**"
                )
                nutrition = []
                if recipe.get("calories_per_serving") is not None:
                    nutrition.append(f"{recipe['calories_per_serving']:.0f} kcal")
                if recipe.get("protein_per_serving") is not None:
                    nutrition.append(f"{recipe['protein_per_serving']:.1f} g protein")
                st.caption(" · ".join(nutrition) + f" · {recipe.get('source', '')}")
            with action_column:
                if allow_replacement:
                    key = f"replace-{day_number}-{meal['meal_slot']}-{recipe['recipe_id']}"
                    if st.button("↻ Replace", key=key):
                        st.session_state.replacement_target = meal
                        st.rerun()

def show_replacement_form():
    target = st.session_state.replacement_target
    if not target:
        return
    recipe = target["recipe"]
    st.info(
        f"Replacing Day {target['day']} {target['meal_slot'].title()}: "
        f"{recipe['recipe_name']}"
    )
    feedback = st.text_input(
        "What would you prefer? (optional)",
        placeholder="something more filling, spicy, different cuisine",
        key="replacement_feedback",
    )
    cancel_column, replace_column = st.columns(2)
    if cancel_column.button("Cancel"):
        st.session_state.replacement_target = None
        st.rerun()
    if replace_column.button("Find Replacement"):
        resume_graph({
            "action": "replace",
            "feedback": feedback,
            "revision_request": {
                "day": target["day"],
                "meal_slot": target["meal_slot"],
                "rejected_recipe_id": recipe["recipe_id"],
                "reason": "preference",
                "feedback": feedback,
            },
        })


def show_pricing(result):
    """Show both successful and failed Price MCP results."""
    st.subheader("Shopping & Budget")
    priced_items = result.get("priced_grocery_list", [])
    available = [item for item in priced_items if item.get("status") == "available"]
    unavailable = [item for item in priced_items if item.get("status") == "unavailable"]

    st.markdown("#### Priced Items")
    if available:
        st.dataframe(
            [
                {
                    "Ingredient": item["ingredient_line"],
                    "Matched item": item.get("matched_ingredient", ""),
                    "Test price": f"${item['price']:.2f}",
                }
                for item in available
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No grocery items were priced.")

    st.markdown("#### Price Unavailable")
    if unavailable:
        st.dataframe(
            [{"Ingredient": item["ingredient_line"], "Status": "Unavailable"} for item in unavailable],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("All grocery items have test prices.")

    subtotal = result.get("estimated_total")
    if subtotal is not None:
        st.metric("Known subtotal", f"${subtotal:.2f}")
    st.write(f"Budget status: **{result.get('budget_status')}**")
    if unavailable:
        st.warning(
            "Known subtotal excludes unavailable items. "
            "The agent did not invent missing prices."
        )

def show_cost_replacement(meal_plan):
    meal_options = {
        f"Day {meal['day']} — {meal['meal_slot'].title()} — {meal['recipe']['recipe_name']}": meal
        for meal in meal_plan
    }
    selected_label = st.selectbox("Meal to replace", list(meal_options.keys()))
    feedback = st.text_input(
        "Replacement request",
        value="cheaper alternative",
        key="cost_feedback",
    )
    if st.button("Find Cheaper Option"):
        meal = meal_options[selected_label]
        resume_graph({
            "action": "find_cheaper_meal",
            "revision_request": {
                "day": meal["day"],
                "meal_slot": meal["meal_slot"],
                "rejected_recipe_id": meal["recipe"]["recipe_id"],
                "reason": "cost",
                "feedback": feedback,
            },
        })

def show_final_summary(result, history_mode=False):
    st.success("Meal plan and shopping plan approved.")
    meal_plan = result.get("draft_meal_plan", result.get("meal_plan", []))

    st.subheader("Final Meal Plan")
    for day_number in sorted({meal["day"] for meal in meal_plan}):
        st.markdown(f"### Day {day_number}")
        for meal in [item for item in meal_plan if item["day"] == day_number]:
            recipe = meal["recipe"]
            st.markdown(
                f"**{meal['meal_slot'].title()} — {recipe['recipe_name']}**"
            )
            calories = recipe.get("calories_per_serving")
            protein = recipe.get("protein_per_serving")
            if calories is not None and protein is not None:
                st.caption(f"{calories:.0f} kcal · {protein:.1f} g protein")
            with st.expander("View Full Recipe"):
                st.text(recipe.get("recipe_text", "Recipe details unavailable."))

    st.subheader("Grocery Bill")
    priced_items = result.get("priced_grocery_list", [])
    st.dataframe(
        [
            {
                "Ingredient": item["ingredient_line"],
                "Price / status": (
                    f"${item['price']:.2f}"
                    if item.get("status") == "available"
                    else "Unavailable"
                ),
            }
            for item in priced_items
        ],
        use_container_width=True,
        hide_index=True,
    )
    subtotal = result.get("estimated_total")
    if subtotal is not None:
        st.metric("Known subtotal", f"${subtotal:.2f}")
    if result.get("pricing_errors"):
        st.warning("Known subtotal excludes unavailable items.")

    if not history_mode and st.button("Done"):
        save_history(result)
        reset_to_default_planner()
        st.rerun()

def show_history_plan(plan_id):
    plan = next(
        (item for item in load_history() if item["plan_id"] == plan_id),
        None,
    )
    if not plan:
        st.warning("History record not found.")
        return

    st.caption("Viewing completed plan")
    show_final_summary(
        {
            "meal_plan": plan["meal_plan"],
            "priced_grocery_list": plan["priced_grocery_list"],
            "estimated_total": plan["estimated_total"],
            "budget_status": plan["budget_status"],
            "pricing_errors": plan["pricing_errors"],
        },
        history_mode=True,
    )
    if st.button("Return to Current Plan"):
        st.session_state.history_plan_id = None
        st.rerun()

def show_recipe_browser():
    st.title("Recipe Browser")
    st.caption("Search the same recipe knowledge base used by Agent 1.")

    with st.form("recipe_search"):
        query = st.text_input("Search", placeholder="spicy chickpea dinner")
        diet = st.selectbox("Diet", ["Any", "Vegan", "Vegetarian"])
        meal = st.selectbox("Meal", ["Any", "breakfast", "lunch/dinner", "snack"])
        min_protein = st.number_input(
            "Minimum protein (g)",
            min_value=0.0,
            value=0.0,
        )
        submitted = st.form_submit_button("Search Recipes")

    if submitted:
        recipes = search_recipes(
            query=query or "recipe",
            diet=None if diet == "Any" else diet,
            meal_type=None if meal == "Any" else meal,
            min_protein=None if min_protein == 0 else min_protein,
            top_k=10,
        )
        for recipe in recipes:
            st.markdown(f"### {recipe['recipe_name']}")
            st.caption(
                f"{recipe.get('protein_per_serving', 0):.1f} g protein · "
                f"{recipe.get('calories_per_serving', 0):.0f} kcal · "
                f"{recipe.get('source', '')}"
            )
            with st.expander("View Recipe"):
                st.text(recipe.get("recipe_text", ""))

def show_meal_planner():
    st.title("Meal Plan & Shop Agent")
    st.caption("Agent 1 plans · Agent 2 validates · Agent 3 shops and checks budget")

    with st.form("requirements"):
        days = st.number_input("Number of days", min_value=1, max_value=7, value=1)
        diet = st.selectbox("Diet", ["Vegan", "Vegetarian"])
        st.write("Meals")
        breakfast = st.checkbox("Breakfast", value=True)
        lunch = st.checkbox("Lunch", value=True)
        dinner = st.checkbox("Dinner", value=True)
        excluded_text = st.text_input(
            "Excluded ingredients",
            placeholder="soy, mushroom",
        )
        min_protein = st.number_input(
            "Minimum protein per meal (g)",
            min_value=0.0,
            value=0.0,
        )
        budget = st.number_input("Budget ($)", min_value=0.0, value=75.0)
        submitted = st.form_submit_button("Create Meal Plan")

    if submitted:
        meal_slots = []
        if breakfast:
            meal_slots.append("breakfast")
        if lunch:
            meal_slots.append("lunch")
        if dinner:
            meal_slots.append("dinner")

        excluded = [
            item.strip()
            for item in excluded_text.split(",")
            if item.strip()
        ]
        reset_to_default_planner()
        initial_state = {
            "user_request": "Create a meal plan",
            "days": int(days),
            "meal_slots": meal_slots,
            "diet": diet,
            "excluded_ingredients": excluded,
            "min_protein_per_meal": min_protein if min_protein > 0 else None,
            "budget": budget if budget > 0 else None,
        }
        with st.spinner("Agents are building and validating your plan..."):
            st.session_state.graph_result = meal_plan_graph.invoke(
                initial_state,
                config=graph_config(),
            )

    result = st.session_state.graph_result
    if not result:
        return

    show_agent_progress(result)
    meal_plan = result.get("draft_meal_plan", [])
    interrupt_value = get_interrupt(result)
    interrupt_type = interrupt_value.get("type") if interrupt_value else None

    if interrupt_type == "meal_plan_review":
        show_meal_plan(meal_plan, allow_replacement=True)
        show_replacement_form()
        st.divider()
        approve_column, decline_column = st.columns(2)
        if approve_column.button("Approve Meal Plan →"):
            resume_graph({"action": "approve", "feedback": None})
        if decline_column.button("Decline Plan"):
            resume_graph({"action": "decline", "feedback": None})

    elif interrupt_type == "shopping_review":
        show_meal_plan(meal_plan)
        show_pricing(result)
        st.divider()

        if st.button("Find Cheaper Meal"):
            st.session_state.show_cost_replacement = True
            st.rerun()

        if st.session_state.show_cost_replacement:
            show_cost_replacement(meal_plan)

        approve_column, decline_column = st.columns(2)
        if approve_column.button("Approve Available Estimate"):
            resume_graph({"action": "approve"})
        if decline_column.button("Decline"):
            resume_graph({"action": "decline"})

    elif result.get("final_approval") == "approve":
        show_final_summary(result)

    elif result.get("final_response"):
        st.warning(result["final_response"])


initialize_session()
show_left_navigation()

main_column, history_column = st.columns([4, 1], gap="large")

with history_column:
    show_history_panel()

with main_column:
    if st.session_state.history_plan_id:
        show_history_plan(st.session_state.history_plan_id)
    elif st.session_state.page == "Recipe Browser":
        show_recipe_browser()
    else:
        show_meal_planner()
