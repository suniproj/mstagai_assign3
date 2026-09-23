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
        "planner_mode": "configure",
        "plan_settings": {
            "days": 1,
            "diet": "Vegan",
            "breakfast": True,
            "lunch": True,
            "dinner": True,
            "excluded_text": "",
            "min_protein": 0.0,
            "budget": 0.0,
        },
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
    st.session_state.planner_mode = "configure"
    st.session_state.plan_settings = {
        "days": 1,
        "diet": "Vegan",
        "breakfast": True,
        "lunch": True,
        "dinner": True,
        "excluded_text": "",
        "min_protein": 0.0,
        "budget": 0.0,
    }

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

def show_cost_replacement(meal_plan, resume_action="find_cheaper_meal"):
    """
    Let the human select one meal for a cost-driven replacement.

    `shopping_review` expects `find_cheaper_meal`.
    `budget_failure` expects `try_cheaper_meal`.
    """
    meal_options = {
        (
            f"Day {meal['day']} — "
            f"{meal['meal_slot'].title()} — "
            f"{meal['recipe']['recipe_name']}"
        ): meal
        for meal in meal_plan
    }

    if not meal_options:
        st.error(
            "No meals are available for cost-based replacement."
        )
        return

    selected_label = st.selectbox(
        "Meal to replace",
        list(meal_options.keys()),
    )

    feedback = st.text_input(
        "Replacement request",
        value="cheaper alternative",
        key="cost_feedback",
    )

    cancel_column, replace_column = st.columns(2)

    if cancel_column.button(
        "Cancel Cheaper Meal",
        key=f"cancel-cheaper-{resume_action}",
    ):
        st.session_state.show_cost_replacement = False
        st.rerun()

    if replace_column.button(
        "Find Cheaper Option",
        key=f"find-cheaper-{resume_action}",
    ):
        meal = meal_options[selected_label]

        resume_graph({
            "action": resume_action,
            "revision_request": {
                "day": meal["day"],
                "meal_slot": meal["meal_slot"],
                "rejected_recipe_id": (
                    meal["recipe"]["recipe_id"]
                ),
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


def show_budget_failure(result, current_interrupt):
    """Show an explicit failure when the hard budget is exceeded."""
    st.error("Budget could not be satisfied")

    budget = current_interrupt.get("budget")
    subtotal = current_interrupt.get("estimated_total")
    over_by = current_interrupt.get("over_by")

    st.write(current_interrupt.get("message"))

    metric_columns = st.columns(3)
    metric_columns[0].metric("Budget", f"${budget:.2f}")
    metric_columns[1].metric("Known subtotal", f"${subtotal:.2f}")
    metric_columns[2].metric("Over budget by", f"${over_by:.2f}")

    st.info(
        "The current plan cannot be approved against this budget. "
        "Try a cheaper meal, modify the budget/settings, or cancel."
    )

    cancel_column, modify_column, cheaper_column = st.columns(3)

    if cancel_column.button("Cancel", key="budget-failure-cancel"):
        reset_to_default_planner()
        st.rerun()

    if modify_column.button("Modify Budget / Settings", key="budget-failure-modify"):
        st.session_state.planner_mode = "modify"
        st.rerun()

    if cheaper_column.button("Try Cheaper Meal", key="budget-failure-cheaper"):
        st.session_state.show_cost_replacement = True
        st.rerun()

    if st.session_state.show_cost_replacement:
        show_cost_replacement(
            result.get("draft_meal_plan", []),
            resume_action="try_cheaper_meal",
        )


def show_pricing_unknown(result, current_interrupt):
    """Show that a hard budget cannot be verified because prices are missing."""
    st.warning("Budget cannot be verified")

    st.write(current_interrupt.get("message"))
    show_pricing(result)

    st.info(
        "You can continue with the partial estimate, "
        "modify the budget/settings, or cancel."
    )

    cancel_column, modify_column, continue_column = st.columns(3)

    if cancel_column.button("Cancel", key="pricing-unknown-cancel"):
        reset_to_default_planner()
        st.rerun()

    if modify_column.button("Modify Budget / Settings", key="pricing-unknown-modify"):
        st.session_state.planner_mode = "modify"
        st.rerun()

    if continue_column.button("Continue With Partial Estimate", key="pricing-unknown-continue"):
        resume_graph({"action": "continue_partial"})


def show_planning_failure(result, current_interrupt):
    """Show an explicit outcome when requested constraints cannot be satisfied."""
    st.error("Could not complete the requested meal plan")

    message = (
        current_interrupt.get("message")
        or result.get("planning_message")
        or "The requested constraints could not be satisfied."
    )
    st.write(message)

    missing_slots = (
        current_interrupt.get("missing_meal_slots")
        or result.get("missing_meal_slots", [])
    )

    if missing_slots:
        st.markdown("#### Missing meal slots")
        for missing in missing_slots:
            st.write(
                f"- Day {missing['day']} — "
                f"{missing['meal_slot'].title()}"
            )

    st.info(
        "Try lowering the minimum protein, removing an exclusion, "
        "changing the diet, or requesting fewer meal slots."
    )

    cancel_column, modify_column = st.columns(2)

    if cancel_column.button("Cancel", key="planning-failure-cancel"):
        reset_to_default_planner()
        st.rerun()

    if modify_column.button("Modify Settings", key="planning-failure-modify"):
        st.session_state.planner_mode = "modify"
        st.rerun()


def show_replacement_failure(result, current_interrupt):
    """Show an explicit outcome when no valid replacement recipe is found."""
    st.error("Could not find a suitable replacement")

    message = (
        current_interrupt.get("message")
        or result.get("planning_message")
        or "No alternative recipe matched the current requirements."
    )
    st.write(message)

    st.info(
        "Keep the current recipe, modify the plan settings, "
        "or cancel the current plan."
    )

    keep_column, modify_column, cancel_column = st.columns(3)

    if keep_column.button("Keep Current", key="replacement-failure-keep"):
        resume_graph({"action": "keep_current"})

    if modify_column.button("Modify Settings", key="replacement-failure-modify"):
        st.session_state.planner_mode = "modify"
        st.rerun()

    if cancel_column.button("Cancel", key="replacement-failure-cancel"):
        reset_to_default_planner()
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
    """Render configure, active-review, and modify modes explicitly."""
    st.title("Meal Plan & Shop Agent")
    st.caption(
        "Agent 1 plans · Agent 2 validates · "
        "Agent 3 shops and checks budget"
    )

    result = st.session_state.graph_result
    mode = st.session_state.planner_mode
    settings = st.session_state.plan_settings

    # CONFIGURE / MODIFY — editable settings.
    if mode in {"configure", "modify"}:
        is_modify = mode == "modify"

        st.subheader(
            "Modify Requirements"
            if is_modify
            else "Your Requirements"
        )

        with st.form(
            "modify_requirements"
            if is_modify
            else "create_requirements"
        ):
            days = st.number_input(
                "Number of days",
                min_value=1,
                max_value=7,
                value=int(settings["days"]),
            )

            diets = ["Vegan", "Vegetarian"]
            diet = st.selectbox(
                "Diet",
                diets,
                index=diets.index(settings["diet"]),
            )

            st.write("Meals")
            breakfast = st.checkbox(
                "Breakfast",
                value=settings["breakfast"],
            )
            lunch = st.checkbox(
                "Lunch",
                value=settings["lunch"],
            )
            dinner = st.checkbox(
                "Dinner",
                value=settings["dinner"],
            )

            excluded_text = st.text_input(
                "Excluded ingredients",
                value=settings["excluded_text"],
                placeholder="soy, mushroom, tomatoes",
            )

            min_protein = st.number_input(
                "Minimum protein per meal (g)",
                min_value=0.0,
                value=float(settings["min_protein"]),
            )

            budget = st.number_input(
                "Budget ($)",
                min_value=0.0,
                value=float(settings["budget"]),
            )

            st.caption(
                "Enter $0 for any budget. "
                "When specified, the minimum budget is $3."
            )

            if is_modify:
                cancel_changes, update_plan = st.columns(2)
                cancel_clicked = cancel_changes.form_submit_button(
                    "Cancel Changes"
                )
                submit_clicked = update_plan.form_submit_button(
                    "Update Meal Plan"
                )
            else:
                cancel_clicked = False
                submit_clicked = st.form_submit_button(
                    "Create Meal Plan"
                )

        if cancel_clicked:
            st.session_state.planner_mode = "active"
            st.rerun()

        if submit_clicked:
            if 0 < budget < 3:
                st.error(
                    "Enter $0 for any budget, "
                    "or enter a budget of at least $3."
                )
                return

            meal_slots = []
            if breakfast:
                meal_slots.append("breakfast")
            if lunch:
                meal_slots.append("lunch")
            if dinner:
                meal_slots.append("dinner")

            if not meal_slots:
                st.error(
                    "Select at least one meal: "
                    "Breakfast, Lunch, or Dinner."
                )
                return

            updated_settings = {
                "days": int(days),
                "diet": diet,
                "breakfast": breakfast,
                "lunch": lunch,
                "dinner": dinner,
                "excluded_text": excluded_text,
                "min_protein": float(min_protein),
                "budget": float(budget),
            }

            st.session_state.plan_settings = updated_settings
            st.session_state.thread_id = (
                f"meal-plan-{uuid.uuid4()}"
            )
            st.session_state.replacement_target = None
            st.session_state.show_cost_replacement = False
            st.session_state.history_plan_id = None
            st.session_state.planner_mode = "active"

            excluded = [
                item.strip()
                for item in excluded_text.split(",")
                if item.strip()
            ]

            initial_state = {
                "user_request": "Create a meal plan",
                "days": int(days),
                "meal_slots": meal_slots,
                "diet": diet,
                "excluded_ingredients": excluded,
                "min_protein_per_meal": (
                    min_protein
                    if min_protein > 0
                    else None
                ),
                "budget": (
                    None
                    if budget == 0
                    else budget
                ),
            }

            with st.spinner(
                "Agents are building and validating your plan..."
            ):
                st.session_state.graph_result = (
                    meal_plan_graph.invoke(
                        initial_state,
                        config=graph_config(),
                    )
                )

            # Force a fresh render in ACTIVE mode. This guarantees the
            # Create button/settings cannot remain enabled after execution.
            st.rerun()

        return

    # ACTIVE — settings are visible but read-only.
    st.subheader("Current Requirements")

    requirements_columns = st.columns(2)
    requirements_columns[0].write(
        f"**Days:** {settings['days']}"
    )
    requirements_columns[0].write(
        f"**Diet:** {settings['diet']}"
    )

    selected_meals = [
        label.title()
        for label in ["breakfast", "lunch", "dinner"]
        if settings[label]
    ]
    requirements_columns[0].write(
        f"**Meals:** {', '.join(selected_meals)}"
    )

    exclusions = settings["excluded_text"].strip()
    requirements_columns[1].write(
        f"**Excluded:** {exclusions or 'None'}"
    )
    requirements_columns[1].write(
        "**Minimum protein:** "
        f"{settings['min_protein']:.0f}g"
    )
    requirements_columns[1].write(
        "**Budget:** "
        + (
            "Any"
            if settings["budget"] == 0
            else f"${settings['budget']:.2f}"
        )
    )

    if not result:
        st.error(
            "The workflow is active but no graph result is available. "
            "Cancel and create the plan again."
        )
        if st.button("Cancel", key="active-no-result-cancel"):
            reset_to_default_planner()
            st.rerun()
        return

    show_agent_progress(result)

    meal_plan = result.get("draft_meal_plan", [])
    current_interrupt = get_interrupt(result)
    interrupt_type = (
        current_interrupt.get("type")
        if current_interrupt
        else None
    )

    if interrupt_type == "budget_failure":
        show_budget_failure(
            result,
            current_interrupt,
        )

    elif interrupt_type == "pricing_unknown":
        show_pricing_unknown(
            result,
            current_interrupt,
        )

    elif interrupt_type == "planning_failure":
        show_planning_failure(
            result,
            current_interrupt,
        )

    elif interrupt_type == "replacement_failure":
        show_replacement_failure(
            result,
            current_interrupt,
        )

    elif interrupt_type == "meal_plan_review":
        show_meal_plan(
            meal_plan,
            allow_replacement=True,
        )
        show_replacement_form()
        st.divider()

        cancel_column, modify_column, approve_column = (
            st.columns(3)
        )

        if cancel_column.button(
            "Cancel",
            key="meal-review-cancel",
        ):
            reset_to_default_planner()
            st.rerun()

        if modify_column.button(
            "Modify Settings",
            key="meal-review-modify",
        ):
            st.session_state.planner_mode = "modify"
            st.rerun()

        if approve_column.button(
            "Approve Meal Plan →",
            key="meal-review-approve",
        ):
            resume_graph({
                "action": "approve",
                "feedback": None,
            })

    elif interrupt_type == "shopping_review":
        show_meal_plan(meal_plan)
        show_pricing(result)
        st.divider()

        if st.session_state.show_cost_replacement:
            show_cost_replacement(
                meal_plan,
                resume_action="find_cheaper_meal",
            )

        cancel_column, cheaper_column, approve_column = (
            st.columns(3)
        )

        if cancel_column.button(
            "Cancel",
            key="shopping-review-cancel",
        ):
            reset_to_default_planner()
            st.rerun()

        if cheaper_column.button(
            "Find Cheaper Meal",
            key="shopping-review-cheaper",
        ):
            st.session_state.show_cost_replacement = True
            st.rerun()

        if approve_column.button(
            "Approve Shopping Plan →",
            key="shopping-review-approve",
        ):
            resume_graph({
                "action": "approve",
            })

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
