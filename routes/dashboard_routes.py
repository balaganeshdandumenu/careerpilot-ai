from datetime import date, timedelta

from flask import Blueprint, render_template, session

from services.career_service import generate_plan
from services.session_store import load_career_data

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard")
def dashboard():
    saved = load_career_data(session)
    if not saved or not saved.get("profile"):
        return render_template("empty.html", kind="dashboard")
    plan = generate_plan(saved["profile"])
    plan.update({key: value for key, value in saved.items() if key != "profile"})
    completed = plan.get("progress", {}).get("completed", [])
    next_day = next((day for day in plan["roadmap"] if day["day"] not in completed and not day["is_rest"]), plan["roadmap"][0])
    completed_dates = set(plan.get("progress", {}).get("completed_on", {}).values())
    streak_day = date.today() if date.today().isoformat() in completed_dates else date.today() - timedelta(days=1)
    learning_streak = 0
    while streak_day.isoformat() in completed_dates:
        learning_streak += 1
        streak_day -= timedelta(days=1)
    return render_template("dashboard.html", plan=plan, next_day=next_day, learning_streak=learning_streak)