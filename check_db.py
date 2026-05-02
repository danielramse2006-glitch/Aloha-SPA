from app import db, Appointment, app
with app.app_context():
    print(Appointment.__table__.columns.keys())
