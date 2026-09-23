# Assignment 3 UI V3 — Clean Flow

Replace `app/streamlit_app.py` with this file.

Changes:
- no New Plan button anywhere;
- Meal Planner shows default settings whenever no workflow is active;
- Stage 2 uses Cancel / Modify Settings / Approve Meal Plan;
- per-recipe Replace remains the only recipe replacement control;
- Stage 3 uses Cancel / Find Cheaper Meal / Approve Shopping Plan;
- Done saves the completed plan to right-side History and resets Meal Planner;
- left navigation remains Meal Planner / Recipe Browser / Receipts & Bills;
- right column remains Plan History only.

`data/plan_history.json` is runtime data and should remain in `.gitignore`.

After copying:
1. `python -m pytest -q`
2. `python -m streamlit run app/streamlit_app.py`
