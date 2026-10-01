from flask import Blueprint, current_app, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/api/health")
def health():
    return jsonify({"status": "ok", "ai_configured": bool(current_app.config.get("GEMINI_API_KEY"))})