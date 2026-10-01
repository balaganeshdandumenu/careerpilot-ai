import re

from services.career_service import load_data

SECTION_NAMES = {"experience", "work experience", "education", "projects", "skills", "certifications", "summary", "professional summary", "objective"}


def _detect_name(lines):
    for line in lines[:5]:
        candidate = line.strip()
        if candidate and "@" not in candidate and len(candidate) < 64 and candidate.casefold() not in SECTION_NAMES and re.fullmatch(r"[A-Za-z][A-Za-z .'-]+", candidate):
            return candidate
    return "Not confidently detected"


def _contains_phrase(text, phrase):
    return re.search(r"(?<![A-Za-z0-9+#])" + re.escape(phrase) + r"(?![A-Za-z0-9+#])", text, re.IGNORECASE) is not None


def analyze_resume(text, role):
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    lines = normalized.splitlines()
    all_skills = load_data("skills.json")
    known_skills = list(dict.fromkeys(skill for skills in all_skills.values() for skill in skills))
    detected_skills = [skill for skill in known_skills if _contains_phrase(normalized, skill)]
    matched = [skill for skill in role["skills"] if _contains_phrase(normalized, skill)]
    missing = [skill for skill in role["skills"] if skill not in matched]
    score = round(100 * len(matched) / max(len(role["skills"]), 1))

    sections = {name: any(line.casefold().strip(" :") == name for line in lines) for name in SECTION_NAMES}
    education = [line for line in lines if re.search(r"\b(university|college|bachelor|master|b\.s\.|b\.tech|m\.s\.|degree|diploma)\b", line, re.I)][:4]
    project_lines = [line for line in lines if re.search(r"\b(project|built|developed|created|implemented)\b", line, re.I)][:5]
    certification_lines = [line for line in lines if re.search(r"\b(certified|certification|certificate)\b", line, re.I)][:4]
    experience_lines = [line for line in lines if re.search(r"\b(engineer|developer|analyst|intern|manager|years? of experience)\b", line, re.I)][:4]

    dimensions = [
        {"name": "Keyword alignment", "score": score, "explanation": f"{len(matched)} of {len(role['skills'])} target-role skills appear in the resume text."},
        {"name": "Formatting structure", "score": 85 if len(lines) > 8 else 55, "explanation": "Estimated from readable text extraction; visual layout cannot be fully assessed here."},
        {"name": "Section organization", "score": min(100, 30 + 15 * sum(sections[name] for name in ("experience", "education", "projects", "skills", "certifications"))), "explanation": "Based on recognizable section headings in the extracted text."},
        {"name": "Role relevance", "score": score, "explanation": "Measures overlap between visible resume skills and the selected role's curated skill list."},
        {"name": "Skills coverage", "score": score, "explanation": "Counts role skills that are explicitly mentioned; it does not judge proficiency."},
        {"name": "Experience evidence", "score": min(100, 35 + 20 * bool(project_lines) + 15 * bool(experience_lines)), "explanation": "Looks for project and experience evidence; it does not verify claims."},
    ]
    ats_score = round(sum(item["score"] for item in dimensions) / len(dimensions))

    recommendations = []
    if missing:
        recommendations.append({"priority": "high", "problem": f"Role keywords not found: {', '.join(missing[:4])}.", "why": "A reviewer needs clear evidence of relevant skills, and automated filters may look for role language.", "action": "If you have used these skills, add them in the context of a real project or experience. Otherwise, build evidence before listing them."})
    if not project_lines:
        recommendations.append({"priority": "high", "problem": "Project evidence is hard to identify in the extracted text.", "why": "Projects can show applied skills, especially when professional experience is still growing.", "action": "Add a Projects section describing the problem, what you built, the tools used, and an outcome you actually measured."})
    if not sections["skills"]:
        recommendations.append({"priority": "medium", "problem": "A dedicated Skills section was not detected.", "why": "A compact skills list helps readers scan for relevant experience.", "action": "Add a concise Skills section containing only tools and techniques you can discuss confidently."})
    recommendations.append({"priority": "low", "problem": "Keep each experience bullet specific and easy to scan.", "why": "Concrete actions and verified outcomes help a reader understand your contribution.", "action": "Use action + context + result where known; do not add estimated metrics or outcomes you cannot substantiate."})

    return {
        "name": _detect_name(lines),
        "skills": detected_skills,
        "education": education,
        "projects": project_lines,
        "certifications": certification_lines,
        "experience": experience_lines,
        "matched": matched,
        "missing": missing,
        "dimensions": dimensions,
        "ats_score": ats_score,
        "recommendations": recommendations,
        "word_count": len(normalized.split()),
    }