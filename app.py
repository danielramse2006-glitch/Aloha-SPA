import os
import random
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database Configuration
# Ensure the instance folder exists for SQLite
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

db_url = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(instance_path, "aloha_spa.db")}')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Email Configuration
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

# Models
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Pendiente')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# Serve frontend files
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory('.', 'admin.html')

# API Endpoints
@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email requerido'}), 400

    otp_code = str(random.randint(100000, 999999))
    
    # Save OTP to DB
    new_otp = OTP(email=email, code=otp_code)
    db.session.add(new_otp)
    db.session.commit()

    # Send via SMTP
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_USERNAME
        msg['To'] = email
        msg['Subject'] = "Confirmación de Identidad - Aloha SPA"
        
        body_html = f"""
        <html>
        <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #3d2424; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #f0f0f0; border-radius: 10px;">
                <h2 style="color: #e8004f; text-align: center;">Aloha SPA</h2>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p>Estimada clienta,</p>
                <p>Para continuar con el proceso de agendación de su cita en <strong>Aloha Spa</strong>, por favor utilice el siguiente código de verificación:</p>
                <div style="background-color: #fafafa; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #e8004f;">{otp_code}</span>
                </div>
                <p style="font-size: 14px; color: #666;">Este código es necesario para confirmar su identidad y asegurar su espacio en nuestra agenda. Si usted no solicitó este código, por favor ignore este mensaje.</p>
                <p>Atentamente,<br><strong>El Equipo de Aloha SPA</strong></p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #999; text-align: center;">Este es un mensaje automático, por favor no responda a este correo.</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body_html, 'html'))
        
        # Configurar servidor
        MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.googlemail.com')
        
        try:
            if MAIL_PORT == 465:
                server = smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT, timeout=20)
            else:
                server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=20)
                server.starttls()
            
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            # Reintento con puerto alternativo si falla
            print(f"Error SMTP: {e}")
            raise e
        
        return jsonify({'message': 'Código enviado exitosamente'}), 200
    except Exception as e:
        print(f"Error Email: {e}")
        return jsonify({
            'message': 'Modo Desarrollo: El correo no se envió pero puedes usar el código de debug.',
            'debug_code': otp_code,
            'details': str(e)
        }), 200

@app.route('/api/verify-and-book', methods=['POST'])
def verify_and_book():
    data = request.json
    email = data.get('email')
    code = data.get('code')
    
    appointment_data = data.get('appointment') # {name, service, date, time}

    # Verify OTP
    otp_record = OTP.query.filter_by(email=email, code=code).order_by(OTP.created_at.desc()).first()
    
    if not otp_record:
        return jsonify({'error': 'Código inválido'}), 400
    
    # Save Appointment
    try:
        new_app = Appointment(
            name=appointment_data['name'],
            email=email,
            service=appointment_data['service'],
            date=appointment_data['date'],
            time=appointment_data['time']
        )
        db.session.add(new_app)
        db.session.delete(otp_record) # Remove used OTP
        db.session.commit()
        return jsonify({'message': 'Cita agendada exitosamente', 'id': new_app.id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/appointments', methods=['GET'])
def get_appointments():
    # Simple security (can be improved with JWT)
    api_key = request.headers.get('X-API-KEY')
    if api_key != os.getenv('ADMIN_API_KEY', 'aloha-secret-123'):
        return jsonify({'error': 'No autorizado'}), 401

    apps = Appointment.query.order_by(Appointment.created_at.desc()).all()
    return jsonify([{
        'id': a.id,
        'name': a.name,
        'email': a.email,
        'service': a.service,
        'date': a.date,
        'time': a.time,
        'status': a.status,
        'created_at': a.created_at.isoformat()
    } for a in apps])

@app.route('/api/admin/appointments/<int:id>', methods=['PATCH'])
def update_status(id):
    api_key = request.headers.get('X-API-KEY')
    if api_key != os.getenv('ADMIN_API_KEY', 'aloha-secret-123'):
        return jsonify({'error': 'No autorizado'}), 401

    data = request.json
    app = Appointment.query.get_or_404(id)
    app.status = data.get('status', app.status)
    db.session.commit()
    return jsonify({'message': 'Estado actualizado'})

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
