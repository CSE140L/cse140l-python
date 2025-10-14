import os
import json
from flask import Flask, request, jsonify, abort
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

# --- Database Model ---
class Report(db.Model):
    lab_number = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String, primary_key=True)
    report_data = db.Column(JSON, nullable=False)

    def __repr__(self):
        return f'<Report lab={self.lab_number} student={self.student_id}>'

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

@app.route('/report/<int:lab_number>/<student_id>', methods=['POST', 'GET'])
def report(lab_number, student_id):
    """Handles storing and retrieving student lab reports."""
    if request.method == 'POST':
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            app.logger.warning(f"Missing or invalid auth header for student {student_id}")
            abort(401, description="Authorization header is missing or invalid.")

        token = auth_header.split(' ')[1]
        if token != AUTH_TOKEN:
            app.logger.warning(f"Invalid auth token for student {student_id}")
            abort(403, description="Invalid authorization token.")

        data = request.get_json()
        if not data:
            app.logger.error(f"No data provided in POST request for student {student_id}")
            abort(400, description="No data provided in the request.")

        report = db.session.get(Report, (lab_number, student_id))
        if report:
            report.report_data = data
        else:
            report = Report(lab_number=lab_number, student_id=student_id, report_data=data)
            db.session.add(report)
        
        db.session.commit()
        app.logger.info(f"Stored report for lab {lab_number} student {student_id}")
        
        return jsonify({"status": "success", "message": f"Report for lab {lab_number} student {student_id} stored."}), 201

    elif request.method == 'GET':
        report = db.session.get(Report, (lab_number, student_id))

        if report is None:
            app.logger.info(f"No report found for lab {lab_number} student {student_id}")
            template = get_template('404.html.j2')
            return template.render({"student_id": student_id, "lab_number": lab_number}), 404

        app.logger.info(f"Serving report for lab {lab_number} student {student_id}")
        template = get_template('report.html.j2')
        return template.render(student_id=student_id, **report.report_data)

def main():
    """Starts the Flask server for development."""
    if not app.debug:
        app.logger.setLevel(logging.INFO)

    app.logger.info(f"Starting report server...")
    app.logger.info(f"Database at: {os.path.abspath(DATABASE_PATH)}")
    app.logger.info(f"Authentication Token: {AUTH_TOKEN}")
    
    # app.run() is for development only.
    # Gunicorn is used for production in the Docker container.
    app.run(host="0.0.0.0", port=1407)

if __name__ == '__main__':
    main()
