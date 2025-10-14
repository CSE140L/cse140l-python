import os
import json
import uuid
import toml
from datetime import datetime
import pytz
from flask import Flask, request, jsonify, abort, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.sqlite import JSON
import jinja2
import logging

app = Flask(__name__)

# --- Database Configuration ---
DATABASE_PATH = os.environ.get("DATABASE_PATH", "reports.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Server Config Hot-Reloading ---
DEFAULT_CONFIG_PATH = "./server_config.toml"
CONFIG_PATH = os.environ.get("REPORT_SERVER_CONFIG_PATH", DEFAULT_CONFIG_PATH)
_server_config_cache = None
_server_config_mtime = 0

def get_server_config():
    """Gets the server config, with hot-reloading."""
    global _server_config_cache, _server_config_mtime
    try:
        mtime = os.path.getmtime(CONFIG_PATH)
        if mtime > _server_config_mtime:
            app.logger.info(f"Detected change in {CONFIG_PATH}. Reloading.")
            with open(CONFIG_PATH, 'r') as f:
                _server_config_cache = toml.load(f)
            _server_config_mtime = mtime
        return _server_config_cache
    except (FileNotFoundError, toml.TomlDecodeError, Exception) as e:
        app.logger.error(f"Could not load or parse {CONFIG_PATH}: {e}")
        return {}

# --- Database Model ---
class Report(db.Model):
    uuid = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lab_number = db.Column(db.Integer, nullable=False)
    student_id = db.Column(db.String, nullable=False)
    report_data = db.Column(JSON, nullable=False)

    __table_args__ = (db.UniqueConstraint('lab_number', 'student_id', name='_lab_student_uc'),)

    def __repr__(self):
        return f'<Report uuid={self.uuid} lab={self.lab_number} student={self.student_id}>'


with app.app_context():
    db.create_all()

# --- Flask App ---

# This should be stored securely, e.g., in environment variables
AUTH_TOKEN = os.environ.get("REPORT_SERVER_AUTH_TOKEN", "SUPER_SECRET_TOKEN")

templates_path = os.path.join(os.path.dirname(__file__), "templates")
loader = jinja2.FileSystemLoader(templates_path)
jinja_env = jinja2.Environment(loader=loader)


def hex_to_bin(hex_string):
    """Converts a hexadecimal string to a binary string."""
    if not isinstance(hex_string, str):
        return hex_string
    try:
        # Remove "0x" prefix and convert to int, then to binary string and remove "0b"
        return bin(int(hex_string, 16))[2:]
    except (ValueError, TypeError):
        return hex_string


jinja_env.filters['hex_to_bin'] = hex_to_bin


def hex_to_dec(hex_string):
    """Converts a hexadecimal string to a decimal string."""
    if not isinstance(hex_string, str):
        return hex_string
    try:
        return str(int(hex_string, 16))
    except (ValueError, TypeError):
        return hex_string


jinja_env.filters['hex_to_dec'] = hex_to_dec


def get_template(name):
    """Gets a Jinja2 template by name."""
    return jinja_env.get_template(name)


@app.errorhandler(404)
def page_not_found(e):
    """Handles 404 errors for unknown paths."""
    template = get_template('404_generic.html.j2')
    return template.render(), 404


@app.route('/report/<uuid:report_uuid>', methods=['GET'])
def report_by_uuid(report_uuid):
    """Gets a report by its UUID."""
    report = db.session.get(Report, str(report_uuid))

    if report is None:
        app.logger.info(f"No report found for uuid {report_uuid}")
        template = get_template('404.html.j2')
        return template.render({"student_id": "Unknown", "lab_number": "Unknown"}), 404

    # Check if the report is locked
    server_config = get_server_config()
    lab_config = server_config.get(f"lab{report.lab_number}", {})
    locked_until_str = lab_config.get("locked_until")

    if locked_until_str:
        try:
            locked_until_dt = datetime.fromisoformat(locked_until_str)
            now_utc = datetime.now(pytz.utc)

            if now_utc < locked_until_dt:
                app.logger.info(f"Access to report {report_uuid} denied (locked until {locked_until_dt})")
                template = get_template('locked.html.j2')
                return template.render(
                    lab_number=report.lab_number,
                    locked_until_str=locked_until_dt.strftime("%B %d, %Y at %I:%M %p %Z"),
                    locked_until_iso=locked_until_str
                ), 403
        except (ValueError, TypeError) as e:
            app.logger.error(f"Could not parse locked_until date '{locked_until_str}': {e}")

    app.logger.info(f"Serving report for lab {report.lab_number} student {report.student_id}")
    template = get_template('report.html.j2')
    return template.render(student_id=report.student_id, **report.report_data)


@app.route('/report/<int:lab_number>/<student_id>', methods=['POST'])
def report(lab_number, student_id):
    """Handles storing student lab reports."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        app.logger.warning(f"Missing or invalid auth header for student {student_id}")
        abort(401, description="Authorization header is missing or invalid.")

    token = auth_header.split(' ')[1]
    if token != AUTH_TOKEN:
        app.logger.warning(f"Invalid auth token for student {student_id}")
        abort(403, description="Invalid authorization token.")

    data = request.get_json()
    if data is None:
        app.logger.error(f"No data provided in POST request for student {student_id}")
        abort(400, description="No data provided in the request.")

    report = db.session.query(Report).filter_by(lab_number=lab_number, student_id=student_id).first()
    if report:
        # Only update report_data if the new data is not just for initialization
        if data != {"init": True}:
            report.report_data = data
    else:
        report = Report(lab_number=lab_number, student_id=student_id, report_data=data)
        db.session.add(report)

    db.session.commit()
    app.logger.info(f"Stored report for lab {lab_number} student {student_id}")

    report_url = url_for('report_by_uuid', report_uuid=report.uuid, _external=True)
    return jsonify({
        "status": "success",
        "message": f"Report for lab {lab_number} student {student_id} stored.",
        "uuid": report.uuid,
        "url": report_url
    }), 201

def main():
    """Starts the Flask server for development."""
    if not app.debug:
        app.logger.setLevel(logging.INFO)

    app.logger.info(f"Starting report server...")
    app.logger.info(f"Database at: {os.path.abspath(DATABASE_PATH)}")
    app.logger.info(f"Server config at: {os.path.abspath(CONFIG_PATH)}")
    app.logger.info(f"Authentication Token: {AUTH_TOKEN}")
    
    # app.run() is for development only.
    # Gunicorn is used for production in the Docker container.
    app.run(host="0.0.0.0", port=1407)

if __name__ == '__main__':
    main()
