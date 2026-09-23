import uuid

import streamlit as st
from langgraph.types import Command

from src.graph import meal_plan_graph


st.set_page_config(
    page_title="Meal Plan & Shop Agent",
    layout="wide",
)


def initialize_session():
    """Create Streamlit state used to resume the LangGraph workflow."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = (
            f"meal-plan-{uuid.uuid4()}"
        )

    if "graph_result" not in st.session_state:
        st.session_state.graph_result = None


def graph_config():
    """Return the persistent LangGraph thread configuration."""
    return {
        "configurable": {
            "thread_id":
                st.session_state.thread_id
        }
    }


def reset_workflow():
    """Start a completely new meal-planning workflow."""
    st.session_state.thread_id = (
        f"meal-plan-{uuid.uuid4()}"
    )

    st.session_state.graph_result = None


def display_agent_progress(result):
    """Show how far the workflow has progressed."""
    st.subheader("Agent workflow")

    if result.get("draft_meal_plan"):
        st.success(
            "Agent 1 — Meal plan created"
        )
    else:
        st.info(
            "Agent 1 — Waiting"
        )

    validation_status = result.get(
        "validation_status"
    )

    if validation_status == "PASS":
        st.success(
            "Agent 2 — Nutrition & safety passed"
        )
    elif validation_status == "FAIL":
        st.error(
            "Agent 2 — Validation failed"
        )
    elif validation_status == "NEEDS_REVIEW":
        st.warning(
            "Agent 2 — Human review required"
        )
    else:
        st.info(
            "Agent 2 — Waiting"
        )

    if result.get("grocery_list"):
        st.success(
            "Agent 3 — Shopping & budget started"
        )
    else:
        st.info(
            "Agent 3 — Waiting"
        )


def display_meal_plan(meal_plan):
    """Display the current draft meal plan grouped by day."""
    st.subheader("Meal plan")

    days = sorted({
        meal["day"]
        for meal in meal_plan
    })

    for day in days:
        st.markdown(
            f"### Day {day}"
        )

        day_meals = [
            meal
            for meal in meal_plan
            if meal["day"] == day
        ]

        for meal in day_meals:
            recipe = meal["recipe"]

            st.markdown(
                f"**{meal['meal_slot'].title()}** — "
                f"{recipe['recipe_name']}"
            )

            protein = recipe.get(
                "protein_per_serving"
            )

            if protein is not None:
                st.caption(
                    f"Protein: {protein:.1f} g/serving"
                )


def display_shopping_result(result):
    """Display Agent 3 pricing and budget information."""
    grocery_list = result.get(
        "priced_grocery_list",
        []
    )

    if not grocery_list:
        return

    st.subheader(
        "Shopping & budget"
    )

    st.write(
        f"Budget status: "
        f"**{result.get('budget_status')}**"
    )

    estimated_total = result.get(
        "estimated_total"
    )

    if estimated_total is not None:
        st.write(
            f"Known subtotal: "
            f"**${estimated_total:.2f}**"
        )

    pricing_errors = result.get(
        "pricing_errors",
        []
    )

    if pricing_errors:
        st.warning(
            "Some grocery prices were unavailable. "
            "The agent did not invent missing prices."
        )

        for error in pricing_errors:
            st.write(
                f"- {error}"
            )


def get_interrupt(result):
    """Return the current LangGraph interrupt, if one exists."""
    interrupts = result.get(
        "__interrupt__",
        []
    )

    if not interrupts:
        return None

    return interrupts[0].value


initialize_session()

st.title(
    "Meal Plan & Shop Agent"
)

st.caption(
    "Three-agent LangGraph workflow with MCP tools, "
    "human approval, and persistent checkpoints."
)


# STEP 1 — Collect user requirements.
with st.form(
    "meal_plan_form"
):
    days = st.number_input(
        "Number of days",
        min_value=1,
        max_value=7,
        value=1,
    )

    diet = st.selectbox(
        "Diet",
        [
            "Vegan",
            "Vegetarian",
        ],
    )

    st.write(
        "Meals"
    )

    breakfast = st.checkbox(
        "Breakfast",
        value=True,
    )

    lunch = st.checkbox(
        "Lunch",
        value=True,
    )

    dinner = st.checkbox(
        "Dinner",
        value=True,
    )

    excluded_text = st.text_input(
        "Excluded ingredients",
        placeholder="soy, mushroom",
    )

    min_protein = st.number_input(
        "Minimum protein per meal (g)",
        min_value=0.0,
        value=0.0,
    )

    budget = st.number_input(
        "Budget ($)",
        min_value=0.0,
        value=75.0,
    )

    submitted = st.form_submit_button(
        "Create Meal Plan"
    )


if submitted:
    meal_slots = []

    if breakfast:
        meal_slots.append(
            "breakfast"
        )

    if lunch:
        meal_slots.append(
            "lunch"
        )

    if dinner:
        meal_slots.append(
            "dinner"
        )

    excluded_ingredients = [
        item.strip()
        for item in excluded_text.split(",")
        if item.strip()
    ]

    reset_workflow()

    initial_state = {
        "user_request": (
            "Create a meal plan"
        ),
        "days": int(days),
        "meal_slots": meal_slots,
        "diet": diet,
        "excluded_ingredients":
            excluded_ingredients,
        "min_protein_per_meal": (
            min_protein
            if min_protein > 0
            else None
        ),
        "budget": (
            budget
            if budget > 0
            else None
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


result = (
    st.session_state.graph_result
)

if result:
    display_agent_progress(
        result
    )

    meal_plan = result.get(
        "draft_meal_plan",
        []
    )

    if meal_plan:
        display_meal_plan(
            meal_plan
        )

    display_shopping_result(
        result
    )

    current_interrupt = get_interrupt(
        result
    )

    if current_interrupt:
        interrupt_type = (
            current_interrupt.get(
                "type"
            )
        )

        # STEP 6 — Human reviews Agent 1 + Agent 2 output.
        if (
            interrupt_type
            == "meal_plan_approval"
        ):
            st.subheader(
                "Human review"
            )

            st.write(
                "Agent 2 validated the plan. "
                "Approve it before Agent 3 starts shopping."
            )

            approve_column, decline_column = (
                st.columns(2)
            )

            with approve_column:
                if st.button(
                    "Approve Meal Plan"
                ):
                    st.session_state.graph_result = (
                        meal_plan_graph.invoke(
                            Command(
                                resume={
                                    "action": "approve",
                                    "feedback": None,
                                }
                            ),
                            config=graph_config(),
                        )
                    )

                    st.rerun()

            with decline_column:
                if st.button(
                    "Decline Meal Plan"
                ):
                    st.session_state.graph_result = (
                        meal_plan_graph.invoke(
                            Command(
                                resume={
                                    "action": "decline",
                                    "feedback": None,
                                }
                            ),
                            config=graph_config(),
                        )
                    )

                    st.rerun()

        # STEP 10 — Human reviews Agent 3's final shopping result.
        elif (
            interrupt_type
            == "final_shopping_approval"
        ):
            st.subheader(
                "Final approval"
            )

            approve_column, decline_column = (
                st.columns(2)
            )

            with approve_column:
                if st.button(
                    "Approve Final Plan"
                ):
                    st.session_state.graph_result = (
                        meal_plan_graph.invoke(
                            Command(
                                resume={
                                    "action": "approve",
                                    "feedback": None,
                                }
                            ),
                            config=graph_config(),
                        )
                    )

                    st.rerun()

            with decline_column:
                if st.button(
                    "Decline Final Plan"
                ):
                    st.session_state.graph_result = (
                        meal_plan_graph.invoke(
                            Command(
                                resume={
                                    "action": "decline",
                                    "feedback": None,
                                }
                            ),
                            config=graph_config(),
                        )
                    )

                    st.rerun()

    final_response = result.get(
        "final_response"
    )

    if final_response:
        st.success(
            final_response
        )


