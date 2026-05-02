import os
import random
import resend
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Resend Configuration
resend.api_key = os.getenv('RESEND_API_KEY')

# Database Configuration
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

db_url = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(instance_path, "aloha_spa.db")}')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='pendiente')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email requerido'}), 400

    otp_code = str(random.randint(100000, 999999))
    
    # Save to DB
    new_otp = OTP(email=email, code=otp_code)
    db.session.add(new_otp)
    db.session.commit()

    try:
        # Send via Resend
        params = {
            "from": "Aloha SPA <onboarding@resend.dev>",
            "to": [email],
            "subject": "Código de Verificación - Aloha SPA",
            "html": f"""
            <div style="font-family: sans-serif; max-width: 500px; margin: 0 auto; padding: 30px; border: 1px solid #f0f0f0; border-radius: 15px; text-align: center; color: #333;">
                <h2 style="color: #e8004f; margin-bottom: 20px;">Aloha SPA</h2>
                <p style="font-size: 16px;">Estimada clienta, su código de verificación es:</p>
                <div style="background: #fafafa; padding: 20px; font-size: 36px; font-weight: bold; color: #e8004f; letter-spacing: 8px; border-radius: 10px; margin: 25px 0;">
                    {otp_code}
                </div>
                <p style="font-size: 13px; color: #888;">Este código expira en 10 minutos. Si no solicitó este código, ignore este correo.</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #aaa;">Aloha SPA &copy; 2026</p>
            </div>
            """
        }
        resend.Emails.send(params)
        return jsonify({'message': 'Código enviado exitosamente'}), 200
    except Exception as e:
        print(f"Error Resend: {e}")
        return jsonify({
            'message': 'Error al enviar correo',
            'debug_code': otp_code,
            'details': str(e)
        }), 200

@app.route('/api/verify-and-book', methods=['POST'])
def verify_and_book():
    data = request.json
    email = data.get('email')
    code = data.get('code')
    appointment_data = data.get('appointment')

    otp_record = OTP.query.filter_by(email=email, code=code).order_by(OTP.created_at.desc()).first()
    
    if not otp_record:
        return jsonify({'error': 'Código inválido'}), 400

    # Create appointment
    try:
        new_app = Appointment(
            name=appointment_data['name'],
            email=email,
            service=appointment_data['service'],
            date=appointment_data['date'],
            time=appointment_data['time']
        )
        db.session.add(new_app)
        db.session.delete(otp_record)
        db.session.commit()
        return jsonify({'message': 'Cita agendada exitosamente', 'id': new_app.id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/appointments', methods=['GET'])
def get_appointments():
    api_key = request.headers.get('X-API-KEY')
    if api_key != os.getenv('ADMIN_API_KEY', 'aloha-secret-123'):
        return jsonify({'error': 'No autorizado'}), 401
    apps = Appointment.query.order_by(Appointment.created_at.desc()).all()
    return jsonify([{
        'id': a.id, 'name': a.name, 'email': a.email, 'service': a.service,
        'date': a.date, 'time': a.time, 'status': a.status,
        'created_at': a.created_at.isoformat()
    } for a in apps])

@app.route('/api/admin/appointments/<int:id>', methods=['PATCH'])
def update_status(id):
    api_key = request.headers.get('X-API-KEY')
    if api_key != os.getenv('ADMIN_API_KEY', 'aloha-secret-123'):
        return jsonify({'error': 'No autorizado'}), 401
    data = request.json
    app_record = Appointment.query.get_or_404(id)
    app_record.status = data.get('status', app_record.status)
    db.session.commit()
    return jsonify({'message': 'Estado actualizado'})

@app.route('/api/seed', methods=['GET'])
def seed_db():
    try:
        test_apps = [
            Appointment(name="Lucía García", email="lucia.test@gmail.com", service="Depilación Bozo", date="2026-05-20", time="10:00", status="pendiente"),
            Appointment(name="María Rodríguez", email="maria.spa@hotmail.com", service="Cuerpo Completo", date="2026-05-21", time="14:30", status="confirmada"),
            Appointment(name="Sofía López", email="sofia.l@yahoo.com", service="Masaje Relajante", date="2026-05-22", time="16:00", status="pendiente")
        ]
        for a in test_apps:
            db.session.add(a)
        db.session.commit()
        return jsonify({'message': 'Base de datos poblada'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
