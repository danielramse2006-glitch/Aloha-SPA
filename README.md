# 🌺 Aloha SPA — Sistema de Reservas

Plataforma de reservas online para Aloha SPA, Reynosa. Permite a los clientes agendar citas con verificación por SMS.

## ✨ Características

- Diseño premium responsive
- Verificación de identidad por código SMS (Twilio)
- Panel de administración para gestionar citas
- Deploy listo para Render

## 🛠️ Tecnologías

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python / Flask
- **Base de datos**: SQLite (dev) / PostgreSQL (prod)
- **SMS**: Twilio
- **Deploy**: Render + Gunicorn

## 🚀 Instalación Local

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU-USUARIO/aloha-spa.git
cd aloha-spa

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Edita .env con tus credenciales de Twilio

# 5. Correr el servidor
python app.py
```

## 🔐 Variables de Entorno

Crea un archivo `.env` basado en `.env.example`:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
DATABASE_URL=sqlite:///aloha_spa.db
ADMIN_API_KEY=tu_clave_secreta
```

## 📱 Flujo de Reserva

1. Cliente abre el modal de reserva
2. Ingresa sus datos y teléfono
3. Recibe un SMS con código de verificación
4. Confirma el código y la cita queda guardada

## 👨‍💼 Panel Admin

Acceder en `/admin.html` con la clave configurada en `ADMIN_API_KEY`.
