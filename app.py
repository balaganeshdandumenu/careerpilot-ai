from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from flask_wtf.csrf import CSRFError

from config.config import Config
from routes.career_routes import career_bp
from routes.dashboard_routes import dashboard_bp
from routes.health_routes import health_bp
from routes.resources_routes import resources_bp
from routes.resume_routes import resume_bp

csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    csrf.init_app(app)
    app.register_blueprint(health_bp)
    app.register_blueprint(career_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(resources_bp)

    @app.errorhandler(413)
    def upload_too_large(_error):
        return render_template("error.html", title="That file is too large.", message="Choose a PDF, DOCX, or TXT file under 5 MB and try again."), 413

    @app.errorhandler(CSRFError)
    def invalid_form_token(_error):
        return render_template("error.html", title="Please refresh and try again.", message="This form could not be verified, or your session expired. Your uploaded files are not retained."), 400

    @app.errorhandler(429)
    def too_many_requests(_error):
        return render_template("error.html", title="Let’s take a short pause.", message="This action has been requested several times. Wait a minute, then try again."), 429

    @app.get("/")
    def home():
        return render_template("index.html")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])