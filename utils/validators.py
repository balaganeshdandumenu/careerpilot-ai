ALLOWED_PREFERENCES = {"video", "documentation", "hands-on", "projects", "mixed"}


def validate_profile(form):
    errors = {}
    name = form.get("name", "").strip()
    if not name or len(name) > 80:
        errors["name"] = "Add your name (up to 80 characters)."

    role_id = form.get("target_role", "").strip()
    if role_id not in {"ai-ml-engineer", "data-analyst", "frontend-developer", "backend-developer"}:
        errors["target_role"] = "Choose a role from the list."

    experience_level = form.get("experience_level", "student")
    if experience_level not in {"student", "fresher", "experienced"}:
        experience_level = "student"

    try:
        hours = float(form.get("hours_per_day", "0"))
        if not 0.25 <= hours <= 12:
            raise ValueError
    except (TypeError, ValueError):
        hours = 0
        errors["hours_per_day"] = "Choose between 15 minutes and 12 hours per day."

    try:
        days = int(form.get("days_per_week", "0"))
        if not 1 <= days <= 7:
            raise ValueError
    except (TypeError, ValueError):
        days = 0
        errors["days_per_week"] = "Choose between 1 and 7 days per week."

    skills = []
    for skill in form.getlist("skills"):
        cleaned = " ".join(skill.strip().split())
        if cleaned and len(cleaned) <= 40 and cleaned.casefold() not in {item.casefold() for item in skills}:
            skills.append(cleaned)
    if len(skills) > 30:
        errors["skills"] = "Keep your list to 30 skills or fewer."

    preferences = [value for value in form.getlist("preferences") if value in ALLOWED_PREFERENCES]
    if not preferences:
        preferences = ["mixed"]

    return {
        "profile": {
            "name": name,
            "target_role": role_id,
            "experience_level": experience_level,
            "skills": skills,
            "education": form.get("education", "").strip()[:160],
            "projects": form.get("projects", "").strip()[:1000],
            "certifications": form.get("certifications", "").strip()[:500],
            "experience": form.get("experience", "").strip()[:1000],
            "hours_per_day": hours,
            "days_per_week": days,
            "preferences": preferences,
        },
        "errors": errors,
    }