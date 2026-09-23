def build_grocery_list(meal_plan):
    """
    STEP 7 — Agent 3 extracts ingredient lines from the approved meal plan.

    V1 keeps ingredient quantities and units exactly as written.
    Ingredient normalization is intentionally out of scope.
    """
    grocery_items = []

    for meal in meal_plan:
        recipe = meal["recipe"]
        recipe_text = recipe.get(
            "recipe_text",
            "",
        )

        in_ingredients_section = False

        for line in recipe_text.splitlines():
            stripped_line = line.strip()

            if stripped_line == "Ingredients:":
                in_ingredients_section = True
                continue

            if stripped_line == "Nutrition:":
                break

            if (
                in_ingredients_section
                and stripped_line.startswith("- ")
            ):
                grocery_items.append({
                    "ingredient_line": stripped_line[2:],
                    "recipe_name": recipe["recipe_name"],
                    "day": meal["day"],
                    "meal_slot": meal["meal_slot"],
                })

    return grocery_items


