# UI Cost Loop Fix

Built from the planner-mode UI.

Fixes:
1. Active/review stages show Current Requirements as solid read-only text and
   no longer show a disabled Create Meal Plan button.
2. Budget-failure cheaper-meal flow now resumes the `budget_failure` interrupt
   with `action="try_cheaper_meal"`.
3. Normal shopping-review cheaper-meal flow continues to use
   `action="find_cheaper_meal"`.

Why bug 2 happened:
- `budget_failure` graph routing expects `try_cheaper_meal`.
- The shared UI was sending `find_cheaper_meal`.
- The router therefore fell through to Cancel.

Backend files are unchanged.
