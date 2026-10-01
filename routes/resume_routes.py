from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from services.ats_service import enrich_recommendations
from services.career_service import get_roles, load_data
from services.rate_limit_service import rate_limit
from services.resume_service import analyze_resume
from services.session_store import load_career_data, save_career_data
from utils.file_parser import extract_resume_text

resume_bp = Blueprint("resume", __name__, url_prefix="/resume")


@resume_bp.get("")
def analyzer():
    return render_template("resume.html", roles=get_roles(), errors={})


@resume_bp.post("/analyze")
@rate_limit("resume_analyze", 8, 60)
def analyze():
    uploaded = request.files.get("resume")
    target_role = request.form.get("target_role", "")
    role = next((item for item in get_roles() if item["id"] == target_role), None)
    errors = {}
    if not uploaded or not uploaded.filename:
        errors["resume"] = "Choose a PDF, DOCX, or TXT resume to analyze."
    elif "." not in uploaded.filename or uploaded.filename.rsplit(".", 1)[1].lower() not in current_app.config["ALLOWED_EXTENSIONS"]:
        errors["resume"] = "That file type is not supported. Choose a PDF, DOCX, or TXT file."
    if not role:
        errors["target_role"] = "Choose a target role from the list."
    if errors:
        return render_template("resume.html", roles=get_roles(), errors=errors), 400

    try:
        content = uploaded.stream.read(current_app.config["MAX_CONTENT_LENGTH"] + 1)
        if len(content) > current_app.config["MAX_CONTENT_LENGTH"]:
            raise ValueError("The file is larger than 5 MB. Choose a smaller file.")
        resume_text = extract_resume_text(uploaded.filename, content)
        if len(resume_text.strip()) < 40:
            raise ValueError("We couldn't find enough readable text. Try an accessible PDF, DOCX, or TXT file.")
        analysis = analyze_resume(resume_text, role)
        analysis["ai_status"] = enrich_recommendations(analysis, role, current_app.config.get("GEMINI_API_KEY"))
    except ValueError as error:
        return render_template("resume.html", roles=get_roles(), errors={"resume": str(error)}), 400
    except Exception:
        current_app.logger.exception("Resume parsing failed")
        return render_template("resume.html", roles=get_roles(), errors={"resume": "We couldn't read this file. Check that it opens correctly, then try again."}), 400

    saved = load_career_data(session)
    saved["resume_summary"] = {"ats_score": analysis["ats_score"], "matched_count": len(analysis["matched"]), "role": role["title"]}
    saved["resume_report"] = {"role_id": role["id"], "analysis": analysis}
    save_career_data(session, saved)
    flash("This compatibility indicator is an estimate based on visible resume text, not an official ATS result.", "info")
    return render_template("resume_result.html", analysis=analysis, role=role)


@resume_bp.get("/report")
def report():
    saved = load_career_data(session)
    report_data = saved.get("resume_report")
    if not report_data:
        return redirect(url_for("resume.analyzer"))
    role = next((item for item in get_roles() if item["id"] == report_data["role_id"]), None)
    if not role:
        return redirect(url_for("resume.analyzer"))
    return render_template("resume_result.html", analysis=report_data["analysis"], role=role)