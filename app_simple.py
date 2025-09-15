from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'tu_clave_secreta_aqui')
database_url = os.getenv('DATABASE_URL', 'sqlite:///wandy.db')
# Convertir DATABASE_URL de Railway/Heroku para SQLAlchemy
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelo básico de Usuario
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    cargo = db.Column(db.String(50), nullable=False)
    rol = db.Column(db.String(20), default='empleado')
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_admin(self):
        return self.rol == 'admin'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Rutas básicas
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Usuario.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Inicio de sesión exitoso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Wandy Soluciones - Login</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 400px; margin: 50px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            h1 { text-align: center; color: #333; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input[type="text"], input[type="password"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            .btn { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #0056b3; }
            .alert { padding: 10px; margin-bottom: 20px; border-radius: 5px; }
            .alert-danger { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>WANDY SOLUCIONES</h1>
            <p style="text-align: center; color: #666; margin-bottom: 30px;">Sistema de Gestión de Préstamos</p>
            
            <form method="POST">
                <div class="form-group">
                    <label for="username">Usuario:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                
                <div class="form-group">
                    <label for="password">Contraseña:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                
                <button type="submit" class="btn">Iniciar Sesión</button>
            </form>
            
            <div style="margin-top: 20px; text-align: center; color: #666; font-size: 14px;">
                <p>Usuario por defecto: <strong>admin</strong></p>
                <p>Contraseña: <strong>admin123</strong></p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/dashboard')
@login_required
def dashboard():
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard - Wandy Soluciones</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .header {{ background: #007bff; color: white; padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
            .welcome {{ font-size: 24px; margin-bottom: 10px; }}
            .subtitle {{ opacity: 0.9; }}
            .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }}
            .btn:hover {{ background: #218838; }}
            .btn-danger {{ background: #dc3545; }}
            .btn-danger:hover {{ background: #c82333; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="welcome">¡Bienvenido, {current_user.nombre}!</div>
            <div class="subtitle">Sistema de Gestión de Préstamos - Wandy Soluciones</div>
        </div>
        
        <div class="card">
            <h2>🎉 ¡Aplicación Desplegada Exitosamente!</h2>
            <p>Tu sistema de gestión de préstamos está ahora disponible en la nube y puede ser accedido desde cualquier dispositivo móvil.</p>
            
            <h3>✅ Funcionalidades Disponibles:</h3>
            <ul>
                <li>Sistema de login seguro</li>
                <li>Dashboard principal</li>
                <li>Base de datos PostgreSQL en la nube</li>
                <li>Acceso desde cualquier móvil</li>
                <li>SSL automático (HTTPS)</li>
            </ul>
            
            <h3>🔄 Próximos Pasos:</h3>
            <p>Una vez que confirmes que la aplicación funciona correctamente, podemos reactivar las funcionalidades avanzadas como:</p>
            <ul>
                <li>Gestión de clientes</li>
                <li>Gestión de préstamos</li>
                <li>Sistema de pagos</li>
                <li>Generación de reportes PDF</li>
                <li>Envío de emails</li>
            </ul>
            
            <div style="margin-top: 30px;">
                <a href="/logout" class="btn btn-danger">Cerrar Sesión</a>
            </div>
        </div>
        
        <div class="card">
            <h3>📱 Acceso Móvil</h3>
            <p>Esta aplicación está optimizada para dispositivos móviles. Puedes:</p>
            <ul>
                <li>Agregar a pantalla de inicio en tu móvil</li>
                <li>Acceder desde cualquier navegador</li>
                <li>Usar desde múltiples dispositivos simultáneamente</li>
            </ul>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada exitosamente', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Crear usuario administrador por defecto si no existe
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                nombre='Administrador',
                apellidos='Sistema',
                cargo='Administrador',
                rol='admin'
            )
            db.session.add(admin)
            db.session.commit()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
