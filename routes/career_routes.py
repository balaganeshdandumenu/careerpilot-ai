import json
import logging
from datetime import date
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from google.genai import types

from services.career_service import generate_plan, get_roles, load_data
from services.gemini_service import AIServiceError, generate_json
from services.rate_limit_service import rate_limit
from services.session_store import load_career_data, save_career_data
from utils.validators import validate_profile

logger = logging.getLogger(__name__)
career_bp = Blueprint("career", __name__, url_prefix="/career")
PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


@career_bp.get("")
def profile():
    saved_profile = load_career_data(session).get("profile", {})
    return render_template(
        "career.html",
        roles=get_roles(),
        skill_categories=load_data("skills.json"),
        saved_profile=saved_profile,
        errors={},
    )


@career_bp.post("/generate")
@rate_limit("career_generate", 30, 60)
def generate():
    result = validate_profile(request.form)
    if result["errors"]:
        return render_template(
            "career.html",
            roles=get_roles(),
            skill_categories=load_data("skills.json"),
            saved_profile=result["profile"],
            errors=result["errors"],
        ), 400

    profile_data = result["profile"]
    plan = generate_plan(profile_data)
    plan["gap_reasons"] = {skill: f"{skill} is used in {plan['role']['title']} work; practicing it helps turn a skill label into demonstrable experience." for skill in plan["missing"]}
    key = current_app.config.get("GEMINI_API_KEY")
    prompt_file = PROMPT_DIR / "career_prompt.txt"
    if key:
        try:
            prompt = prompt_file.read_text(encoding="utf-8").replace("{{PROFILE}}", json.dumps({
                "role": plan["role"]["title"],
                "experience_level": profile_data["experience_level"],
                "matched": plan["matched"],
                "developing": plan["developing"],
                "missing": plan["missing"][:8],
                "schedule_note": plan["schedule_note"],
            }))
            schema = types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "summary": types.Schema(type=types.Type.STRING),
                    "gap_reasons": types.Schema(type=types.Type.ARRAY, items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={"skill": types.Schema(type=types.Type.STRING), "reason": types.Schema(type=types.Type.STRING)},
                        required=["skill", "reason"],
                    )),
                },
                required=["summary", "gap_reasons"],
            )
            ai_result = generate_json(key, prompt, schema)
            if isinstance(ai_result.get("summary"), str) and 10 <= len(ai_result["summary"]) <= 360:
                plan["summary"] = ai_result["summary"]
            if isinstance(ai_result.get("gap_reasons"), list):
                allowed = {skill.casefold(): skill for skill in plan["missing"]}
                for item in ai_result["gap_reasons"][:8]:
                    skill = item.get("skill", "").casefold() if isinstance(item, dict) else ""
                    reason = item.get("reason", "") if isinstance(item, dict) else ""
                    if skill in allowed and isinstance(reason, str) and 15 <= len(reason) <= 240:
                        plan["gap_reasons"][allowed[skill]] = reason
            plan["ai_status"] = "ready"
        except AIServiceError as error:
            logger.warning("Career plan uses deterministic fallback; AI status=%s", error.code)
            plan["ai_status"] = error.code
            flash("Your plan is ready using curated role data. AI explanations are temporarily unavailable.", "info")
    else:
        plan["ai_status"] = "missing_key"
        flash("Your plan uses curated role data. Add an AI key on the server to enable tailored explanations.", "info")

    save_career_data(session, {
        "profile": profile_data,
        "summary": plan["summary"],
        "gap_reasons": plan["gap_reasons"],
        "ai_status": plan["ai_status"],
        "progress": plan["progress"],
    })
    return redirect(url_for("career.report"))


@career_bp.get("/report")
def report():
    saved = load_career_data(session)
    if not saved or not saved.get("profile"):
        return render_template("empty.html", kind="career"), 200
    plan = generate_plan(saved["profile"])
    plan.update({key: value for key, value in saved.items() if key != "profile"})
    return render_template("career_result.html", plan=plan)


@career_bp.get("/roadmap")
def roadmap():
    saved = load_career_data(session)
    if not saved or not saved.get("profile"):
        return redirect(url_for("career.profile"))
    plan = generate_plan(saved["profile"])
    plan.update({key: value for key, value in saved.items() if key != "profile"})
    return render_template("roadmap.html", plan=plan)


@career_bp.post("/roadmap/complete")
def complete_day():
    saved = load_career_data(session)
    try:
        day_number = int(request.form.get("day", "0"))
    except ValueError:
        day_number = 0
    if saved and 1 <= day_number <= 30:
        progress = saved.get("progress", {})
        completed = set(progress.get("completed", []))
        completed.add(day_number)
        completed_on = progress.get("completed_on", {})
        completed_on[str(day_number)] = date.today().isoformat()
        saved["progress"] = {"completed": sorted(completed), "total": 30, "completed_on": completed_on}
        save_career_data(session, saved)
        flash(f"Day {day_number} completed. Your progress is moving forward.", "success")
    destination = "dashboard.dashboard" if request.form.get("return_to") == "dashboard" else "career.roadmap"
    return redirect(url_for(destination))