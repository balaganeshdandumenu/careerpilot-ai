from flask import Blueprint, render_template

from services.career_service import load_data

resources_bp = Blueprint("resources", __name__, url_prefix="/resources")


@resources_bp.get("")
def index():
    return render_template("resources.html", resources=load_data("resources.json"))