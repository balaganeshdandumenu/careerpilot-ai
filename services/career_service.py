import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_data(filename):
    with (DATA_DIR / filename).open(encoding="utf-8") as data_file:
        return json.load(data_file)


def get_roles():
    return load_data("career_roles.json")


def _resource_for(skill, resources):
    return next((item for item in resources if skill.casefold() in [name.casefold() for name in item["skills"]]), None)


def generate_plan(profile):
    roles = get_roles()
    role = next((item for item in roles if item["id"] == profile["target_role"]), roles[0])
    current_skills = {skill.casefold() for skill in profile["skills"]}
    role_skills = role["skills"]
    matched = [skill for skill in role_skills if skill.casefold() in current_skills]
    developing = [skill for skill in role_skills if skill.casefold() not in current_skills and any(skill.casefold() in current for current in current_skills)]
    missing = [skill for skill in role_skills if skill not in matched and skill not in developing]
    readiness = round(100 * (len(matched) + len(developing) * 0.5) / max(len(role_skills), 1))
    profile_fields = [
        bool(profile["name"]),
        bool(profile["target_role"]),
        bool(profile["skills"]),
        bool(profile["education"] or profile["projects"] or profile["certifications"] or profile["experience"]),
        bool(profile["hours_per_day"] and profile["days_per_week"]),
        bool(profile["preferences"]),
    ]
    profile_completeness = round(100 * sum(profile_fields) / len(profile_fields))
    resources = load_data("resources.json")
    projects = load_data("project_templates.json")
    portals = load_data("job_portals.json")
    certifications = load_data("certifications.json")

    hours = profile["hours_per_day"]
    days_per_week = profile["days_per_week"]
    minutes_available = hours * 60
    focus_skills = missing or role_skills[-3:]
    preferences = profile["preferences"]
    roadmap = []
    active_day = 0

    for day in range(1, 31):
        day_of_week = (day - 1) % 7
        is_learning_day = day_of_week < days_per_week
        if not is_learning_day:
            roadmap.append({
                "day": day,
                "week": min((day - 1) // 7 + 1, 4),
                "topic": "Rest, review, or catch up",
                "objective": "Keep the plan flexible and consolidate what you have practiced.",
                "duration": 0,
                "activity": "Take a break or revisit one note from this week's learning.",
                "task": "Write down one question to bring into your next session.",
                "outcome": "A sustainable pace with room for real life.",
                "resource": None,
                "is_rest": True,
            })
            continue

        active_day += 1
        skill = focus_skills[((active_day - 1) * days_per_week // max(days_per_week, 1)) % len(focus_skills)]
        if active_day > 6:
            skill = focus_skills[min((active_day - 1) // 5, len(focus_skills) - 1)]
        resource = _resource_for(skill, resources)
        preference = preferences[(active_day - 1) % len(preferences)] if preferences else "mixed"
        phase = (active_day - 1) % 5
        if phase == 4:
            activity = f"Apply {skill} in a small, role-relevant exercise."
            task = f"Create a short {skill} example and note the decisions you made."
        elif preference == "video":
            activity = f"Watch or follow a lesson on {skill}, then summarize the key idea."
            task = f"Write three takeaways about how {skill} is used in {role['title']} work."
        elif preference == "documentation":
            activity = f"Read the curated {skill} guide and reproduce one example."
            task = f"Adapt one documented {skill} example to a small dataset or use case."
        elif preference == "projects" or preference == "hands-on":
            activity = f"Practice {skill} by building a small working example."
            task = f"Build one focused {skill} feature and record what you tested."
        else:
            activity = f"Learn one {skill} concept, then practice it with a guided exercise."
            task = f"Complete one {skill} exercise and capture the result in your notes."

        roadmap.append({
            "day": day,
            "week": min((day - 1) // 7 + 1, 4),
            "topic": skill,
            "objective": f"Build a practical foundation in {skill} for {role['title']}.",
            "duration": min(minutes_available, resource["minutes"] if resource else 40),
            "activity": activity,
            "task": task,
            "outcome": f"One small piece of evidence of progress in {skill}.",
            "resource": resource,
            "is_rest": False,
        })

    selected_projects = [project for project in projects if project["id"] in role["projects"]]
    job_portals = [portal for portal in portals if profile["experience_level"] in portal["experience"]]
    recommended_certs = [cert for cert in certifications if any(skill in cert["skills"] for skill in missing)]
    next_actions = []
    if missing:
        next_actions.append(f"Start with {missing[0]} using the first roadmap session.")
    if selected_projects:
        next_actions.append(f"Build the {selected_projects[0]['title'].lower()} project to apply your learning.")
    next_actions.append("Capture one real outcome from your practice in your project notes.")
    next_actions.append("Update your resume with evidence you have actually completed.")
    next_actions.append(f"Explore {job_portals[0]['name']} when you are ready to research roles.")

    return {
        "role": role,
        "readiness": readiness,
        "profile_completeness": profile_completeness,
        "summary": f"You already match {len(matched)} of {len(role_skills)} core skills for {role['title']}. This is a planning snapshot, not a prediction of hiring outcomes.",
        "matched": matched,
        "developing": developing,
        "missing": missing,
        "roadmap": roadmap,
        "weeks": [{"number": number, "days": [day for day in roadmap if day["week"] == number]} for number in range(1, 5)],
        "projects": selected_projects,
        "portals": job_portals[:3],
        "certifications": recommended_certs,
        "next_actions": next_actions[:5],
        "progress": {"completed": [], "total": 30},
        "hours_per_day": hours,
        "days_per_week": days_per_week,
        "schedule_note": f"{days_per_week} learning days each week, with {hours:g} hour{'s' if hours != 1 else ''} available per day. Rest days are built into the calendar.",
        "profile": profile,
        "created": True,
    }