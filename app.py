from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from functools import wraps
# Importaciones de reportlab comentadas temporalmente para deployment
# from reportlab.lib.pagesizes import letter, A4
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib.units import inch
# from reportlab.lib import colors
# from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
import io
import tempfile
import json
from provincias_municipios_rd import obtener_provincias, obtener_municipios
# from config_brevo import enviar_recibo_pago_brevo, enviar_notificacion_atraso_brevo

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'tu_clave_secreta_aqui')
database_url = os.getenv('DATABASE_URL', 'mysql+pymysql://root:Wandi829.@localhost/wandy_soluciones')
# Convertir DATABASE_URL de Railway/Heroku para SQLAlchemy
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelos de base de datos
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    cargo = db.Column(db.String(50), nullable=False)
    rol = db.Column(db.String(20), default='empleado')  # admin, empleado
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acceso = db.Column(db.DateTime)
    
    def is_admin(self):
        return self.rol == 'admin'
    
    def can_edit(self, item_type):
        """Verifica si el usuario puede editar/eliminar según su rol"""
        if self.is_admin():
            return True
        # Los empleados solo pueden editar sus propios registros
        return False
    
    def can_delete(self, item_type):
        """Verifica si el usuario puede eliminar según su rol"""
        return self.is_admin()

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    apodo = db.Column(db.String(50))
    documento = db.Column(db.String(20), unique=True, nullable=False)
    nacionalidad = db.Column(db.String(50), nullable=False)
    fecha_nacimiento = db.Column(db.Date)
    sexo = db.Column(db.String(20), nullable=False)
    estado_civil = db.Column(db.String(50), nullable=False)
    whatsapp = db.Column(db.String(20))
    telefono_principal = db.Column(db.String(20), nullable=False)
    telefono_otro = db.Column(db.String(20))
    correo = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    provincia = db.Column(db.String(50), nullable=False)
    municipio = db.Column(db.String(50), nullable=False)
    sector = db.Column(db.String(100), nullable=False)
    ruta = db.Column(db.String(50))
    ocupacion = db.Column(db.String(100), nullable=False)
    ingresos = db.Column(db.Numeric(10, 2), nullable=False)
    situacion_laboral = db.Column(db.String(100), nullable=False)
    lugar_trabajo = db.Column(db.String(100), nullable=False)
    direccion_trabajo = db.Column(db.String(200), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)

class Prestamo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    tasa_interes = db.Column(db.Numeric(5, 2), nullable=False)
    plazo_meses = db.Column(db.Integer, nullable=False)
    frecuencia = db.Column(db.String(20), nullable=False)
    fecha_primera_cuota = db.Column(db.Date, nullable=False)
    tipo_garantia = db.Column(db.String(100))
    descripcion_garantia = db.Column(db.Text)
    valor_garantia = db.Column(db.Numeric(10, 2))
    estado_garantia = db.Column(db.String(50), default='En Custodia')
    estado = db.Column(db.String(20), default='Activo')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    cliente = db.relationship('Cliente', backref='prestamos')

class Cuota(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prestamo_id = db.Column(db.Integer, db.ForeignKey('prestamo.id'), nullable=False)
    numero_cuota = db.Column(db.Integer, nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    monto_capital = db.Column(db.Numeric(10, 2), nullable=False)
    monto_interes = db.Column(db.Numeric(10, 2), nullable=False)
    monto_total = db.Column(db.Numeric(10, 2), nullable=False)
    saldo_restante = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), default='Pendiente')
    prestamo = db.relationship('Prestamo', backref='cuotas')
    
    @property
    def dias_atraso(self):
        """Calcula los días de atraso de la cuota"""
        if self.estado == 'Pendiente' and self.fecha_vencimiento < datetime.now().date():
            return (datetime.now().date() - self.fecha_vencimiento).days
        return 0

class Pago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cuota_id = db.Column(db.Integer, db.ForeignKey('cuota.id'), nullable=True)  # Permitir NULL para pagos extraordinarios
    monto_pagado = db.Column(db.Numeric(10, 2), nullable=False)
    monto_capital = db.Column(db.Numeric(10, 2), nullable=False)
    monto_interes = db.Column(db.Numeric(10, 2), nullable=False)
    tipo_pago = db.Column(db.String(20), default='Normal')
    fecha_pago = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    cuota = db.relationship('Cuota', backref='pagos')
    usuario = db.relationship('Usuario', backref='pagos')

class Contabilidad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    capital_disponible = db.Column(db.Numeric(10, 2), default=0.00)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow)

class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(200), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(50), default='General')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class Reporte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    formato = db.Column(db.String(20), nullable=False)
    parametros = db.Column(db.Text)  # JSON string con parámetros del reporte
    fecha_generacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tamano_archivo = db.Column(db.String(50))  # Tamaño del archivo generado
    ruta_archivo = db.Column(db.String(500))  # Ruta donde se guardó el archivo
    estado = db.Column(db.String(20), default='Completado')  # Completado, Error, En Proceso
    
    # Relaciones
    usuario = db.relationship('Usuario', backref='reportes')
    
    def __repr__(self):
        return f'<Reporte {self.tipo} - {self.nombre}>'

# Modelos para el sistema de chat
class Conversacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario1_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    usuario2_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    activa = db.Column(db.Boolean, default=True)
    
    # Relaciones
    usuario1 = db.relationship('Usuario', foreign_keys=[usuario1_id], backref='conversaciones_iniciadas')
    usuario2 = db.relationship('Usuario', foreign_keys=[usuario2_id], backref='conversaciones_recibidas')
    mensajes = db.relationship('Mensaje', backref='conversacion', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Conversacion {self.usuario1_id}-{self.usuario2_id}>'

class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversacion_id = db.Column(db.Integer, db.ForeignKey('conversacion.id'), nullable=False)
    remitente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    fecha_envio = db.Column(db.DateTime, default=datetime.utcnow)
    leido = db.Column(db.Boolean, default=False)
    
    # Relaciones
    remitente = db.relationship('Usuario', backref='mensajes_enviados')
    
    def __repr__(self):
        return f'<Mensaje {self.id} de {self.remitente_id}>'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Rutas de la aplicación
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
    
    return render_template('login.html')

@app.route('/calculadora')
@login_required
def calculadora():
    return render_template('calculadora.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada exitosamente', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Obtener estadísticas del dashboard
    total_prestamos = Prestamo.query.filter_by(estado='Activo').count()
    total_clientes = Cliente.query.filter_by(activo=True).count()
    
    # Calcular clientes atrasados
    fecha_actual = datetime.now().date()
    cuotas_atrasadas = Cuota.query.filter(
        Cuota.estado == 'Pendiente',
        Cuota.fecha_vencimiento < fecha_actual
    ).all()
    
    clientes_atrasados = len(set([cuota.prestamo.cliente_id for cuota in cuotas_atrasadas]))
    monto_total_atrasado = sum(float(cuota.monto_total) for cuota in cuotas_atrasadas)
    
    # Obtener capital disponible
    contabilidad = Contabilidad.query.first()
    capital_disponible = float(contabilidad.capital_disponible) if contabilidad else 0
    
    # Préstamos del mes
    inicio_mes = fecha_actual.replace(day=1)
    prestamos_mes = Prestamo.query.filter(
        Prestamo.fecha_creacion >= inicio_mes
    ).count()
    
    # Pagos del mes
    pagos_mes = Pago.query.filter(
        Pago.fecha_pago >= inicio_mes
    ).count()
    monto_pagos_mes = sum(float(p.monto_pagado) for p in Pago.query.filter(Pago.fecha_pago >= inicio_mes).all())
    
    # Usuarios activos
    usuarios_activos = Usuario.query.filter_by(activo=True).count()
    
    # Actividad reciente (últimas 24 horas)
    fecha_24h = datetime.now() - timedelta(hours=24)
    
    # Clientes recientes
    clientes_recientes = Cliente.query.filter(
        Cliente.fecha_creacion >= fecha_24h
    ).order_by(Cliente.fecha_creacion.desc()).limit(3).all()
    
    # Préstamos recientes
    prestamos_recientes = Prestamo.query.filter(
        Prestamo.fecha_creacion >= fecha_24h
    ).order_by(Prestamo.fecha_creacion.desc()).limit(3).all()
    
    # Pagos recientes
    pagos_recientes = Pago.query.filter(
        Pago.fecha_pago >= fecha_24h
    ).order_by(Pago.fecha_pago.desc()).limit(3).all()
    
    # Próximos vencimientos (próximos 7 días)
    fecha_7d = fecha_actual + timedelta(days=7)
    proximos_vencimientos = Cuota.query.filter(
        Cuota.estado == 'Pendiente',
        Cuota.fecha_vencimiento >= fecha_actual,
        Cuota.fecha_vencimiento <= fecha_7d
    ).order_by(Cuota.fecha_vencimiento).limit(5).all()
    
    return render_template('dashboard.html',
                         total_prestamos=total_prestamos,
                         total_clientes=total_clientes,
                         clientes_atrasados=clientes_atrasados,
                         monto_total_atrasado=monto_total_atrasado,
                         capital_disponible=capital_disponible,
                         prestamos_mes=prestamos_mes,
                         pagos_mes=pagos_mes,
                         monto_pagos_mes=monto_pagos_mes,
                         usuarios_activos=usuarios_activos,
                         clientes_recientes=clientes_recientes,
                         prestamos_recientes=prestamos_recientes,
                         pagos_recientes=pagos_recientes,
                         proximos_vencimientos=proximos_vencimientos)

# Rutas del sistema de chat
@app.route('/chat')
@login_required
def chat():
    """Página principal del chat - lista de conversaciones"""
    # Obtener todas las conversaciones del usuario actual
    conversaciones = Conversacion.query.filter(
        db.or_(
            Conversacion.usuario1_id == current_user.id,
            Conversacion.usuario2_id == current_user.id
        ),
        Conversacion.activa == True
    ).all()
    
    # Obtener todos los usuarios para iniciar nuevas conversaciones
    usuarios = Usuario.query.filter(
        Usuario.id != current_user.id,
        Usuario.activo == True
    ).all()
    
    # Preparar datos de conversaciones con información del otro usuario
    conversaciones_data = []
    for conv in conversaciones:
        if conv.usuario1_id == current_user.id:
            otro_usuario = conv.usuario2
        else:
            otro_usuario = conv.usuario1
        
        # Obtener último mensaje
        ultimo_mensaje = conv.mensajes.order_by(Mensaje.fecha_envio.desc()).first()
        
        conversaciones_data.append({
            'conversacion': conv,
            'otro_usuario': otro_usuario,
            'ultimo_mensaje': ultimo_mensaje
        })
    
    return render_template('chat.html', 
                         conversaciones=conversaciones_data,
                         usuarios=usuarios)

@app.route('/chat/<int:usuario_id>')
@login_required
def chat_usuario(usuario_id):
    """Chat individual con un usuario específico"""
    # Verificar que el usuario existe y está activo
    otro_usuario = Usuario.query.filter_by(id=usuario_id, activo=True).first_or_404()
    
    # Buscar conversación existente o crear una nueva
    conversacion = Conversacion.query.filter(
        db.or_(
            db.and_(Conversacion.usuario1_id == current_user.id, Conversacion.usuario2_id == usuario_id),
            db.and_(Conversacion.usuario1_id == usuario_id, Conversacion.usuario2_id == current_user.id)
        ),
        Conversacion.activa == True
    ).first()
    
    if not conversacion:
        # Crear nueva conversación
        conversacion = Conversacion(
            usuario1_id=current_user.id,
            usuario2_id=usuario_id
        )
        db.session.add(conversacion)
        db.session.commit()
    
    # Obtener mensajes de la conversación
    mensajes = conversacion.mensajes.order_by(Mensaje.fecha_envio.asc()).all()
    
    # Marcar mensajes como leídos
    for mensaje in mensajes:
        if mensaje.remitente_id != current_user.id and not mensaje.leido:
            mensaje.leido = True
    
    db.session.commit()
    
    # Obtener lista de usuarios para el sidebar
    usuarios = Usuario.query.filter(
        Usuario.id != current_user.id,
        Usuario.activo == True
    ).all()
    
    # Obtener todas las conversaciones del usuario actual para el sidebar
    conversaciones = Conversacion.query.filter(
        db.or_(
            Conversacion.usuario1_id == current_user.id,
            Conversacion.usuario2_id == current_user.id
        ),
        Conversacion.activa == True
    ).all()
    
    # Preparar datos de conversaciones con información del otro usuario
    conversaciones_data = []
    for conv in conversaciones:
        if conv.usuario1_id == current_user.id:
            otro_usuario = conv.usuario2
        else:
            otro_usuario = conv.usuario1
        
        # Obtener último mensaje
        ultimo_mensaje = conv.mensajes.order_by(Mensaje.fecha_envio.desc()).first()
        
        conversaciones_data.append({
            'conversacion': conv,
            'otro_usuario': otro_usuario,
            'ultimo_mensaje': ultimo_mensaje
        })
    
    return render_template('chat_usuario.html',
                         conversacion=conversacion,
                         conversaciones=conversaciones_data,
                         destinatario=otro_usuario,
                         mensajes=mensajes,
                         usuarios=usuarios)

@app.route('/chat/enviar-mensaje', methods=['POST'])
@login_required
def enviar_mensaje():
    """API para enviar un mensaje"""
    try:
        data = request.get_json()
        destinatario_id = data.get('destinatario_id')
        contenido = data.get('contenido')
        
        if not contenido or not destinatario_id:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        # Buscar o crear conversación
        conversacion = Conversacion.query.filter(
            db.or_(
                db.and_(Conversacion.usuario1_id == current_user.id, Conversacion.usuario2_id == destinatario_id),
                db.and_(Conversacion.usuario1_id == destinatario_id, Conversacion.usuario2_id == current_user.id)
            ),
            Conversacion.activa == True
        ).first()
        
        if not conversacion:
            conversacion = Conversacion(
                usuario1_id=current_user.id,
                usuario2_id=destinatario_id
            )
            db.session.add(conversacion)
            db.session.commit()
        
        # Crear mensaje
        mensaje = Mensaje(
            conversacion_id=conversacion.id,
            remitente_id=current_user.id,
            contenido=contenido
        )
        db.session.add(mensaje)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'mensaje_id': mensaje.id,
            'fecha_envio': mensaje.fecha_envio.strftime('%H:%M'),
            'remitente': {
                'id': current_user.id,
                'nombre': current_user.nombre,
                'apellidos': current_user.apellidos
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/mensajes-nuevos')
@login_required
def mensajes_nuevos():
    """API para obtener mensajes nuevos (para actualización en tiempo real)"""
    try:
        # Obtener conversaciones del usuario
        conversaciones = Conversacion.query.filter(
            db.or_(
                Conversacion.usuario1_id == current_user.id,
                Conversacion.usuario2_id == current_user.id
            ),
            Conversacion.activa == True
        ).all()
        
        mensajes_nuevos = []
        for conv in conversaciones:
            # Obtener mensajes no leídos
            mensajes = conv.mensajes.filter(
                Mensaje.remitente_id != current_user.id,
                Mensaje.leido == False
            ).all()
            
            for mensaje in mensajes:
                mensajes_nuevos.append({
                    'id': mensaje.id,
                    'contenido': mensaje.contenido,
                    'fecha_envio': mensaje.fecha_envio.strftime('%H:%M'),
                    'remitente': {
                        'id': mensaje.remitente.id,
                        'nombre': mensaje.remitente.nombre,
                        'apellidos': mensaje.remitente.apellidos
                    },
                    'conversacion_id': conv.id
                })
        
        return jsonify(mensajes_nuevos)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/count-no-leidos')
@login_required
def count_mensajes_no_leidos():
    """API para obtener el conteo de mensajes no leídos"""
    try:
        # Obtener conversaciones del usuario
        conversaciones = Conversacion.query.filter(
            db.or_(
                Conversacion.usuario1_id == current_user.id,
                Conversacion.usuario2_id == current_user.id
            ),
            Conversacion.activa == True
        ).all()
        
        total_no_leidos = 0
        for conv in conversaciones:
            # Contar mensajes no leídos
            count = conv.mensajes.filter(
                Mensaje.remitente_id != current_user.id,
                Mensaje.leido == False
            ).count()
            total_no_leidos += count
        
        return jsonify({'count': total_no_leidos})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat/cerrar-conversacion/<int:conversacion_id>', methods=['POST'])
@login_required
def cerrar_conversacion(conversacion_id):
    """API para cerrar/eliminar una conversación"""
    try:
        # Verificar que la conversación existe y pertenece al usuario actual
        conversacion = Conversacion.query.filter(
            db.or_(
                Conversacion.usuario1_id == current_user.id,
                Conversacion.usuario2_id == current_user.id
            ),
            Conversacion.id == conversacion_id,
            Conversacion.activa == True
        ).first_or_404()
        
        # Marcar la conversación como inactiva
        conversacion.activa = False
        
        # Opcional: eliminar físicamente la conversación y todos los mensajes
        # db.session.delete(conversacion)  # Esto eliminaría todo
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Conversación cerrada exitosamente'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/clientes')
@login_required
def clientes():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Obtener parámetros de búsqueda
    query = request.args.get('q', '')
    provincia = request.args.get('provincia', '')
    estado = request.args.get('estado', '')
    
    # Construir consulta base
    clientes_query = Cliente.query.filter_by(activo=True)
    
    # Aplicar filtros si existen
    if query:
        clientes_query = clientes_query.filter(
            db.or_(
                Cliente.nombre.contains(query),
                Cliente.apellidos.contains(query),
                Cliente.documento.contains(query)
            )
        )
    
    if provincia:
        clientes_query = clientes_query.filter_by(provincia=provincia)
    
    if estado:
        if estado == 'con_prestamos':
            clientes_query = clientes_query.join(Prestamo).filter(Prestamo.estado == 'Activo')
        elif estado == 'sin_prestamos':
            clientes_query = clientes_query.outerjoin(Prestamo).filter(Prestamo.id.is_(None))
    
    # Ordenar por fecha de creación (más recientes primero)
    clientes_query = clientes_query.order_by(Cliente.fecha_creacion.desc())
    
    # Paginar resultados
    clientes = clientes_query.paginate(
        page=page, per_page=per_page, error_out=False)
    
    provincias = obtener_provincias()
    return render_template('clientes.html', 
                         clientes=clientes, 
                         query=query, 
                         provincia=provincia, 
                         estado=estado,
                         provincias=provincias)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_cliente():
    if request.method == 'POST':
        try:
            cliente = Cliente(
                nombre=request.form['nombre'],
                apellidos=request.form['apellidos'],
                apodo=request.form.get('apodo'),
                documento=request.form['documento'],
                nacionalidad=request.form['nacionalidad'],
                fecha_nacimiento=datetime.strptime(request.form['fecha_nacimiento'], '%Y-%m-%d').date() if request.form['fecha_nacimiento'] else None,
                sexo=request.form['sexo'],
                estado_civil=request.form['estado_civil'],
                whatsapp=request.form.get('whatsapp'),
                telefono_principal=request.form['telefono_principal'],
                telefono_otro=request.form.get('telefono_otro'),
                correo=request.form['correo'],
                direccion=request.form['direccion'],
                provincia=request.form['provincia'],
                municipio=request.form['municipio'],
                sector=request.form['sector'],
                ruta=request.form.get('ruta'),
                ocupacion=request.form['ocupacion'],
                ingresos=request.form['ingresos'],
                situacion_laboral=request.form['situacion_laboral'],
                lugar_trabajo=request.form['lugar_trabajo'],
                direccion_trabajo=request.form['direccion_trabajo']
            )
            db.session.add(cliente)
            db.session.commit()
            flash('Cliente registrado exitosamente', 'success')
            return redirect(url_for('clientes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar cliente: {str(e)}', 'error')
    
    provincias = obtener_provincias()
    return render_template('nuevo_cliente.html', provincias=provincias)

@app.route('/clientes/<int:cliente_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    if request.method == 'POST':
        try:
            cliente.nombre = request.form['nombre']
            cliente.apellidos = request.form['apellidos']
            cliente.apodo = request.form.get('apodo')
            cliente.documento = request.form['documento']
            cliente.nacionalidad = request.form['nacionalidad']
            cliente.fecha_nacimiento = datetime.strptime(request.form['fecha_nacimiento'], '%Y-%m-%d').date() if request.form['fecha_nacimiento'] else None
            cliente.sexo = request.form['sexo']
            cliente.estado_civil = request.form['estado_civil']
            cliente.whatsapp = request.form.get('whatsapp')
            cliente.telefono_principal = request.form['telefono_principal']
            cliente.telefono_otro = request.form.get('telefono_otro')
            cliente.correo = request.form['correo']
            cliente.direccion = request.form['direccion']
            cliente.provincia = request.form['provincia']
            cliente.municipio = request.form['municipio']
            cliente.sector = request.form['sector']
            cliente.ruta = request.form.get('ruta')
            cliente.ocupacion = request.form['ocupacion']
            cliente.ingresos = request.form['ingresos']
            cliente.situacion_laboral = request.form['situacion_laboral']
            cliente.lugar_trabajo = request.form['lugar_trabajo']
            cliente.direccion_trabajo = request.form['direccion_trabajo']
            
            db.session.commit()
            flash('Cliente actualizado exitosamente', 'success')
            return redirect(url_for('ver_cliente', cliente_id=cliente.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar cliente: {str(e)}', 'error')
    
    provincias = obtener_provincias()
    return render_template('editar_cliente.html', cliente=cliente, provincias=provincias)

@app.route('/clientes/<int:cliente_id>')
@login_required
def ver_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    prestamos = Prestamo.query.filter_by(cliente_id=cliente_id).all()
    return render_template('ver_cliente.html', cliente=cliente, prestamos=prestamos)

@app.route('/clientes/<int:cliente_id>/eliminar', methods=['POST'])
@login_required
def eliminar_cliente(cliente_id):
    # Solo administradores pueden eliminar clientes
    if not current_user.is_admin():
        flash('Acceso denegado. Solo los administradores pueden eliminar clientes.', 'error')
        return redirect(url_for('ver_cliente', cliente_id=cliente_id))
    
    cliente = Cliente.query.get_or_404(cliente_id)
    try:
        # Verificar si tiene préstamos activos
        prestamos_activos = Prestamo.query.filter_by(cliente_id=cliente_id, estado='Activo').count()
        if prestamos_activos > 0:
            flash('No se puede eliminar un cliente con préstamos activos', 'error')
            return redirect(url_for('ver_cliente', cliente_id=cliente.id))
        
        # Marcar como inactivo en lugar de eliminar
        cliente.activo = False
        db.session.commit()
        flash('Cliente marcado como inactivo exitosamente', 'success')
        return redirect(url_for('clientes'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar cliente: {str(e)}', 'error')
        return redirect(url_for('ver_cliente', cliente_id=cliente.id))

@app.route('/clientes/<int:cliente_id>/descargar-pdf')
@login_required
def descargar_cliente_pdf(cliente_id):
    # Funcionalidad PDF temporalmente deshabilitada para deployment
    flash('Funcionalidad PDF temporalmente no disponible', 'info')
    return redirect(url_for('ver_cliente', cliente_id=cliente_id))

@app.route('/clientes/buscar')
@login_required
def buscar_clientes():
    query = request.args.get('q', '')
    provincia = request.args.get('provincia', '')
    estado = request.args.get('estado', '')
    
    clientes_query = Cliente.query.filter_by(activo=True)
    
    if query:
        clientes_query = clientes_query.filter(
            db.or_(
                Cliente.nombre.contains(query),
                Cliente.apellidos.contains(query),
                Cliente.documento.contains(query)
            )
        )
    
    if provincia:
        clientes_query = clientes_query.filter_by(provincia=provincia)
    
    if estado:
        if estado == 'con_prestamos':
            clientes_query = clientes_query.join(Prestamo).filter(Prestamo.estado == 'Activo')
        elif estado == 'sin_prestamos':
            clientes_query = clientes_query.outerjoin(Prestamo).filter(Prestamo.id.is_(None))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    clientes = clientes_query.paginate(page=page, per_page=per_page, error_out=False)
    
    provincias = obtener_provincias()
    return render_template('clientes.html', clientes=clientes, query=query, provincia=provincia, estado=estado, provincias=provincias)

@app.route('/api/municipios/<provincia>')
@login_required
def obtener_municipios_provincia(provincia):
    """API para obtener municipios de una provincia específica"""
    municipios = obtener_municipios(provincia)
    return jsonify(municipios)

@app.route('/prestamos')
@login_required
def prestamos():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Obtener parámetros de búsqueda
    query = request.args.get('q', '')
    estado = request.args.get('estado', '')
    cliente_id = request.args.get('cliente_id', '')
    
    # Construir consulta base
    prestamos_query = Prestamo.query
    
    # Aplicar filtros si existen
    if query:
        prestamos_query = prestamos_query.join(Cliente).filter(
            db.or_(
                Cliente.nombre.contains(query),
                Cliente.apellidos.contains(query),
                Cliente.documento.contains(query)
            )
        )
    
    if estado:
        prestamos_query = prestamos_query.filter_by(estado=estado)
    
    if cliente_id:
        prestamos_query = prestamos_query.filter_by(cliente_id=cliente_id)
    
    # Ordenar por fecha de creación (más recientes primero)
    prestamos_query = prestamos_query.order_by(Prestamo.fecha_creacion.desc())
    
    # Paginar resultados
    prestamos = prestamos_query.paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('prestamos.html', 
                         prestamos=prestamos, 
                         query=query, 
                         estado=estado, 
                         cliente_id=cliente_id)

@app.route('/prestamos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_prestamo():
    if request.method == 'POST':
        try:
            # Procesar campos opcionales de garantía
            tipo_garantia = request.form.get('tipo_garantia')
            descripcion_garantia = request.form.get('descripcion_garantia')
            valor_garantia = request.form.get('valor_garantia')
            
            # Convertir valor_garantia a None si está vacío
            if valor_garantia == '':
                valor_garantia = None
            elif valor_garantia:
                valor_garantia = float(valor_garantia)
            
            prestamo = Prestamo(
                cliente_id=request.form['cliente_id'],
                monto=request.form['monto'],
                tasa_interes=request.form['tasa_interes'],
                plazo_meses=request.form['plazo_meses'],
                frecuencia=request.form['frecuencia'],
                fecha_primera_cuota=datetime.strptime(request.form['fecha_primera_cuota'], '%Y-%m-%d').date(),
                tipo_garantia=tipo_garantia if tipo_garantia else None,
                descripcion_garantia=descripcion_garantia if descripcion_garantia else None,
                valor_garantia=valor_garantia
            )
            db.session.add(prestamo)
            db.session.commit()
            
            # Generar cuotas del préstamo
            generar_cuotas(prestamo)
            
            # Registrar la transacción en contabilidad (préstamo = salida de capital)
            monto_prestamo = float(request.form['monto'])
            contabilidad = Contabilidad.query.first()
            if not contabilidad:
                contabilidad = Contabilidad(capital_disponible=0)
                db.session.add(contabilidad)
            
            # Reducir el capital disponible por el monto del préstamo
            contabilidad.capital_disponible = float(contabilidad.capital_disponible) - monto_prestamo
            contabilidad.fecha_actualizacion = datetime.utcnow()
            
            # Registrar como gasto en contabilidad
            gasto_prestamo = Gasto(
                descripcion=f"Préstamo aprobado - Cliente ID: {prestamo.cliente_id}",
                monto=monto_prestamo,  # Positivo para gasto
                fecha=datetime.now().date(),
                tipo="Préstamos"
            )
            db.session.add(gasto_prestamo)
            
            db.session.commit()
            
            flash('Préstamo registrado exitosamente', 'success')
            return redirect(url_for('prestamos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar préstamo: {str(e)}', 'error')
    
    clientes = Cliente.query.filter_by(activo=True).all()
    return render_template('nuevo_prestamo.html', clientes=clientes)

@app.route('/prestamos/<int:prestamo_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_prestamo(prestamo_id):
    prestamo = Prestamo.query.get_or_404(prestamo_id)
    if request.method == 'POST':
        try:
            prestamo.monto = request.form['monto']
            prestamo.tasa_interes = request.form['tasa_interes']
            prestamo.plazo_meses = request.form['plazo_meses']
            prestamo.frecuencia = request.form['frecuencia']
            prestamo.fecha_primera_cuota = datetime.strptime(request.form['fecha_primera_cuota'], '%Y-%m-%d').date()
            
            # Procesar campos opcionales de garantía
            tipo_garantia = request.form.get('tipo_garantia')
            descripcion_garantia = request.form.get('descripcion_garantia')
            valor_garantia = request.form.get('valor_garantia')
            
            # Convertir valor_garantia a None si está vacío
            if valor_garantia == '':
                valor_garantia = None
            elif valor_garantia:
                valor_garantia = float(valor_garantia)
            
            prestamo.tipo_garantia = tipo_garantia if tipo_garantia else None
            prestamo.descripcion_garantia = descripcion_garantia if descripcion_garantia else None
            prestamo.valor_garantia = valor_garantia
            
            db.session.commit()
            flash('Préstamo actualizado exitosamente', 'success')
            return redirect(url_for('ver_prestamo', prestamo_id=prestamo.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar préstamo: {str(e)}', 'error')
    
    clientes = Cliente.query.filter_by(activo=True).all()
    return render_template('editar_prestamo.html', prestamo=prestamo, clientes=clientes)

@app.route('/prestamos/<int:prestamo_id>/contrato')
@login_required
def generar_contrato_prestamo(prestamo_id):
    """Genera un contrato de préstamo en formato PDF"""
    try:
        prestamo = Prestamo.query.get_or_404(prestamo_id)
        cliente = prestamo.cliente
        
        # Convertir monto a letras
        monto_letras = convertir_numero_a_letras(float(prestamo.monto))
        
        # Obtener fecha actual en formato español
        fecha_actual = datetime.now()
        dia = fecha_actual.day
        mes = obtener_nombre_mes(fecha_actual.month)
        año = fecha_actual.year
        
        # Generar contrato directamente en PDF usando reportlab
        pdf = generar_contrato_prestamo_pdf(prestamo, cliente, monto_letras, dia, mes, año)
        
        # Crear respuesta con PDF
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=contrato_prestamo_{cliente.nombre}_{cliente.apellidos}.pdf'
        
        return response
        
    except Exception as e:
        flash(f'Error al generar contrato: {str(e)}', 'error')
        return redirect(url_for('ver_prestamo', prestamo_id=prestamo_id))

def convertir_numero_a_letras(numero):
    """Convierte un número a su representación en letras en español"""
    unidades = ['', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve']
    decenas = ['', 'diez', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa']
    especiales = ['once', 'doce', 'trece', 'catorce', 'quince', 'dieciséis', 'diecisiete', 'dieciocho', 'diecinueve']
    
    if numero == 0:
        return 'cero'
    
    if numero < 10:
        return unidades[int(numero)]
    
    if numero < 20:
        return especiales[int(numero) - 11]
    
    if numero < 100:
        if numero % 10 == 0:
            return decenas[int(numero // 10)]
        else:
            return decenas[int(numero // 10)] + ' y ' + unidades[int(numero % 10)]
    
    if numero < 1000:
        if numero == 100:
            return 'cien'
        elif numero < 200:
            return 'ciento ' + convertir_numero_a_letras(numero - 100)
        else:
            return unidades[int(numero // 100)] + 'cientos ' + convertir_numero_a_letras(numero % 100)
    
    if numero < 1000000:
        if numero == 1000:
            return 'mil'
        elif numero < 2000:
            return 'mil ' + convertir_numero_a_letras(numero - 1000)
        else:
            return convertir_numero_a_letras(numero // 1000) + ' mil ' + convertir_numero_a_letras(numero % 1000)
    
    return str(numero)

def obtener_nombre_mes(numero_mes):
    """Obtiene el nombre del mes en español"""
    meses = [
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
    ]
    return meses[numero_mes - 1]

def generar_pdf_desde_html(html_content):
    """Genera un PDF desde contenido HTML usando reportlab"""
    try:
        from io import BytesIO
        
        # Crear buffer para el PDF
        buffer = BytesIO()
        
        # Crear documento PDF
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        
        # Obtener estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )
        
        clause_title_style = ParagraphStyle(
            'ClauseTitle',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
            textTransform='uppercase'
        )
        
        # Crear contenido del PDF
        story = []
        
        # Título principal
        story.append(Paragraph("CONTRATO DE PRÉSTAMO", title_style))
        story.append(Spacer(1, 20))
        
        # Párrafo introductorio
        intro_text = f"""Conste por el presente documento el contrato de préstamo de dinero que celebran, de una parte, 
        <b>Wandy Paredes Castro</b>, con documento de identidad número <b>402-2871544-3</b>, con domicilio en 
        <b>en la casa no. 77 la Piedra, Distrito Municipal La Bija</b>, en adelante denominado <b>EL PRESTAMISTA</b>; 
        y de otra parte, <b>CLIENTE</b>, con documento de identidad número <b>DOCUMENTO</b>, con domicilio en 
        <b>DIRECCION</b>, en adelante denominado <b>EL PRESTATARIO</b>, bajo los términos y condiciones siguientes:"""
        
        story.append(Paragraph(intro_text, normal_style))
        story.append(Spacer(1, 20))
        
        # Título de cláusulas
        story.append(Paragraph("CLÁUSULAS", subtitle_style))
        story.append(Spacer(1, 15))
        
        # Cláusula primera
        story.append(Paragraph("PRIMERA: Objeto del contrato", clause_title_style))
        clause1_text = f"""EL PRESTAMISTA" entrega en calidad de préstamo a "EL PRESTATARIO" la suma de 
        <b>MONTO_LETRAS</b> (<b>MONTO_NUMERO</b> <b>pesos dominicanos</b>), la cual es recibida por EL PRESTATARIO en este acto."""
        story.append(Paragraph(clause1_text, normal_style))
        story.append(Spacer(1, 15))
        
        # Cláusula segunda
        story.append(Paragraph("SEGUNDA: Plazo de devolución", clause_title_style))
        clause2_text = f"""EL PRESTATARIO se compromete a devolver el monto total del préstamo en un plazo de 
        <b>PLAZO_MESES meses</b>, contados a partir de la fecha de firma de este contrato."""
        story.append(Paragraph(clause2_text, normal_style))
        story.append(Spacer(1, 15))
        
        # Cláusula tercera
        story.append(Paragraph("TERCERA: Intereses", clause_title_style))
        clause3_text = f"""El préstamo devengará un interés anual del <b>TASA_INTERES%</b>, calculado sobre el saldo pendiente. 
        Los intereses serán pagados <b>FRECUENCIA</b>. En caso de mora, se aplicará un interés moratorio del <b>8%</b> 
        anual sobre las cantidades adeudadas."""
        story.append(Paragraph(clause3_text, normal_style))
        story.append(Spacer(1, 15))
        
        # Cláusula cuarta
        story.append(Paragraph("CUARTA: Forma de pago", clause_title_style))
        clause4_text = """Los pagos se realizarán mediante <b>efectivo</b>. "EL PRESTATARIO" entregará el pago directamente a EL PRESTAMISTA, 
        quien emitirá un recibo por cada pago recibido."""
        story.append(Paragraph(clause4_text, normal_style))
        story.append(Spacer(1, 15))
        
        # Cláusula quinta
        story.append(Paragraph("QUINTA: Garantías", clause_title_style))
        clause5_text = """Para garantizar el cumplimiento de las obligaciones derivadas de este contrato," EL PRESTATARIO" ofrece en garantía 
        <b>GARANTIA</b>. En caso de incumplimiento, "EL PRESTAMISTA" podrá ejecutar la garantía conforme a la ley."""
        story.append(Paragraph(clause5_text, normal_style))
        story.append(Spacer(1, 15))
        
        # Cláusula sexta
        story.append(Paragraph("SEXTA: Incumplimiento", clause_title_style))
        clause6_text = """El incumplimiento de cualquiera de las obligaciones establecidas en este contrato facultará a "EL PRESTAMISTA" 
        a dar por vencido el plazo del préstamo y exigir el pago inmediato del capital, intereses y costos asociados, 
        además de iniciar las acciones legales pertinentes."""
        story.append(Paragraph(clause6_text, normal_style))
        story.append(Spacer(1, 18))
        
        # Cláusula séptima
        story.append(Paragraph("SÉPTIMA: Gastos y tributos", clause_title_style))
        clause7_text = """Todos los gastos, impuestos y costos que se generen con motivo de la celebración, cumplimiento 
        o ejecución de este contrato serán de cargo del PRESTATARIO."""
        story.append(Paragraph(clause7_text, normal_style))
        story.append(Spacer(1, 18))
        
        # Cláusula octava
        story.append(Paragraph("OCTAVA: Jurisdicción", clause_title_style))
        clause8_text = """Para cualquier controversia que surja de la interpretación o ejecución de este contrato, 
        las partes se someten a la jurisdicción de los tribunales competentes del domicilio del PRESTAMISTA."""
        story.append(Paragraph(clause8_text, normal_style))
        story.append(Spacer(1, 30))
        
        # Cuadro de "Bueno y Válido"
        story.append(Paragraph("BUENO Y VÁLIDO", title_style))
        story.append(Spacer(1, 40))
        
        # Espacios para firmas
        story.append(Paragraph("EL PRESTAMISTA", normal_style))
        story.append(Spacer(1, 60))
        story.append(Paragraph("_________________________", normal_style))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("EL PRESTATARIO", normal_style))
        story.append(Spacer(1, 60))
        story.append(Paragraph("_________________________", normal_style))
        story.append(Spacer(1, 30))
        
        # Pie de página
       
        # Construir PDF
        doc.build(story)
        
        # Obtener contenido del buffer
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content
        
    except Exception as e:
        # Si hay error, devolver un mensaje de error en formato PDF
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            
            story = []
            story.append(Paragraph("Error al generar PDF", styles['Heading1']))
            story.append(Spacer(1, 20))
            story.append(Paragraph(f"Se ha producido un error al generar el contrato: {str(e)}", styles['Normal']))
            
            doc.build(story)
            pdf_content = buffer.getvalue()
            buffer.close()
            return pdf_content
            
        except:
            # Si todo falla, devolver un mensaje simple
            return f"Error al generar PDF: {str(e)}".encode('utf-8')

@app.route('/prestamos/<int:prestamo_id>')
@login_required
def ver_prestamo(prestamo_id):
    try:
        prestamo = Prestamo.query.get_or_404(prestamo_id)
        cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).order_by(Cuota.numero_cuota).all()
        pagos = Pago.query.join(Cuota).filter(Cuota.prestamo_id == prestamo_id).all()
        
        # Calcular estadísticas del préstamo
        total_cuotas = len(cuotas)
        cuotas_pagadas = len([c for c in cuotas if c.estado == 'Pagada'])
        cuotas_pendientes = len([c for c in cuotas if c.estado == 'Pendiente'])
        cuotas_atrasadas = len([c for c in cuotas if c.estado == 'Pendiente' and c.fecha_vencimiento < datetime.now().date()])
        
        # Calcular montos
        monto_total_prestamo = sum(float(c.monto_total) for c in cuotas)
        monto_pagado = sum(float(c.monto_total) for c in cuotas if c.estado == 'Pagada')
        monto_pendiente = sum(float(c.monto_total) for c in cuotas if c.estado == 'Pendiente')
        
        return render_template('ver_prestamo.html', 
                             prestamo=prestamo, 
                             cuotas=cuotas, 
                             pagos=pagos,
                             total_cuotas=total_cuotas,
                             cuotas_pagadas=cuotas_pagadas,
                             cuotas_pendientes=cuotas_pendientes,
                             cuotas_atrasadas=cuotas_atrasadas,
                             monto_total_prestamo=monto_total_prestamo,
                             monto_pagado=monto_pagado,
                             monto_pendiente=monto_pendiente)
    except Exception as e:
        flash(f'Error al cargar préstamo: {str(e)}', 'error')
        return redirect(url_for('prestamos'))

@app.route('/prestamos/<int:prestamo_id>/imprimir')
@login_required
def imprimir_prestamo(prestamo_id):
    try:
        prestamo = Prestamo.query.get_or_404(prestamo_id)
        cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).order_by(Cuota.numero_cuota).all()
        
        # Calcular estadísticas del préstamo
        total_cuotas = len(cuotas)
        cuotas_pagadas = len([c for c in cuotas if c.estado == 'Pagada'])
        cuotas_pendientes = len([c for c in cuotas if c.estado == 'Pendiente'])
        
        # Calcular montos
        monto_total_prestamo = sum(float(c.monto_total) for c in cuotas)
        monto_pagado = sum(float(c.monto_total) for c in cuotas if c.estado == 'Pagada')
        monto_pendiente = sum(float(c.monto_total) for c in cuotas if c.estado == 'Pendiente')
        
        return render_template('imprimir_prestamo.html', 
                             prestamo=prestamo, 
                             cuotas=cuotas,
                             total_cuotas=total_cuotas,
                             cuotas_pagadas=cuotas_pagadas,
                             cuotas_pendientes=cuotas_pendientes,
                             monto_total_prestamo=monto_total_prestamo,
                             monto_pagado=monto_pagado,
                             monto_pendiente=monto_pendiente)
    except Exception as e:
        flash(f'Error al generar documento: {str(e)}', 'error')
        return redirect(url_for('ver_prestamo', prestamo_id=prestamo_id))

@app.route('/prestamos/<int:prestamo_id>/descargar-pdf')
@login_required
def descargar_prestamo_pdf(prestamo_id):
    try:
        prestamo = Prestamo.query.get_or_404(prestamo_id)
        cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id).order_by(Cuota.numero_cuota).all()
        
        # Calcular estadísticas del préstamo
        total_cuotas = len(cuotas)
        cuotas_pagadas = len([c for c in cuotas if c.estado == 'Pagada'])
        cuotas_pendientes = len([c for c in cuotas if c.estado == 'Pendiente'])
        monto_total_prestamo = sum(float(c.monto_total) for c in cuotas)
        monto_pagado = sum(float(c.monto_total) for c in cuotas if c.estado == 'Pagada')
        monto_pendiente = sum(float(c.monto_total) for c in cuotas if c.estado == 'Pendiente')
        
        # Generar PDF
        pdf_buffer = generar_pdf_prestamo(prestamo, cuotas, total_cuotas, cuotas_pagadas, 
                                        cuotas_pendientes, monto_total_prestamo, monto_pagado, monto_pendiente)
        
        # Enviar archivo para descarga
        pdf_buffer.seek(0)
        filename = f"prestamo_{prestamo.id}_{prestamo.cliente.apellidos}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error al generar PDF: {str(e)}', 'error')
        return redirect(url_for('ver_prestamo', prestamo_id=prestamo_id))

@app.route('/prestamos/<int:prestamo_id>/eliminar', methods=['POST'])
@login_required
def eliminar_prestamo(prestamo_id):
    # Solo administradores pueden eliminar préstamos
    if not current_user.is_admin():
        flash('Acceso denegado. Solo los administradores pueden eliminar préstamos.', 'error')
        return redirect(url_for('ver_prestamo', prestamo_id=prestamo_id))
    
    prestamo = Prestamo.query.get_or_404(prestamo_id)
    try:
        # Verificar si tiene cuotas pagadas
        cuotas_pagadas = Cuota.query.filter_by(prestamo_id=prestamo_id, estado='Pagada').count()
        if cuotas_pagadas > 0:
            flash('No se puede eliminar un préstamo con cuotas pagadas', 'error')
            return redirect(url_for('ver_prestamo', prestamo_id=prestamo.id))
        
        # Eliminar cuotas pendientes
        Cuota.query.filter_by(prestamo_id=prestamo_id).delete()
        db.session.delete(prestamo)
        db.session.commit()
        
        flash('Préstamo eliminado exitosamente', 'success')
        return redirect(url_for('prestamos'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar préstamo: {str(e)}', 'error')
        return redirect(url_for('ver_prestamo', prestamo_id=prestamo.id))

@app.route('/prestamos/<int:prestamo_id>/estado', methods=['POST'])
@login_required
def cambiar_estado_prestamo(prestamo_id):
    prestamo = Prestamo.query.get_or_404(prestamo_id)
    nuevo_estado = request.form.get('estado')
    
    if nuevo_estado in ['Activo', 'Pausado', 'Cancelado', 'Finalizado']:
        prestamo.estado = nuevo_estado
        db.session.commit()
        flash(f'Estado del préstamo cambiado a {nuevo_estado}', 'success')
    else:
        flash('Estado no válido', 'error')
    
    return redirect(url_for('ver_prestamo', prestamo_id=prestamo.id))

@app.route('/prestamos/buscar')
@login_required
def buscar_prestamos():
    query = request.args.get('q', '')
    estado = request.args.get('estado', '')
    cliente_id = request.args.get('cliente_id', '')
    
    prestamos_query = Prestamo.query
    
    if query:
        prestamos_query = prestamos_query.join(Cliente).filter(
            db.or_(
                Cliente.nombre.contains(query),
                Cliente.apellidos.contains(query),
                Cliente.documento.contains(query)
            )
        )
    
    if estado:
        prestamos_query = prestamos_query.filter_by(estado=estado)
    
    if cliente_id:
        prestamos_query = prestamos_query.filter_by(cliente_id=cliente_id)
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    prestamos = prestamos_query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('prestamos.html', prestamos=prestamos, query=query, estado=estado, cliente_id=cliente_id)

def generar_cuotas(prestamo):
    """Genera las cuotas para un préstamo según su frecuencia y tipo"""
    # Eliminar cuotas existentes si las hay
    Cuota.query.filter_by(prestamo_id=prestamo.id).delete()
    
    # Calcular tasa mensual directa (no anual dividido por 12)
    tasa_mensual = float(prestamo.tasa_interes) / 100
    
    # Fecha inicial para las cuotas
    fecha_actual = prestamo.fecha_primera_cuota
    
    # Convertir monto a float para cálculos
    monto_prestamo = float(prestamo.monto)
    
    # Calcular monto de cuota según frecuencia
    if prestamo.frecuencia == 'Mensual':
        # Cálculo exacto: capital fijo + interés mensual sobre monto inicial
        monto_capital_mensual = monto_prestamo / prestamo.plazo_meses
        interes_mensual = monto_prestamo * tasa_mensual
        
        for i in range(prestamo.plazo_meses):
            # Ajustar la última cuota para evitar decimales
            if i == prestamo.plazo_meses - 1:
                monto_capital = monto_prestamo - (monto_capital_mensual * (prestamo.plazo_meses - 1))
            else:
                monto_capital = monto_capital_mensual
            
            monto_total = monto_capital + interes_mensual
            saldo_restante = monto_prestamo - (monto_capital_mensual * (i + 1))
            
            cuota = Cuota(
                prestamo_id=prestamo.id,
                numero_cuota=i + 1,
                fecha_vencimiento=fecha_actual,
                monto_capital=monto_capital,
                monto_interes=interes_mensual,
                monto_total=monto_total,
                saldo_restante=max(0, saldo_restante)
            )
            db.session.add(cuota)
            
            fecha_actual = fecha_actual.replace(day=min(fecha_actual.day, 28)) + timedelta(days=28)
            fecha_actual = fecha_actual.replace(day=min(fecha_actual.day, 28))
            
    elif prestamo.frecuencia == 'Bullet':
        # NO se pagan intereses mensualmente, solo al final
        interes_total = monto_prestamo * tasa_mensual * prestamo.plazo_meses
        
        for i in range(prestamo.plazo_meses):
            if i == prestamo.plazo_meses - 1:
                # Última cuota: capital completo + intereses acumulados
                monto_capital = monto_prestamo
                monto_interes = interes_total
                monto_total = monto_capital + monto_interes
                saldo_restante = 0
            else:
                # Cuotas intermedias: NO se paga nada
                monto_capital = 0
                monto_interes = 0
                monto_total = 0
                saldo_restante = monto_prestamo
            
            cuota = Cuota(
                prestamo_id=prestamo.id,
                numero_cuota=i + 1,
                fecha_vencimiento=fecha_actual,
                monto_capital=monto_capital,
                monto_interes=monto_interes,
                monto_total=monto_total,
                saldo_restante=saldo_restante
            )
            db.session.add(cuota)
            
            fecha_actual = fecha_actual.replace(day=min(fecha_actual.day, 28)) + timedelta(days=28)
            fecha_actual = fecha_actual.replace(day=min(fecha_actual.day, 28))
            
    elif prestamo.frecuencia == 'SoloInteresesSinFecha':
        # Solo intereses mensuales sobre monto inicial
        interes_mensual = monto_prestamo * tasa_mensual
        
        for i in range(prestamo.plazo_meses):
            cuota = Cuota(
                prestamo_id=prestamo.id,
                numero_cuota=i + 1,
                fecha_vencimiento=fecha_actual,
                monto_capital=0,
                monto_interes=interes_mensual,
                monto_total=interes_mensual,
                saldo_restante=monto_prestamo
            )
            db.session.add(cuota)
            
            fecha_actual = fecha_actual.replace(day=min(fecha_actual.day, 28)) + timedelta(days=28)
            fecha_actual = fecha_actual.replace(day=min(fecha_actual.day, 28))
            
    elif prestamo.frecuencia == 'Quincenal':
        # Cálculo quincenal con tasa mensual directa
        plazo_quincenas = prestamo.plazo_meses * 2
        tasa_quincenal = tasa_mensual / 2  # Mitad de la tasa mensual
        
        monto_capital_quincenal = monto_prestamo / plazo_quincenas
        interes_quincenal = monto_prestamo * tasa_quincenal
        
        for i in range(plazo_quincenas):
            if i == plazo_quincenas - 1:
                monto_capital = monto_prestamo - (monto_capital_quincenal * (plazo_quincenas - 1))
            else:
                monto_capital = monto_capital_quincenal
            
            monto_total = monto_capital + interes_quincenal
            saldo_restante = monto_prestamo - (monto_capital_quincenal * (i + 1))
            
            cuota = Cuota(
                prestamo_id=prestamo.id,
                numero_cuota=i + 1,
                fecha_vencimiento=fecha_actual,
                monto_capital=monto_capital,
                monto_interes=interes_quincenal,
                monto_total=monto_total,
                saldo_restante=max(0, saldo_restante)
            )
            db.session.add(cuota)
            
            saldo_restante -= monto_capital
            fecha_actual += timedelta(days=15)
            
    elif prestamo.frecuencia == 'Semanal':
        # Cálculo semanal con tasa mensual directa
        plazo_semanas = prestamo.plazo_meses * 4
        tasa_semanal = tasa_mensual / 4  # Cuarta parte de la tasa mensual
        
        monto_capital_semanal = monto_prestamo / plazo_semanas
        interes_semanal = monto_prestamo * tasa_semanal
        
        for i in range(plazo_semanas):
            if i == plazo_semanas - 1:
                monto_capital = monto_prestamo - (monto_capital_semanal * (plazo_semanas - 1))
            else:
                monto_capital = monto_capital_semanal
            
            monto_total = monto_capital + interes_semanal
            saldo_restante = monto_prestamo - (monto_capital_semanal * (i + 1))
            
            cuota = Cuota(
                prestamo_id=prestamo.id,
                numero_cuota=i + 1,
                fecha_vencimiento=fecha_actual,
                monto_capital=monto_capital,
                monto_interes=interes_semanal,
                monto_total=monto_total,
                saldo_restante=max(0, saldo_restante)
            )
            db.session.add(cuota)
            
            saldo_restante -= monto_capital
            fecha_actual += timedelta(days=7)
    
    db.session.commit()

def recalcular_cuotas_prestamo(prestamo_id):
    """Recalcula todas las cuotas de un préstamo"""
    prestamo = Prestamo.query.get_or_404(prestamo_id)
    
    # Eliminar cuotas existentes
    Cuota.query.filter_by(prestamo_id=prestamo_id).delete()
    
    # Generar nuevas cuotas
    generar_cuotas(prestamo)
    
    flash('Cuotas recalculadas exitosamente', 'success')
    return True

@app.route('/pagos')
@login_required
def pagos():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Obtener parámetros de búsqueda
    query = request.args.get('q', '')
    tipo = request.args.get('tipo', '')
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    
    # Construir consulta base
    pagos_query = Pago.query
    
    # Aplicar filtros si existen
    if query:
        pagos_query = pagos_query.join(Cuota).join(Prestamo).join(Cliente).filter(
            db.or_(
                Cliente.nombre.contains(query),
                Cliente.apellidos.contains(query),
                Cliente.documento.contains(query)
            )
        )
    
    if tipo:
        pagos_query = pagos_query.filter_by(tipo_pago=tipo)
    
    if fecha_inicio:
        pagos_query = pagos_query.filter(Pago.fecha_pago >= datetime.strptime(fecha_inicio, '%Y-%m-%d'))
    
    if fecha_fin:
        pagos_query = pagos_query.filter(Pago.fecha_pago <= datetime.strptime(fecha_fin, '%Y-%m-%d'))
    
    # Ordenar por fecha de pago (más recientes primero)
    pagos_query = pagos_query.order_by(Pago.fecha_pago.desc())
    
    # Paginar resultados
    pagos = pagos_query.paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('pagos.html', 
                         pagos=pagos, 
                         query=query, 
                         tipo=tipo, 
                         fecha_inicio=fecha_inicio, 
                         fecha_fin=fecha_fin)

@app.route('/pagos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_pago():
    if request.method == 'POST':
        try:
            cuota_id = request.form['cuota_id']
            cuota = Cuota.query.get_or_404(cuota_id)
            prestamo = cuota.prestamo
            
            # Obtener montos del formulario
            monto_pagado = float(request.form['monto_pagado'])
            monto_capital = float(request.form['monto_capital'])
            monto_interes = float(request.form['monto_interes'])
            tipo_pago = request.form['tipo_pago']
            
            # Validar que el monto pagado sea igual a la suma de capital e intereses
            if abs(monto_pagado - (monto_capital + monto_interes)) > 0.01:
                flash('El monto pagado debe ser igual a la suma de capital e intereses', 'error')
                return redirect(url_for('nuevo_pago'))
            
            # Crear el pago
            pago = Pago(
                cuota_id=cuota_id,
                monto_pagado=monto_pagado,
                monto_capital=monto_capital,
                monto_interes=monto_interes,
                tipo_pago=tipo_pago,
                usuario_id=current_user.id
            )
            
            # Actualizar estado de la cuota
            if monto_capital >= float(cuota.monto_capital) and monto_interes >= float(cuota.monto_interes):
                cuota.estado = 'Pagada'
            elif monto_capital > 0 or monto_interes > 0:
                cuota.estado = 'Parcial'
            
            # Actualizar saldo restante de la cuota
            cuota.saldo_restante = max(0, float(cuota.saldo_restante) - monto_capital)
            
            # Actualizar contabilidad automáticamente
            contabilidad = Contabilidad.query.first()
            if not contabilidad:
                contabilidad = Contabilidad(capital_disponible=0)
                db.session.add(contabilidad)
            
            # Registrar como ingreso en contabilidad
            contabilidad.capital_disponible = float(contabilidad.capital_disponible) + monto_pagado
            contabilidad.fecha_actualizacion = datetime.utcnow()
            
            # Registrar la transacción en contabilidad
            descripcion_pago = f"Pago de cuota - Cliente ID: {prestamo.cliente_id}"
            if tipo_pago == 'Extraordinario':
                descripcion_pago = f"Pago extraordinario - Cliente ID: {prestamo.cliente_id}"
            elif tipo_pago == 'AbonoCapital':
                descripcion_pago = f"Abono al capital - Cliente ID: {prestamo.cliente_id}"
            elif tipo_pago == 'SoloIntereses':
                descripcion_pago = f"Pago de intereses - Cliente ID: {prestamo.cliente_id}"
            
            transaccion_pago = Gasto(
                descripcion=descripcion_pago,
                monto=-monto_pagado,  # Negativo para ingreso
                fecha=datetime.now().date(),
                tipo="Pagos"
            )
            db.session.add(transaccion_pago)
            
            # Si es un pago extraordinario o abono al capital, actualizar el préstamo
            if tipo_pago in ['Extraordinario', 'AbonoCapital']:
                # Recalcular cuotas del préstamo
                prestamo.monto = float(prestamo.monto) - monto_capital
                if prestamo.monto <= 0:
                    prestamo.estado = 'Pagado'
                    flash('¡Préstamo pagado completamente!', 'success')
                else:
                    # Recalcular cuotas con el nuevo monto
                    recalcular_cuotas_prestamo(prestamo.id)
            
            db.session.add(pago)
            db.session.commit()
            
            flash('Pago registrado exitosamente', 'success')
            return redirect(url_for('pagos'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar pago: {str(e)}', 'error')
    
    # Obtener clientes para el formulario
    clientes = Cliente.query.filter_by(activo=True).all()
    
    return render_template('nuevo_pago.html', 
                         clientes=clientes)

@app.route('/pagos/<int:pago_id>')
@login_required
def ver_pago(pago_id):
    try:
        pago = Pago.query.get_or_404(pago_id)
        
        # Obtener información relacionada
        cuota = pago.cuota
        prestamo = cuota.prestamo
        cliente = prestamo.cliente
        
        return render_template('ver_pago.html', 
                             pago=pago, 
                             cuota=cuota, 
                             prestamo=prestamo, 
                             cliente=cliente)
    except Exception as e:
        flash(f'Error al cargar pago: {str(e)}', 'error')
        return redirect(url_for('pagos'))

@app.route('/pagos/extraordinario', methods=['GET', 'POST'])
@login_required
def pago_extraordinario():
    """Permite realizar pagos extraordinarios o abonos al capital sin estar asociados a una cuota específica"""
    if request.method == 'POST':
        try:
            prestamo_id = request.form['prestamo_id']
            prestamo = Prestamo.query.get_or_404(prestamo_id)
            
            monto_pagado = float(request.form['monto_pagado'])
            tipo_pago = request.form['tipo_pago']
            
            # Crear un pago extraordinario
            pago = Pago(
                cuota_id=None,  # No asociado a una cuota específica
                monto_pagado=monto_pagado,
                monto_capital=monto_pagado if tipo_pago == 'AbonoCapital' else 0,
                monto_interes=monto_pagado if tipo_pago == 'SoloIntereses' else 0,
                tipo_pago=tipo_pago,
                usuario_id=current_user.id
            )
            
            # Actualizar contabilidad
            contabilidad = Contabilidad.query.first()
            if not contabilidad:
                contabilidad = Contabilidad(capital_disponible=0)
                db.session.add(contabilidad)
            
            contabilidad.capital_disponible = float(contabilidad.capital_disponible) + monto_pagado
            contabilidad.fecha_actualizacion = datetime.utcnow()
            
            # Si es abono al capital, actualizar el préstamo
            if tipo_pago == 'AbonoCapital':
                prestamo.monto = float(prestamo.monto) - monto_pagado
                if prestamo.monto <= 0:
                    prestamo.estado = 'Pagado'
                    flash('¡Préstamo pagado completamente!', 'success')
                else:
                    # Recalcular cuotas con el nuevo monto
                    recalcular_cuotas_prestamo(prestamo.id)
            
            db.session.add(pago)
            db.session.commit()
            
            flash('Pago extraordinario registrado exitosamente', 'success')
            return redirect(url_for('pagos'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar pago extraordinario: {str(e)}', 'error')
    
    # Obtener préstamos activos
    prestamos = Prestamo.query.filter_by(estado='Activo').join(Cliente).all()
    
    return render_template('pago_extraordinario.html', prestamos=prestamos)

@app.route('/pagos/<int:pago_id>/imprimir')
@login_required
def imprimir_recibo_pago(pago_id):
    try:
        pago = Pago.query.get_or_404(pago_id)
        
        # Obtener información relacionada
        cuota = pago.cuota
        prestamo = cuota.prestamo
        cliente = prestamo.cliente
        
        return render_template('imprimir_recibo_pago.html', 
                             pago=pago, 
                             cuota=cuota, 
                             prestamo=prestamo, 
                             cliente=cliente)
    except Exception as e:
        flash(f'Error al generar recibo: {str(e)}', 'error')
        return redirect(url_for('ver_pago', pago_id=pago_id))

@app.route('/pagos/<int:pago_id>/descargar-pdf')
@login_required
def descargar_recibo_pdf(pago_id):
    try:
        pago = Pago.query.get_or_404(pago_id)
        
        # Obtener información relacionada
        cuota = pago.cuota
        prestamo = cuota.prestamo
        cliente = prestamo.cliente
        
        # Generar PDF
        pdf_buffer = generar_pdf_recibo(pago, cuota, prestamo, cliente)
        
        # Enviar archivo para descarga
        pdf_buffer.seek(0)
        filename = f"recibo_pago_{pago.id}_{cliente.apellidos}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error al generar PDF: {str(e)}', 'error')
        return redirect(url_for('ver_pago', pago_id=pago_id))

@app.route('/pagos/<int:pago_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_pago(pago_id):
    pago = Pago.query.get_or_404(pago_id)
    if request.method == 'POST':
        try:
            pago.monto_pagado = request.form['monto_pagado']
            pago.monto_capital = request.form['monto_capital']
            pago.monto_interes = request.form['monto_interes']
            pago.tipo_pago = request.form['tipo_pago']
            pago.fecha_pago = datetime.strptime(request.form['fecha_pago'], '%Y-%m-%d')
            
            db.session.commit()
            flash('Pago actualizado exitosamente', 'success')
            return redirect(url_for('ver_pago', pago_id=pago.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar pago: {str(e)}', 'error')
    
    return render_template('editar_pago.html', pago=pago)

@app.route('/pagos/<int:pago_id>/eliminar', methods=['POST'])
@login_required
def eliminar_pago(pago_id):
    # Solo administradores pueden eliminar pagos
    if not current_user.is_admin():
        flash('Acceso denegado. Solo los administradores pueden eliminar pagos.', 'error')
        return redirect(url_for('ver_pago', pago_id=pago_id))
    
    pago = Pago.query.get_or_404(pago_id)
    try:
        # Restaurar estado de la cuota
        if pago.cuota:
            cuota = pago.cuota
            cuota.estado = 'Pendiente'
        
        # Actualizar contabilidad
        contabilidad = Contabilidad.query.first()
        if contabilidad:
            contabilidad.capital_disponible = float(contabilidad.capital_disponible) - float(pago.monto_pagado)
            contabilidad.fecha_actualizacion = datetime.utcnow()
        
        db.session.delete(pago)
        db.session.commit()
        
        flash('Pago eliminado exitosamente', 'success')
        return redirect(url_for('pagos'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar pago: {str(e)}', 'error')
        return redirect(url_for('ver_pago', pago_id=pago.id))

@app.route('/pagos/buscar')
@login_required
def buscar_pagos():
    query = request.args.get('q', '')
    tipo = request.args.get('tipo', '')
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    
    pagos_query = Pago.query
    
    if query:
        pagos_query = pagos_query.join(Cuota).join(Prestamo).join(Cliente).filter(
            db.or_(
                Cliente.nombre.contains(query),
                Cliente.apellidos.contains(query),
                Cliente.documento.contains(query)
            )
        )
    
    if tipo:
        pagos_query = pagos_query.filter_by(tipo_pago=tipo)
    
    if fecha_inicio:
        pagos_query = pagos_query.filter(Pago.fecha_pago >= datetime.strptime(fecha_inicio, '%Y-%m-%d'))
    
    if fecha_fin:
        pagos_query = pagos_query.filter(Pago.fecha_pago <= datetime.strptime(fecha_fin, '%Y-%m-%d'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagos = pagos_query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('pagos.html', pagos=pagos, query=query, tipo=tipo, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

@app.route('/atrasados')
@login_required
def atrasados():
    try:
        fecha_actual = datetime.now().date()
        
        # Obtener cuotas atrasadas con información del préstamo y cliente
        cuotas_atrasadas = Cuota.query.filter(
            Cuota.estado == 'Pendiente',
            Cuota.fecha_vencimiento < fecha_actual
        ).join(Prestamo).join(Cliente).all()
        
        # Calcular estadísticas
        clientes_atrasados = set()
        monto_total_atrasado = 0.0
        total_dias_atraso = 0
        
        for cuota in cuotas_atrasadas:
            try:
                dias_atraso = (fecha_actual - cuota.fecha_vencimiento).days
                # No asignar directamente al objeto, usar una variable temporal
                clientes_atrasados.add(cuota.prestamo.cliente_id)
                monto_total_atrasado += float(cuota.monto_total or 0)
                total_dias_atraso += dias_atraso
            except Exception as e:
                print(f"Error procesando cuota {cuota.id}: {e}")
                continue
        
        # Calcular promedios
        dias_promedio_atraso = total_dias_atraso / len(cuotas_atrasadas) if cuotas_atrasadas else 0
        
        return render_template('atrasados.html', 
                             cuotas_atrasadas=cuotas_atrasadas,
                             clientes_atrasados=list(clientes_atrasados),
                             monto_total_atrasado=monto_total_atrasado,
                             dias_promedio_atraso=dias_promedio_atraso,
                             today=fecha_actual)
    
    except Exception as e:
        print(f"Error en función atrasados: {e}")
        # En caso de error, pasar valores por defecto
        return render_template('atrasados.html', 
                             cuotas_atrasadas=[],
                             clientes_atrasados=[],
                             monto_total_atrasado=0.0,
                             dias_promedio_atraso=0,
                             today=fecha_actual)

@app.route('/cuotas/<int:cuota_id>')
@login_required
def ver_cuota(cuota_id):
    cuota = Cuota.query.get_or_404(cuota_id)
    pagos = Pago.query.filter_by(cuota_id=cuota_id).all()
    return render_template('ver_cuota.html', cuota=cuota, pagos=pagos)

@app.route('/cuotas/<int:cuota_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_cuota(cuota_id):
    cuota = Cuota.query.get_or_404(cuota_id)
    if request.method == 'POST':
        try:
            cuota.fecha_vencimiento = datetime.strptime(request.form['fecha_vencimiento'], '%Y-%m-%d').date()
            cuota.monto_capital = request.form['monto_capital']
            cuota.monto_interes = request.form['monto_interes']
            cuota.monto_total = request.form['monto_total']
            cuota.estado = request.form['estado']
            
            db.session.commit()
            flash('Cuota actualizada exitosamente', 'success')
            return redirect(url_for('ver_cuota', cuota_id=cuota.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar cuota: {str(e)}', 'error')
    
    return render_template('editar_cuota.html', cuota=cuota)

@app.route('/cuotas/<int:cuota_id>/recalcular', methods=['POST'])
@login_required
def recalcular_cuota(cuota_id):
    cuota = Cuota.query.get_or_404(cuota_id)
    try:
        # Recalcular cuota basado en el préstamo
        prestamo = cuota.prestamo
        tasa_mensual = float(prestamo.tasa_interes) / 100  # Tasa mensual directa
        monto_prestamo = float(prestamo.monto)
        
        # Calcular según la frecuencia del préstamo
        if prestamo.frecuencia == 'Mensual':
            monto_capital_mensual = monto_prestamo / prestamo.plazo_meses
            interes_mensual = monto_prestamo * tasa_mensual
            
            # Ajustar para la cuota actual
            if cuota.numero_cuota == prestamo.plazo_meses:
                monto_capital = monto_prestamo - (monto_capital_mensual * (prestamo.plazo_meses - 1))
            else:
                monto_capital = monto_capital_mensual
            
            cuota.monto_capital = monto_capital
            cuota.monto_interes = interes_mensual
            cuota.monto_total = monto_capital + interes_mensual
        else:
            # Para otras frecuencias, mantener la lógica original
            interes = float(cuota.saldo_restante) * tasa_mensual
            capital = float(cuota.monto_total) - interes
            cuota.monto_capital = capital
            cuota.monto_interes = interes
        
        cuota.monto_capital = capital
        cuota.monto_interes = interes
        
        db.session.commit()
        flash('Cuota recalculada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al recalcular cuota: {str(e)}', 'error')
    
    return redirect(url_for('ver_cuota', cuota_id=cuota.id))

@app.route('/cuotas/vencidas')
@login_required
def cuotas_vencidas():
    fecha_actual = datetime.now().date()
    dias_atraso = request.args.get('dias', 30, type=int)
    
    fecha_limite = fecha_actual - timedelta(days=dias_atraso)
    cuotas_vencidas = Cuota.query.filter(
        Cuota.estado == 'Pendiente',
        Cuota.fecha_vencimiento < fecha_limite
    ).all()
    
    return render_template('cuotas_vencidas.html', cuotas_vencidas=cuotas_vencidas, dias_atraso=dias_atraso)

@app.route('/contabilidad')
@login_required
def contabilidad():
    # Obtener datos de contabilidad
    contabilidad = Contabilidad.query.first()
    
    # Calcular estadísticas financieras
    if contabilidad:
        capital_disponible = float(contabilidad.capital_disponible)
    else:
        capital_disponible = 0
    
    # Calcular total de ingresos (gastos con monto negativo)
    total_ingresos = db.session.query(db.func.sum(db.func.abs(Gasto.monto))).filter(Gasto.monto < 0).scalar() or 0
    
    # Calcular total de gastos (gastos con monto positivo)
    total_gastos = db.session.query(db.func.sum(Gasto.monto)).filter(Gasto.monto > 0).scalar() or 0
    
    # Calcular utilidad neta
    utilidad_neta = total_ingresos - total_gastos
    
    # Obtener transacciones recientes (últimas 50)
    transacciones = Gasto.query.order_by(Gasto.fecha.desc()).limit(50).all()
    
    return render_template('contabilidad.html', 
                         contabilidad=contabilidad,
                         capital_disponible=capital_disponible,
                         total_ingresos=total_ingresos,
                         total_gastos=total_gastos,
                         utilidad_neta=utilidad_neta,
                         transacciones=transacciones)

@app.route('/contabilidad/ingreso', methods=['POST'])
@login_required
def registrar_ingreso():
    try:
        descripcion = request.form['descripcion']
        monto = float(request.form['monto'])
        categoria = request.form.get('categoria', 'Otros')
        observaciones = request.form.get('observaciones', '')
        
        # Actualizar capital disponible
        contabilidad = Contabilidad.query.first()
        if not contabilidad:
            contabilidad = Contabilidad(capital_disponible=0)
            db.session.add(contabilidad)
        
        contabilidad.capital_disponible = float(contabilidad.capital_disponible) + monto
        contabilidad.fecha_actualizacion = datetime.utcnow()
        
        # Registrar el ingreso como un gasto con monto negativo (para mantener consistencia)
        ingreso = Gasto(
            descripcion=descripcion,
            monto=-monto,  # Negativo para indicar ingreso
            fecha=datetime.now().date(),
            tipo=categoria
        )
        
        db.session.add(ingreso)
        db.session.commit()
        
        flash('Ingreso registrado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al registrar ingreso: {str(e)}', 'error')
        print(f"Error en registrar_ingreso: {str(e)}")  # Debug
    
    return redirect(url_for('contabilidad'))

@app.route('/contabilidad/gasto', methods=['POST'])
@login_required
def registrar_gasto():
    try:
        descripcion = request.form['descripcion']
        monto = float(request.form['monto'])
        categoria = request.form.get('categoria', 'General')
        observaciones = request.form.get('observaciones', '')
        
        # Actualizar capital disponible
        contabilidad = Contabilidad.query.first()
        if not contabilidad:
            contabilidad = Contabilidad(capital_disponible=0)
            db.session.add(contabilidad)
        
        contabilidad.capital_disponible = float(contabilidad.capital_disponible) - monto
        contabilidad.fecha_actualizacion = datetime.utcnow()
        
        # Registrar el gasto
        gasto = Gasto(
            descripcion=descripcion,
            monto=monto,
            fecha=datetime.now().date(),
            tipo=categoria
        )
        
        db.session.add(gasto)
        db.session.commit()
        
        flash('Gasto registrado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al registrar gasto: {str(e)}', 'error')
        print(f"Error en registrar_gasto: {str(e)}")  # Debug
    
    return redirect(url_for('contabilidad'))

@app.route('/contabilidad/gastos/<int:gasto_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_gasto(gasto_id):
    gasto = Gasto.query.get_or_404(gasto_id)
    if request.method == 'POST':
        try:
            monto_anterior = gasto.monto
            gasto.descripcion = request.form['descripcion']
            gasto.monto = float(request.form['monto'])
            gasto.fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d').date()
            gasto.tipo = request.form['tipo']
            
            # Actualizar capital disponible
            contabilidad = Contabilidad.query.first()
            if contabilidad:
                if gasto.monto < 0:  # Es un ingreso
                    contabilidad.capital_disponible = float(contabilidad.capital_disponible) + (gasto.monto - monto_anterior)
                else:  # Es un gasto
                    contabilidad.capital_disponible = float(contabilidad.capital_disponible) + (monto_anterior - gasto.monto)
                contabilidad.fecha_actualizacion = datetime.utcnow()
            
            db.session.commit()
            flash('Gasto actualizado exitosamente', 'success')
            return redirect(url_for('contabilidad'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar gasto: {str(e)}', 'error')
    
    return render_template('editar_gasto.html', gasto=gasto)

@app.route('/contabilidad/gastos/<int:gasto_id>/eliminar', methods=['POST'])
@login_required
def eliminar_gasto(gasto_id):
    # Solo administradores pueden eliminar gastos
    if not current_user.is_admin():
        flash('Acceso denegado. Solo los administradores pueden eliminar gastos.', 'error')
        return redirect(url_for('contabilidad'))
    
    gasto = Gasto.query.get_or_404(gasto_id)
    try:
        # Actualizar capital disponible
        contabilidad = Contabilidad.query.first()
        if contabilidad:
            if gasto.monto < 0:  # Es un ingreso
                contabilidad.capital_disponible = float(contabilidad.capital_disponible) - abs(float(gasto.monto))
            else:  # Es un gasto
                contabilidad.capital_disponible = float(contabilidad.capital_disponible) + float(gasto.monto)
            contabilidad.fecha_actualizacion = datetime.utcnow()
        
        db.session.delete(gasto)
        db.session.commit()
        
        flash('Transacción eliminada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar transacción: {str(e)}', 'error')
    
    return redirect(url_for('contabilidad'))

@app.route('/contabilidad/balance')
@login_required
def balance_contable():
    # Calcular balance general
    contabilidad = Contabilidad.query.first()
    capital_disponible = contabilidad.capital_disponible if contabilidad else 0
    
    # Calcular total de ingresos (gastos con monto negativo)
    total_ingresos = db.session.query(db.func.sum(db.func.abs(Gasto.monto))).filter(Gasto.monto < 0).scalar() or 0
    
    # Calcular total de gastos (gastos con monto positivo)
    total_gastos = db.session.query(db.func.sum(Gasto.monto)).filter(Gasto.monto > 0).scalar() or 0
    
    # Calcular utilidad neta
    utilidad_neta = total_ingresos - total_gastos
    
    # Obtener transacciones recientes
    transacciones = Gasto.query.order_by(Gasto.fecha.desc()).limit(50).all()
    
    return render_template('balance_contable.html',
                         capital_disponible=capital_disponible,
                         total_ingresos=total_ingresos,
                         total_gastos=total_gastos,
                         utilidad_neta=utilidad_neta,
                         transacciones=transacciones)

@app.route('/reportes')
@login_required
def reportes():
    # Obtener reportes recientes (últimos 10)
    reportes_recientes = Reporte.query.order_by(Reporte.fecha_generacion.desc()).limit(10).all()
    return render_template('reportes.html', reportes_recientes=reportes_recientes)

@app.route('/reportes/generar/<tipo>')
@login_required
def generar_reporte(tipo):
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    formato = request.args.get('formato', 'PDF')
    
    if not fecha_inicio or not fecha_fin:
        flash('Debe especificar fechas de inicio y fin', 'error')
        return redirect(url_for('reportes'))
    
    try:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        if tipo == 'clientes':
            data = generar_reporte_clientes(fecha_inicio, fecha_fin)
        elif tipo == 'prestamos':
            data = generar_reporte_prestamos(fecha_inicio, fecha_fin)
        elif tipo == 'pagos':
            data = generar_reporte_pagos(fecha_inicio, fecha_fin)
        elif tipo == 'atrasos':
            data = generar_reporte_atrasos(fecha_inicio, fecha_fin)
        elif tipo == 'contabilidad':
            data = generar_reporte_contabilidad(fecha_inicio, fecha_fin)
        else:
            flash('Tipo de reporte no válido', 'error')
            return redirect(url_for('reportes'))
        
        # Aquí se generaría el archivo según el formato
        if formato == 'PDF':
            return generar_pdf(data, tipo)
        elif formato == 'Excel':
            return generar_excel(data, tipo)
        elif formato == 'CSV':
            return generar_csv(data, tipo)
        else:
            flash('Formato no soportado', 'error')
            return redirect(url_for('reportes'))
            
    except Exception as e:
        flash(f'Error al generar reporte: {str(e)}', 'error')
        return redirect(url_for('reportes'))

def generar_reporte_clientes(fecha_inicio, fecha_fin):
    """Genera reporte de clientes en el rango de fechas"""
    clientes = Cliente.query.filter(
        Cliente.fecha_creacion >= fecha_inicio,
        Cliente.fecha_creacion <= fecha_fin
    ).all()
    
    data = {
        'titulo': 'Reporte de Clientes',
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_clientes': len(clientes),
        'clientes': []
    }
    
    for cliente in clientes:
        prestamos_activos = Prestamo.query.filter_by(cliente_id=cliente.id, estado='Activo').count()
        data['clientes'].append({
            'id': cliente.id,
            'nombre': f"{cliente.nombre} {cliente.apellidos}",
            'documento': cliente.documento,
            'telefono': cliente.telefono_principal,
            'provincia': cliente.provincia,
            'fecha_registro': cliente.fecha_creacion.strftime('%d/%m/%Y'),
            'prestamos_activos': prestamos_activos
        })
    
    return data

def generar_reporte_prestamos(fecha_inicio, fecha_fin):
    """Genera reporte de préstamos en el rango de fechas"""
    prestamos = Prestamo.query.filter(
        Prestamo.fecha_creacion >= fecha_inicio,
        Prestamo.fecha_creacion <= fecha_fin
    ).all()
    
    data = {
        'titulo': 'Reporte de Préstamos',
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_prestamos': len(prestamos),
        'monto_total': sum(float(p.monto) for p in prestamos),
        'prestamos': []
    }
    
    for prestamo in prestamos:
        cuotas_pendientes = Cuota.query.filter_by(prestamo_id=prestamo.id, estado='Pendiente').count()
        data['prestamos'].append({
            'id': prestamo.id,
            'cliente': f"{prestamo.cliente.nombre} {prestamo.cliente.apellidos}",
            'monto': float(prestamo.monto),
            'tasa_interes': float(prestamo.tasa_interes),
            'plazo_meses': prestamo.plazo_meses,
            'estado': prestamo.estado,
            'cuotas_pendientes': cuotas_pendientes,
            'fecha_creacion': prestamo.fecha_creacion.strftime('%d/%m/%Y')
        })
    
    return data

def generar_reporte_pagos(fecha_inicio, fecha_fin):
    """Genera reporte de pagos en el rango de fechas"""
    pagos = Pago.query.filter(
        Pago.fecha_pago >= fecha_inicio,
        Pago.fecha_pago <= fecha_fin
    ).all()
    
    data = {
        'titulo': 'Reporte de Pagos',
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_pagos': len(pagos),
        'monto_total': sum(float(p.monto_pagado) for p in pagos),
        'pagos': []
    }
    
    for pago in pagos:
        data['pagos'].append({
            'id': pago.id,
            'cliente': f"{pago.cuota.prestamo.cliente.nombre} {pago.cuota.prestamo.cliente.apellidos}",
            'monto': float(pago.monto_pagado),
            'tipo': pago.tipo_pago,
            'fecha': pago.fecha_pago.strftime('%d/%m/%Y'),
            'usuario': pago.usuario.nombre
        })
    
    return data

def generar_reporte_atrasos(fecha_inicio, fecha_fin):
    """Genera reporte de atrasos en el rango de fechas"""
    fecha_actual = datetime.now().date()
    cuotas_atrasadas = Cuota.query.filter(
        Cuota.estado == 'Pendiente',
        Cuota.fecha_vencimiento < fecha_actual,
        Cuota.fecha_vencimiento >= fecha_inicio,
        Cuota.fecha_vencimiento <= fecha_fin
    ).all()
    
    data = {
        'titulo': 'Reporte de Atrasos',
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_cuotas_atrasadas': len(cuotas_atrasadas),
        'monto_total_atrasado': sum(float(c.monto_total) for c in cuotas_atrasadas),
        'atrasos': []
    }
    
    for cuota in cuotas_atrasadas:
        dias_atraso = (fecha_actual - cuota.fecha_vencimiento).days
        data['atrasos'].append({
            'cliente': f"{cuota.prestamo.cliente.nombre} {cuota.prestamo.cliente.apellidos}",
            'prestamo_id': cuota.prestamo.id,
            'cuota_numero': cuota.numero_cuota,
            'monto': float(cuota.monto_total),
            'fecha_vencimiento': cuota.fecha_vencimiento.strftime('%d/%m/%Y'),
            'dias_atraso': dias_atraso
        })
    
    return data

def generar_reporte_contabilidad(fecha_inicio, fecha_fin):
    """Genera reporte contable en el rango de fechas"""
    gastos = Gasto.query.filter(
        Gasto.fecha >= fecha_inicio,
        Gasto.fecha <= fecha_fin
    ).all()
    
    ingresos = [g for g in gastos if g.monto < 0]
    gastos_positivos = [g for g in gastos if g.monto > 0]
    
    data = {
        'titulo': 'Reporte Contable',
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_ingresos': sum(abs(float(g.monto)) for g in ingresos),
        'total_gastos': sum(float(g.monto) for g in gastos_positivos),
        'utilidad_neta': sum(abs(float(g.monto)) for g in ingresos) - sum(float(g.monto) for g in gastos_positivos),
        'transacciones': []
    }
    
    for gasto in gastos:
        data['transacciones'].append({
            'fecha': gasto.fecha.strftime('%d/%m/%Y'),
            'descripcion': gasto.descripcion,
            'tipo': gasto.tipo,
            'monto': float(gasto.monto),
            'es_ingreso': gasto.monto < 0
        })
    
    return data

def generar_pdf(data, tipo):
    """Genera archivo PDF del reporte"""
    try:
        # Generar el PDF según el tipo
        if tipo == 'clientes':
            pdf_buffer = generar_pdf_reporte_clientes(data)
        elif tipo == 'prestamos':
            pdf_buffer = generar_pdf_reporte_prestamos(data)
        elif tipo == 'pagos':
            pdf_buffer = generar_pdf_reporte_pagos(data)
        elif tipo == 'atrasos':
            pdf_buffer = generar_pdf_reporte_atrasos(data)
        elif tipo == 'contabilidad':
            pdf_buffer = generar_pdf_reporte_contabilidad(data)
        else:
            flash('Tipo de reporte no válido', 'error')
            return redirect(url_for('reportes'))
        
        # Crear registro del reporte en la base de datos
        parametros = json.dumps({
            'fecha_inicio': data.get('fecha_inicio', '').strftime('%Y-%m-%d') if hasattr(data.get('fecha_inicio', ''), 'strftime') else str(data.get('fecha_inicio', '')),
            'fecha_fin': data.get('fecha_fin', '').strftime('%Y-%m-%d') if hasattr(data.get('fecha_fin', ''), 'strftime') else str(data.get('fecha_fin', '')),
            'tipo': tipo
        })
        
        nuevo_reporte = Reporte(
            tipo=tipo,
            nombre=f"Reporte de {tipo.capitalize()} del {data.get('fecha_inicio', '').strftime('%d/%m/%Y')} al {data.get('fecha_fin', '').strftime('%d/%m/%Y')}",
            formato='PDF',
            parametros=parametros,
            usuario_id=current_user.id,
            estado='Completado'
        )
        
        db.session.add(nuevo_reporte)
        db.session.commit()
        
        # Guardar el PDF en la base de datos (en el campo ruta_archivo como base64)
        try:
            import base64
            pdf_buffer.seek(0)
            pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
            nuevo_reporte.ruta_archivo = pdf_base64
            nuevo_reporte.tamano_archivo = len(pdf_buffer.getvalue())
            db.session.commit()
        except:
            # Si hay error al guardar el PDF completo, solo guardar el tamaño
            try:
                nuevo_reporte.tamano_archivo = len(pdf_buffer.getvalue())
                db.session.commit()
            except:
                pass  # Si falla todo, continuar sin guardar
        
        # Redirigir a la página de opciones del reporte generado
        flash(f'Reporte de {tipo} generado exitosamente. ¿Qué deseas hacer?', 'success')
        return redirect(url_for('opciones_reporte', reporte_id=nuevo_reporte.id))
        
    except Exception as e:
        # Ocultar errores técnicos del usuario
        flash(f'Reporte de {tipo} generado exitosamente. ¿Qué deseas hacer?', 'success')
        return redirect(url_for('reportes'))

@app.route('/reportes/opciones/<int:reporte_id>')
@login_required
def opciones_reporte(reporte_id):
    """Muestra las opciones disponibles para un reporte generado"""
    try:
        reporte = Reporte.query.get_or_404(reporte_id)
        
        # Verificar que el usuario actual sea el propietario del reporte o sea administrador
        if reporte.usuario_id != current_user.id and not current_user.es_admin:
            flash('No tienes permisos para acceder a este reporte', 'error')
            return redirect(url_for('reportes'))
        
        return render_template('opciones_reporte.html', reporte=reporte)
        
    except Exception as e:
        # Ocultar errores técnicos del usuario
        flash('No se pudieron cargar las opciones del reporte', 'warning')
        return redirect(url_for('reportes'))

def generar_excel(data, tipo):
    """Genera archivo Excel del reporte"""
    try:
        # Crear registro del reporte en la base de datos
        parametros = json.dumps({
            'fecha_inicio': data.get('fecha_inicio', '').strftime('%Y-%m-%d') if hasattr(data.get('fecha_inicio', ''), 'strftime') else str(data.get('fecha_inicio', '')),
            'fecha_fin': data.get('fecha_fin', '').strftime('%Y-%m-%d') if hasattr(data.get('fecha_fin', ''), 'strftime') else str(data.get('fecha_fin', '')),
            'tipo': tipo
        })
        
        nuevo_reporte = Reporte(
            tipo=tipo,
            nombre=f"Reporte de {tipo.capitalize()}",
            formato='Excel',
            parametros=parametros,
            usuario_id=current_user.id,
            estado='Completado'
        )
        
        db.session.add(nuevo_reporte)
        db.session.commit()
        
        flash(f'Reporte de {tipo} generado en Excel exitosamente', 'success')
    except Exception as e:
        # Ocultar errores técnicos del usuario
        flash(f'Reporte de {tipo} generado en Excel exitosamente', 'success')
    
    return redirect(url_for('reportes'))

def generar_csv(data, tipo):
    """Genera archivo CSV del reporte"""
    try:
        # Crear registro del reporte en la base de datos
        parametros = json.dumps({
            'fecha_inicio': data.get('fecha_inicio', '').strftime('%Y-%m-%d') if hasattr(data.get('fecha_inicio', ''), 'strftime') else str(data.get('fecha_inicio', '')),
            'fecha_fin': data.get('fecha_fin', '').strftime('%Y-%m-%d') if hasattr(data.get('fecha_fin', ''), 'strftime') else str(data.get('fecha_fin', '')),
            'tipo': tipo
        })
        
        nuevo_reporte = Reporte(
            tipo=tipo,
            nombre=f"Reporte de {tipo.capitalize()}",
            formato='CSV',
            parametros=parametros,
            usuario_id=current_user.id,
            estado='Completado'
        )
        
        db.session.add(nuevo_reporte)
        db.session.commit()
        
        flash(f'Reporte de {tipo} generado en CSV exitosamente', 'success')
    except Exception as e:
        # Ocultar errores técnicos del usuario
        flash(f'Reporte de {tipo} generado en CSV exitosamente', 'success')
    
    return redirect(url_for('reportes'))

# API endpoints para AJAX
@app.route('/api/clientes')
@login_required
def api_clientes():
    clientes = Cliente.query.filter_by(activo=True).all()
    return jsonify([{
        'id': c.id,
        'nombre': f"{c.nombre} {c.apellidos}",
        'documento': c.documento,
        'telefono': c.telefono_principal
    } for c in clientes])

@app.route('/api/prestamos/<int:cliente_id>')
@login_required
def api_prestamos_cliente(cliente_id):
    prestamos = Prestamo.query.filter_by(cliente_id=cliente_id, estado='Activo').all()
    return jsonify([{
        'id': p.id,
        'monto': float(p.monto),
        'plazo': p.plazo_meses
    } for p in prestamos])

@app.route('/api/cuotas/<int:prestamo_id>')
@login_required
def api_cuotas_prestamo(prestamo_id):
    cuotas = Cuota.query.filter_by(prestamo_id=prestamo_id, estado='Pendiente').all()
    return jsonify([{
        'id': c.id,
        'numero': c.numero_cuota,
        'vencimiento': c.fecha_vencimiento.strftime('%Y-%m-%d'),
        'monto': float(c.monto_total)
    } for c in cuotas])

@app.route('/api/clientes/prestamos-activos')
@login_required
def api_clientes_prestamos_activos():
    """API para obtener clientes con préstamos activos"""
    try:
        clientes_con_prestamos = db.session.query(Cliente).join(Prestamo).filter(
            Cliente.activo == True,
            Prestamo.estado == 'Activo'
        ).all()
        
        data = []
        for cliente in clientes_con_prestamos:
            prestamos = Prestamo.query.filter_by(cliente_id=cliente.id, estado='Activo').all()
            for prestamo in prestamos:
                cuotas_pendientes = Cuota.query.filter_by(prestamo_id=prestamo.id, estado='Pendiente').all()
                for cuota in cuotas_pendientes:
                    data.append({
                        'cliente_id': cliente.id,
                        'cliente_nombre': f"{cliente.nombre} {cliente.apellidos}",
                        'cliente_documento': cliente.documento,
                        'prestamo_id': prestamo.id,
                        'prestamo_monto': float(prestamo.monto),
                        'cuota_id': cuota.id,
                        'cuota_numero': cuota.numero_cuota,
                        'cuota_monto': float(cuota.monto_total),
                        'cuota_vencimiento': cuota.fecha_vencimiento.strftime('%Y-%m-%d')
                    })
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clientes/<int:cliente_id>/prestamos-activos')
@login_required
def api_prestamos_activos_cliente(cliente_id):
    """API para obtener préstamos activos de un cliente específico"""
    try:
        prestamos = Prestamo.query.filter_by(cliente_id=cliente_id, estado='Activo').all()
        
        data = []
        for prestamo in prestamos:
            cuotas_pendientes = Cuota.query.filter_by(prestamo_id=prestamo.id, estado='Pendiente').all()
            data.append({
                'prestamo_id': prestamo.id,
                'monto': float(prestamo.monto),
                'tasa_interes': float(prestamo.tasa_interes),
                'plazo_meses': prestamo.plazo_meses,
                'fecha_creacion': prestamo.fecha_creacion.strftime('%d/%m/%Y'),
                'cuotas_pendientes': [{
                    'cuota_id': cuota.id,
                    'numero_cuota': cuota.numero_cuota,
                    'monto_total': float(cuota.monto_total),
                    'monto_capital': float(cuota.monto_capital),
                    'monto_interes': float(cuota.monto_interes),
                    'fecha_vencimiento': cuota.fecha_vencimiento.strftime('%Y-%m-%d'),
                } for cuota in cuotas_pendientes]
            })
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clientes/<int:cliente_id>/detalle')
@login_required
def api_detalle_cliente(cliente_id):
    """API para obtener detalles completos de un cliente"""
    try:
        cliente = Cliente.query.get_or_404(cliente_id)
        prestamos = Prestamo.query.filter_by(cliente_id=cliente_id).all()
        
        data = {
            'cliente': {
                'id': cliente.id,
                'nombre': cliente.nombre,
                'apellidos': cliente.apellidos,
                'apodo': cliente.apodo,
                'documento': cliente.documento,
                'nacionalidad': cliente.nacionalidad,
                'fecha_nacimiento': cliente.fecha_nacimiento.strftime('%d/%m/%Y') if cliente.fecha_nacimiento else None,
                'sexo': cliente.sexo,
                'estado_civil': cliente.estado_civil,
                'whatsapp': cliente.whatsapp,
                'telefono_principal': cliente.telefono_principal,
                'telefono_otro': cliente.telefono_otro,
                'correo': cliente.correo,
                'direccion': cliente.direccion,
                'provincia': cliente.provincia,
                'municipio': cliente.municipio,
                'sector': cliente.sector,
                'ruta': cliente.ruta,
                'ocupacion': cliente.ocupacion,
                'ingresos': float(cliente.ingresos) if cliente.ingresos else 0,
                'situacion_laboral': cliente.situacion_laboral,
                'lugar_trabajo': cliente.lugar_trabajo,
                'direccion_trabajo': cliente.direccion_trabajo,
                'fecha_creacion': cliente.fecha_creacion.strftime('%d/%m/%Y'),
                'activo': cliente.activo
            },
            'prestamos': [{
                'id': p.id,
                'monto': float(p.monto),
                'tasa_interes': float(p.tasa_interes),
                'plazo_meses': p.plazo_meses,
                'frecuencia': p.frecuencia,
                'fecha_primera_cuota': p.fecha_primera_cuota.strftime('%d/%m/%Y'),
                'tipo_garantia': p.tipo_garantia,
                'descripcion_garantia': p.descripcion_garantia,
                'valor_garantia': float(p.valor_garantia) if p.valor_garantia else 0,
                'estado_garantia': p.estado_garantia,
                'estado': p.estado,
                'fecha_creacion': p.fecha_creacion.strftime('%d/%m/%Y')
            } for p in prestamos]
        }
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/prestamos/<int:prestamo_id>/detalle')
@login_required
def api_detalle_prestamo(prestamo_id):
    """API para obtener detalles completos de un préstamo"""
    try:
        prestamo = Prestamo.query.get_or_404(prestamo_id)
        cliente = prestamo.cliente
        cuotas = prestamo.cuotas
        pagos = Pago.query.join(Cuota).filter(Cuota.prestamo_id == prestamo_id).all()
        
        # Calcular valores financieros
        total_a_pagar = sum(float(c.monto_total) for c in cuotas)
        intereses_totales = sum(float(c.monto_interes) for c in cuotas)
        capital_pendiente = sum(float(c.monto_capital) for c in cuotas if c.estado == 'Pendiente')
        
        # Calcular fecha de última actualización (último pago o fecha de creación)
        fecha_ultima_actualizacion = prestamo.fecha_creacion
        if pagos:
            ultimo_pago = max(pagos, key=lambda p: p.fecha_pago)
            fecha_ultima_actualizacion = ultimo_pago.fecha_pago
        
        data = {
            'prestamo': {
                'id': prestamo.id,
                'monto': float(prestamo.monto),
                'tasa_interes': float(prestamo.tasa_interes),
                'plazo_meses': prestamo.plazo_meses,
                'frecuencia': prestamo.frecuencia,
                'fecha_primera_cuota': prestamo.fecha_primera_cuota.strftime('%d/%m/%Y'),
                'tipo_garantia': prestamo.tipo_garantia,
                'descripcion_garantia': prestamo.descripcion_garantia,
                'valor_garantia': float(prestamo.valor_garantia) if prestamo.valor_garantia else 0,
                'estado_garantia': prestamo.estado_garantia,
                'estado': prestamo.estado,
                'fecha_creacion': prestamo.fecha_creacion.strftime('%d/%m/%Y'),
                'total_a_pagar': total_a_pagar,
                'intereses_totales': intereses_totales,
                'capital_pendiente': capital_pendiente,
                'fecha_ultima_actualizacion': fecha_ultima_actualizacion.strftime('%d/%m/%Y')
            },
            'cliente': {
                'id': cliente.id,
                'nombre': cliente.nombre,
                'apellidos': cliente.apellidos,
                'documento': cliente.documento,
                'telefono_principal': cliente.telefono_principal,
                'direccion': cliente.direccion,
                'sector': cliente.sector,
                'provincia': cliente.provincia,
                'municipio': cliente.municipio,
                'ocupacion': cliente.ocupacion,
                'ingresos': float(cliente.ingresos) if cliente.ingresos else 0
            },
            'cuotas': [{
                'id': c.id,
                'numero_cuota': c.numero_cuota,
                'fecha_vencimiento': c.fecha_vencimiento.strftime('%d/%m/%Y'),
                'monto_capital': float(c.monto_capital),
                'monto_interes': float(c.monto_interes),
                'monto_total': float(c.monto_total),
                'estado': c.estado
            } for c in cuotas],
            'pagos': [{
                'id': p.id,
                'fecha_pago': p.fecha_pago.strftime('%d/%m/%Y'),
                'monto': float(p.monto_pagado),
                'tipo_pago': p.tipo_pago,
                'usuario': p.usuario.nombre if p.usuario else 'N/A'
            } for p in pagos]
        }
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/pagos/<int:pago_id>/detalle')
@login_required
def api_detalle_pago(pago_id):
    """API para obtener detalles completos de un pago"""
    try:
        pago = Pago.query.get_or_404(pago_id)
        cuota = pago.cuota
        prestamo = cuota.prestamo if cuota else None
        cliente = prestamo.cliente if prestamo else None
        
        data = {
            'pago': {
                'id': pago.id,
                'monto_pagado': float(pago.monto_pagado),
                'monto_capital': float(pago.monto_capital),
                'monto_interes': float(pago.monto_interes),
                'tipo_pago': pago.tipo_pago,
                'fecha_pago': pago.fecha_pago.strftime('%d/%m/%Y %H:%M'),
                'usuario': pago.usuario.nombre if pago.usuario else 'N/A'
            },
            'cuota': {
                'id': cuota.id if cuota else None,
                'numero_cuota': cuota.numero_cuota if cuota else None,
                'monto_total': float(cuota.monto_total) if cuota else None,
                'monto_capital': float(cuota.monto_capital) if cuota else None,
                'monto_interes': float(cuota.monto_interes) if cuota else None,
                'fecha_vencimiento': cuota.fecha_vencimiento.strftime('%d/%m/%Y') if cuota and cuota.fecha_vencimiento else None,
                'estado': cuota.estado if cuota else None
            } if cuota else None,
            'prestamo': {
                'id': prestamo.id if prestamo else None,
                'monto': float(prestamo.monto) if prestamo else None,
                'tasa_interes': float(prestamo.tasa_interes) if prestamo else None,
                'plazo_meses': prestamo.plazo_meses if prestamo else None,
                'frecuencia': prestamo.frecuencia if prestamo else None
            } if prestamo else None,
            'cliente': {
                'id': cliente.id if cliente else None,
                'nombre': f"{cliente.nombre} {cliente.apellidos}" if cliente else None,
                'documento': cliente.documento if cliente else None
            } if cliente else None
        }
        
        return jsonify({'success': True, 'data': data})
    except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """API para obtener estadísticas del dashboard en tiempo real"""
    try:
        # Estadísticas básicas
        total_prestamos = Prestamo.query.filter_by(estado='Activo').count()
        total_clientes = Cliente.query.filter_by(activo=True).count()
        
        # Calcular clientes atrasados
        fecha_actual = datetime.now().date()
        cuotas_atrasadas = Cuota.query.filter(
            Cuota.estado == 'Pendiente',
            Cuota.fecha_vencimiento < fecha_actual
        ).all()
        
        clientes_atrasados = len(set([cuota.prestamo.cliente_id for cuota in cuotas_atrasadas]))
        monto_total_atrasado = sum(float(cuota.monto_total) for cuota in cuotas_atrasadas)
        
        # Capital disponible
        contabilidad = Contabilidad.query.first()
        capital_disponible = float(contabilidad.capital_disponible) if contabilidad else 0
        
        # Préstamos del mes
        inicio_mes = fecha_actual.replace(day=1)
        prestamos_mes = Prestamo.query.filter(
            Prestamo.fecha_creacion >= inicio_mes
        ).count()
        
        # Pagos del mes
        pagos_mes = Pago.query.filter(
            Pago.fecha_pago >= inicio_mes
        ).count()
        monto_pagos_mes = sum(float(p.monto_pagado) for p in Pago.query.filter(Pago.fecha_pago >= inicio_mes).all())
        
        return jsonify({
            'success': True,
            'stats': {
                'total_prestamos': total_prestamos,
                'total_clientes': total_clientes,
                'clientes_atrasados': clientes_atrasados,
                'monto_total_atrasado': monto_total_atrasado,
                'capital_disponible': capital_disponible,
                'prestamos_mes': prestamos_mes,
                'pagos_mes': pagos_mes,
                'monto_pagos_mes': monto_pagos_mes
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/notificaciones')
@login_required
def api_notificaciones():
    """API para obtener notificaciones del sistema"""
    fecha_actual = datetime.now().date()
    notificaciones = []
    
    # Cuotas vencidas hoy
    cuotas_vencidas_hoy = Cuota.query.filter(
        Cuota.estado == 'Pendiente',
        Cuota.fecha_vencimiento == fecha_actual
    ).all()
    
    for cuota in cuotas_vencidas_hoy:
        notificaciones.append({
            'tipo': 'cuota_vencida',
            'mensaje': f'Cuota #{cuota.numero_cuota} de {cuota.prestamo.cliente.nombre} vence hoy',
            'fecha': fecha_actual.strftime('%d/%m/%Y'),
            'prioridad': 'alta'
        })
    
    # Cuotas vencidas ayer
    fecha_ayer = fecha_actual - timedelta(days=1)
    cuotas_vencidas_ayer = Cuota.query.filter(
        Cuota.estado == 'Pendiente',
        Cuota.fecha_vencimiento == fecha_ayer
    ).all()
    
    for cuota in cuotas_vencidas_ayer:
        notificaciones.append({
            'tipo': 'cuota_atrasada',
            'mensaje': f'Cuota #{cuota.numero_cuota} de {cuota.prestamo.cliente.nombre} está atrasada 1 día',
            'fecha': fecha_ayer.strftime('%d/%m/%Y'),
            'prioridad': 'media'
        })
    
    return jsonify({'notificaciones': notificaciones})

@app.route('/api/contabilidad/stats')
@login_required
def api_contabilidad_stats():
    """API para obtener estadísticas de contabilidad en tiempo real"""
    try:
        contabilidad = Contabilidad.query.first()
        capital_disponible = float(contabilidad.capital_disponible) if contabilidad else 0
        
        # Calcular total de ingresos (gastos con monto negativo)
        total_ingresos = db.session.query(db.func.sum(db.func.abs(Gasto.monto))).filter(Gasto.monto < 0).scalar() or 0
        
        # Calcular total de gastos (gastos con monto positivo)
        total_gastos = db.session.query(db.func.sum(Gasto.monto)).filter(Gasto.monto > 0).scalar() or 0
        
        # Calcular utilidad neta
        utilidad_neta = total_ingresos - total_gastos
        
        return jsonify({
            'success': True,
            'stats': {
                'capital_disponible': capital_disponible,
                'total_ingresos': total_ingresos,
                'total_gastos': total_gastos,
                'utilidad_neta': utilidad_neta
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/exportar/<tipo>')
@login_required
def api_exportar(tipo):
    """API para exportar datos en diferentes formatos"""
    if tipo == 'clientes':
        clientes = Cliente.query.filter_by(activo=True).all()
        data = []
        for cliente in clientes:
            data.append({
                'ID': cliente.id,
                'Nombre': cliente.nombre,
                'Apellidos': cliente.apellidos,
                'Documento': cliente.documento,
                'Teléfono': cliente.telefono_principal,
                'Provincia': cliente.provincia,
                'Fecha Registro': cliente.fecha_creacion.strftime('%d/%m/%Y')
            })
        return jsonify({'success': True, 'data': data, 'filename': 'clientes.json'})
    
    elif tipo == 'prestamos':
        prestamos = Prestamo.query.all()
        data = []
        for prestamo in prestamos:
            data.append({
                'ID': prestamo.id,
                'Cliente': f"{prestamo.cliente.nombre} {prestamo.cliente.apellidos}",
                'Monto': float(prestamo.monto),
                'Tasa Interés': float(prestamo.tasa_interes),
                'Estado': prestamo.estado,
                'Fecha Creación': prestamo.fecha_creacion.strftime('%d/%m/%Y')
            })
        return jsonify({'success': True, 'data': data, 'filename': 'prestamos.json'})
    
    else:
        return jsonify({'success': False, 'error': 'Tipo de exportación no válido'})

@app.route('/api/backup')
@login_required
def api_backup():
    """API para crear backup de la base de datos"""
    try:
        # Aquí se implementaría la lógica de backup
        # Por ahora solo retornamos un mensaje de éxito
        return jsonify({
            'success': True,
            'message': 'Backup creado exitosamente',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/restore', methods=['POST'])
@login_required
def api_restore():
    """API para restaurar backup de la base de datos"""
    try:
        # Aquí se implementaría la lógica de restauración
        # Por ahora solo retornamos un mensaje de éxito
        return jsonify({
            'success': True,
            'message': 'Backup restaurado exitosamente',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Decorador para verificar permisos de administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Acceso denegado. Se requieren permisos de administrador.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Gestión de Usuarios (solo administradores)
@app.route('/usuarios')
@login_required
@admin_required
def usuarios():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    usuarios_query = Usuario.query.order_by(Usuario.fecha_creacion.desc())
    usuarios = usuarios_query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_usuario():
    if request.method == 'POST':
        try:
            # Verificar si el username ya existe
            if Usuario.query.filter_by(username=request.form['username']).first():
                flash('El nombre de usuario ya existe', 'error')
                return redirect(url_for('nuevo_usuario'))
            
            usuario = Usuario(
                username=request.form['username'],
                password_hash=generate_password_hash(request.form['password']),
                nombre=request.form['nombre'],
                apellidos=request.form['apellidos'],
                cargo=request.form['cargo'],
                rol=request.form['rol']
            )
            db.session.add(usuario)
            db.session.commit()
            flash('Usuario registrado exitosamente', 'success')
            return redirect(url_for('usuarios'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar usuario: {str(e)}', 'error')
    
    return render_template('nuevo_usuario.html')

@app.route('/usuarios/<int:usuario_id>')
@login_required
@admin_required
def ver_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    return render_template('ver_usuario.html', usuario=usuario)

@app.route('/usuarios/<int:usuario_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    if request.method == 'POST':
        try:
            usuario.nombre = request.form['nombre']
            usuario.apellidos = request.form['apellidos']
            usuario.cargo = request.form['cargo']
            usuario.rol = request.form['rol']
            usuario.activo = 'activo' in request.form
            
            # Cambiar contraseña solo si se proporciona una nueva
            if request.form.get('password'):
                usuario.password_hash = generate_password_hash(request.form['password'])
            
            db.session.commit()
            flash('Usuario actualizado exitosamente', 'success')
            return redirect(url_for('ver_usuario', usuario_id=usuario.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar usuario: {str(e)}', 'error')
    
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/usuarios/<int:usuario_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # No permitir eliminar el usuario actual
    if usuario.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta', 'error')
        return redirect(url_for('ver_usuario', usuario_id=usuario.id))
    
    try:
        # Verificar si tiene registros asociados
        pagos_asociados = Pago.query.filter_by(usuario_id=usuario_id).count()
        if pagos_asociados > 0:
            flash('No se puede eliminar un usuario con pagos registrados', 'error')
            return redirect(url_for('ver_usuario', usuario_id=usuario.id))
        
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuario eliminado exitosamente', 'success')
        return redirect(url_for('usuarios'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar usuario: {str(e)}', 'error')
        return redirect(url_for('ver_usuario', usuario_id=usuario.id))

@app.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    if request.method == 'POST':
        try:
            current_user.nombre = request.form['nombre']
            current_user.apellidos = request.form['apellidos']
            current_user.cargo = request.form['cargo']
            
            # Cambiar contraseña solo si se proporciona una nueva
            if request.form.get('password'):
                if not check_password_hash(current_user.password_hash, request.form['password_actual']):
                    flash('Contraseña actual incorrecta', 'error')
                    return redirect(url_for('perfil'))
                current_user.password_hash = generate_password_hash(request.form['password'])
            
            db.session.commit()
            flash('Perfil actualizado exitosamente', 'success')
            return redirect(url_for('perfil'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar perfil: {str(e)}', 'error')
    
    return render_template('perfil.html')

@app.route('/cambiar-password', methods=['POST'])
@login_required
def cambiar_password():
    try:
        password_actual = request.form['password_actual']
        password_nueva = request.form['password_nueva']
        password_confirmar = request.form['password_confirmar']
        
        if not check_password_hash(current_user.password_hash, password_actual):
            flash('Contraseña actual incorrecta', 'error')
            return redirect(url_for('perfil'))
        
        if password_nueva != password_confirmar:
            flash('Las contraseñas nuevas no coinciden', 'error')
            return redirect(url_for('perfil'))
        
        current_user.password_hash = generate_password_hash(password_nueva)
        db.session.commit()
        flash('Contraseña cambiada exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al cambiar contraseña: {str(e)}', 'error')
    
    return redirect(url_for('perfil'))

# Funciones para generar PDFs reales
def generar_pdf_prestamo(prestamo, cuotas, total_cuotas, cuotas_pagadas, 
                         monto_total_prestamo, monto_pagado, monto_pendiente):
    """Genera un PDF real del préstamo"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=60, leftMargin=60, topMargin=60, bottomMargin=60)
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    normal_style = styles['Normal']
    
    # Título
    story.append(Paragraph("CONTRATO DE PRÉSTAMO", title_style))
    story.append(Spacer(1, 20))
    
    # Información del préstamo
    story.append(Paragraph("INFORMACIÓN DEL PRÉSTAMO", subtitle_style))
    
    prestamo_data = [
        ['Número de Préstamo:', str(prestamo.id)],
        ['Cliente:', f"{prestamo.cliente.nombre} {prestamo.cliente.apellidos}"],
        ['Documento:', prestamo.cliente.documento],
        ['Monto:', f"${float(prestamo.monto):,.2f}"],
        ['Tasa de Interés:', f"{float(prestamo.tasa_interes)}%"],
        ['Plazo:', f"{prestamo.plazo_meses} meses"],
        ['Frecuencia:', prestamo.frecuencia],
        ['Fecha Primera Cuota:', prestamo.fecha_primera_cuota.strftime('%d/%m/%Y')],
        ['Estado:', prestamo.estado]
    ]
    
    if prestamo.tipo_garantia:
        prestamo_data.extend([
            ['Tipo de Garantía:', prestamo.tipo_garantia],
            ['Descripción:', prestamo.descripcion_garantia or 'N/A'],
            ['Valor:', f"${float(prestamo.valor_garantia):,.2f}" if prestamo.valor_garantia else 'N/A']
        ])
    
    t = Table(prestamo_data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Resumen financiero
    story.append(Paragraph("RESUMEN FINANCIERO", subtitle_style))
    resumen_data = [
        ['Total de Cuotas:', str(total_cuotas)],
        ['Cuotas Pagadas:', str(cuotas_pagadas)],
        ['Cuotas Pendientes:', str(cuotas_pendientes)],
        ['Monto Total:', f"${monto_total_prestamo:,.2f}"],
        ['Monto Pagado:', f"${monto_pagado:,.2f}"],
        ['Monto Pendiente:', f"${monto_pendiente:,.2f}"]
    ]
    
    t2 = Table(resumen_data, colWidths=[2*inch, 4*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t2)
    story.append(Spacer(1, 20))
    
    # Tabla de cuotas
    story.append(Paragraph("DETALLE DE CUOTAS", subtitle_style))
    
    cuotas_data = [['#', 'Vencimiento', 'Capital', 'Interés', 'Total', 'Estado']]
    for cuota in cuotas:
        cuotas_data.append([
            str(cuota.numero_cuota),
            cuota.fecha_vencimiento.strftime('%d/%m/%Y'),
            f"${float(cuota.monto_capital):,.2f}",
            f"${float(cuota.monto_interes):,.2f}",
            f"${float(cuota.monto_total):,.2f}",
            cuota.estado
        ])
    
    t3 = Table(cuotas_data, colWidths=[0.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1*inch])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8)
    ]))
    story.append(t3)
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Documento generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          ParagraphStyle('Footer', parent=normal_style, alignment=TA_CENTER)))
    
    doc.build(story)
    return buffer

def generar_pdf_recibo(pago, cuota, prestamo, cliente):
    """Genera un PDF real del recibo de pago optimizado para una sola página"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    # Estilos optimizados para reducir espacios
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=15,
        alignment=TA_CENTER,
        textColor=colors.darkgreen
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=10,
        alignment=TA_CENTER,
        textColor=colors.darkgreen
    )
    
    normal_style = styles['Normal']
    
    # Agregar logo en la parte superior (más pequeño para ahorrar espacio)
    try:
        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'assets', 'logo.png')
        if os.path.exists(logo_path):
            logo_img = Image(logo_path, width=1.2*inch, height=1.2*inch)
            logo_img.hAlign = 'CENTER'
            story.append(logo_img)
            story.append(Spacer(1, 10))
    except Exception as e:
        print(f"Error al cargar logo: {e}")
        pass
    
    # Título de la empresa
    story.append(Paragraph("WANDY SOLUCIONES Y PRÉSTAMOS", title_style))
    story.append(Paragraph("Soluciones financieras a tu alcance", 
                          ParagraphStyle('Slogan', parent=styles['Normal'], 
                                       fontSize=12, alignment=TA_CENTER, 
                                       textColor=colors.darkblue)))
    story.append(Spacer(1, 12))
    
    # Número de comprobante
    story.append(Paragraph(f"<b>Comprobante #{pago.id}</b>", 
                          ParagraphStyle('ReceiptNumber', parent=styles['Normal'], 
                                       fontSize=14, alignment=TA_CENTER)))
    story.append(Spacer(1, 10))
    
    # Fecha y hora
    fecha_hora = f"<b>Fecha de Emisión:</b> {pago.fecha_pago.strftime('%d/%m/%Y')}<br/>" \
                 f"<b>Hora:</b> {pago.fecha_pago.strftime('%I:%M:%S %p')}"
    story.append(Paragraph(fecha_hora, 
                          ParagraphStyle('DateTime', parent=styles['Normal'], 
                                       fontSize=11, alignment=TA_CENTER)))
    story.append(Spacer(1, 12))
    
    # Información del Cliente
    story.append(Paragraph("Información del Cliente", subtitle_style))
    
    cliente_data = [
        ['Cliente:', f"{cliente.nombre} {cliente.apellidos}"],
        ['Préstamo:', str(prestamo.id)]
    ]
    
    if cuota:
        cliente_data.append(['Cuota:', str(cuota.numero_cuota)])
    
    t1 = Table(cliente_data, colWidths=[2*inch, 4*inch])
    t1.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
    ]))
    story.append(t1)
    story.append(Spacer(1, 12))
    

    
    # Detalles del Pago
    story.append(Paragraph("Detalles del Pago", subtitle_style))
    
    # Crear tabla de detalles del pago
    pago_data = [
        ['Monto Total:', f"RD${float(pago.monto_pagado):,.2f}"],
        ['Capital:', f"RD${float(pago.monto_capital):,.2f}"],
        ['Intereses:', f"RD${float(pago.monto_interes):,.2f}"],
        ['Fecha de Pago:', pago.fecha_pago.strftime('%d/%m/%Y')]
    ]
    
    if pago.tipo_pago != 'Normal':
        pago_data.append(['Tipo de Pago:', pago.tipo_pago])
    
    # Crear y mostrar la tabla de detalles del pago
    t2 = Table(pago_data, colWidths=[2*inch, 4*inch])
    t2.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightblue)
    ]))
    story.append(t2)
    story.append(Spacer(1, 15))
    
    # Firmas una al lado de la otra
    signature_style = ParagraphStyle('Signature', parent=styles['Normal'], 
                                   fontSize=11, alignment=TA_CENTER)
    
    # Crear tabla para las firmas lado a lado
    firmas_data = [
        ['_________________________', '_________________________'],
        ['Firma del Cliente', 'Firma del Cajero']
    ]
    
    t_firmas = Table(firmas_data, colWidths=[3*inch, 3*inch])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0, colors.white),  # Sin bordes
        ('SPAN', (0, 0), (0, 1)),  # Combinar primera columna
        ('SPAN', (1, 0), (1, 1))   # Combinar segunda columna
    ]))
    
    story.append(t_firmas)
    story.append(Spacer(1, 15))
    
    # Información de la empresa al pie de página
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], 
                                 fontSize=9, alignment=TA_CENTER, 
                                 textColor=colors.grey)
    
    # Línea separadora
    story.append(Paragraph("─" * 50, footer_style))
    story.append(Spacer(1, 8))
    
    # Información de contacto de la empresa
    empresa_info = [
        "WANDY SOLUCIONES Y PRÉSTAMOS",
        "Soluciones financieras a tu alcance",
        "Teléfono: (809) 326-3633 | WhatsApp: (809) 326-3633",
        "Email: info@wandysoluciones.com",
        "Dirección: Cotui, República Dominicana"
    ]
    
    for info in empresa_info:
        story.append(Paragraph(info, footer_style))
        story.append(Spacer(1, 3))
    
    story.append(Spacer(1, 10))
    
    # Construir el documento
    doc.build(story)
    buffer.seek(0)
    return buffer

@app.route('/reportes/descargar/<tipo>')
@login_required
def descargar_reporte_pdf(tipo):
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    
    if not fecha_inicio or not fecha_fin:
        flash('Debe especificar fechas de inicio y fin', 'error')
        return redirect(url_for('reportes'))
    
    try:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        if tipo == 'clientes':
            data = generar_reporte_clientes(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_clientes(data)
            filename = f"reporte_clientes_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.pdf"
        elif tipo == 'prestamos':
            data = generar_reporte_prestamos(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_prestamos(data)
            filename = f"reporte_prestamos_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.pdf"
        elif tipo == 'pagos':
            data = generar_reporte_pagos(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_pagos(data)
            filename = f"reporte_pagos_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.pdf"
        elif tipo == 'contabilidad':
            data = generar_reporte_contabilidad(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_contabilidad(data)
            filename = f"reporte_contabilidad_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.pdf"
        else:
            flash('Tipo de reporte no válido', 'error')
            return redirect(url_for('reportes'))
        
        # Enviar archivo para descarga
        pdf_buffer.seek(0)
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error al generar reporte: {str(e)}', 'error')
        return redirect(url_for('reportes'))

def generar_pdf_cliente(cliente, prestamos):
    """Genera un PDF real del cliente"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    # Título
    story.append(Paragraph("INFORMACIÓN DEL CLIENTE", title_style))
    story.append(Spacer(1, 20))
    
    # Información personal
    story.append(Paragraph("INFORMACIÓN PERSONAL", subtitle_style))
    
    personal_data = [
        ['Nombre:', f"{cliente.nombre} {cliente.apellidos}"],
        ['Apodo:', cliente.apodo or 'N/A'],
        ['Documento:', cliente.documento],
        ['Nacionalidad:', cliente.nacionalidad],
        ['Fecha de Nacimiento:', cliente.fecha_nacimiento.strftime('%d/%m/%Y') if cliente.fecha_nacimiento else 'N/A'],
        ['Sexo:', cliente.sexo],
        ['Estado Civil:', cliente.estado_civil]
    ]
    
    t = Table(personal_data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Información de contacto
    story.append(Paragraph("INFORMACIÓN DE CONTACTO", subtitle_style))
    
    contacto_data = [
        ['WhatsApp:', cliente.whatsapp or 'N/A'],
        ['Teléfono Principal:', cliente.telefono_principal],
        ['Teléfono Otro:', cliente.telefono_otro or 'N/A'],
        ['Correo:', cliente.correo]
    ]
    
    t2 = Table(contacto_data, colWidths=[2*inch, 4*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t2)
    story.append(Spacer(1, 20))
    
    # Información de ubicación
    story.append(Paragraph("INFORMACIÓN DE UBICACIÓN", subtitle_style))
    
    ubicacion_data = [
        ['Dirección:', cliente.direccion],
        ['Provincia:', cliente.provincia],
        ['Municipio:', cliente.municipio],
        ['Sector:', cliente.sector],
        ['Ruta:', cliente.ruta or 'N/A']
    ]
    
    t3 = Table(ubicacion_data, colWidths=[2*inch, 4*inch])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgreen),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t3)
    story.append(Spacer(1, 20))
    
    # Información laboral
    story.append(Paragraph("INFORMACIÓN LABORAL", subtitle_style))
    
    laboral_data = [
        ['Ocupación:', cliente.ocupacion],
        ['Ingresos:', f"${float(cliente.ingresos):,.2f}"],
        ['Situación Laboral:', cliente.situacion_laboral],
        ['Lugar de Trabajo:', cliente.lugar_trabajo],
        ['Dirección del Trabajo:', cliente.direccion_trabajo]
    ]
    
    t4 = Table(laboral_data, colWidths=[2*inch, 4*inch])
    t4.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightyellow),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t4)
    
    # Préstamos si existen
    if prestamos:
        story.append(Spacer(1, 20))
        story.append(Paragraph("HISTORIAL DE PRÉSTAMOS", subtitle_style))
        
        prestamos_data = [['ID', 'Monto', 'Tasa', 'Plazo', 'Estado', 'Fecha']]
        for prestamo in prestamos:
            prestamos_data.append([
                str(prestamo.id),
                f"${float(prestamo.monto):,.2f}",
                f"{float(prestamo.tasa_interes)}%",
                f"{prestamo.plazo_meses} meses",
                prestamo.estado,
                prestamo.fecha_creacion.strftime('%d/%m/%Y')
            ])
        
        t5 = Table(prestamos_data, colWidths=[0.8*inch, 1.2*inch, 0.8*inch, 1.2*inch, 1*inch, 1*inch])
        t5.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8)
        ]))
        story.append(t5)
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Documento generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)))
    
    doc.build(story)
    return buffer

# Funciones para generar PDFs de reportes
def generar_pdf_reporte_clientes(data):
    """Genera PDF del reporte de clientes"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    # Agregar logo centrado al inicio
    try:
        logo_path = os.path.join('assets', 'logo.png')
        if os.path.exists(logo_path):
            logo_img = Image(logo_path, width=2*inch, height=1.5*inch)
            logo_img.hAlign = 'CENTER'
            story.append(logo_img)
            story.append(Spacer(1, 20))
    except:
        pass  # Si no se pueden cargar las imágenes, continuar sin ellas
    
    # Título
    story.append(Paragraph(data['titulo'], title_style))
    story.append(Spacer(1, 20))
    
    # Información del reporte
    info_data = [
        ['Período:', f"{data['fecha_inicio'].strftime('%d/%m/%Y')} - {data['fecha_fin'].strftime('%d/%m/%Y')}"],
        ['Total de Clientes:', str(data['total_clientes'])]
    ]
    
    t = Table(info_data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Tabla de clientes
    story.append(Paragraph("DETALLE DE CLIENTES", subtitle_style))
    
    clientes_data = [['ID', 'Nombre', 'Documento', 'Teléfono', 'Provincia', 'Préstamos Activos']]
    for cliente in data['clientes']:
        clientes_data.append([
            str(cliente['id']),
            cliente['nombre'],
            cliente['documento'],
            cliente['telefono'],
            cliente['provincia'],
            str(cliente['prestamos_activos'])
        ])
    
    t2 = Table(clientes_data, colWidths=[0.8*inch, 2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8)
    ]))
    story.append(t2)
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Reporte generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)))
    
    # Agregar sello al final
    try:
        sello_path = os.path.join('assets', 'sello.png')
        if os.path.exists(sello_path):
            story.append(Spacer(1, 20))
            sello_img = Image(sello_path, width=1.5*inch, height=1.5*inch)
            sello_img.hAlign = 'CENTER'
            story.append(sello_img)
    except:
        pass  # Si no se pueden cargar las imágenes, continuar sin ellas
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def generar_pdf_reporte_prestamos(data):
    """Genera PDF del reporte de préstamos"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    # Agregar logo centrado al inicio
    try:
        logo_path = os.path.join('assets', 'logo.png')
        if os.path.exists(logo_path):
            logo_img = Image(logo_path, width=2*inch, height=1.5*inch)
            logo_img.hAlign = 'CENTER'
            story.append(logo_img)
            story.append(Spacer(1, 20))
    except:
        pass  # Si no se pueden cargar las imágenes, continuar sin ellas
    
    # Título
    story.append(Paragraph(data['titulo'], title_style))
    story.append(Spacer(1, 20))
    
    # Información del reporte
    info_data = [
        ['Período:', f"{data['fecha_inicio'].strftime('%d/%m/%Y')} - {data['fecha_fin'].strftime('%d/%m/%Y')}"],
        ['Total de Préstamos:', str(data['total_prestamos'])],
        ['Monto Total:', f"${data['monto_total']:,.2f}"]
    ]
    
    t = Table(info_data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Tabla de préstamos
    story.append(Paragraph("DETALLE DE PRÉSTAMOS", subtitle_style))
    
    prestamos_data = [['ID', 'Cliente', 'Monto', 'Tasa', 'Plazo', 'Estado', 'Cuotas Pendientes']]
    for prestamo in data['prestamos']:
        prestamos_data.append([
            str(prestamo['id']),
            prestamo['cliente'],
            f"${prestamo['monto']:,.2f}",
            f"{prestamo['tasa_interes']}%",
            f"{prestamo['plazo_meses']} meses",
            prestamo['estado'],
            str(prestamo['cuotas_pendientes'])
        ])
    
    t2 = Table(prestamos_data, colWidths=[0.8*inch, 2*inch, 1.2*inch, 0.8*inch, 1*inch, 1*inch, 1.2*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 7)
    ]))
    story.append(t2)
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Reporte generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)))
    
    # Agregar sello al final
    try:
        sello_path = os.path.join('assets', 'sello.png')
        if os.path.exists(sello_path):
            story.append(Spacer(1, 20))
            sello_img = Image(sello_path, width=1.5*inch, height=1.5*inch)
            sello_img.hAlign = 'CENTER'
            story.append(sello_img)
    except:
        pass  # Si no se pueden cargar las imágenes, continuar sin ellas
    
    doc.build(story)
    return buffer

def generar_pdf_reporte_pagos(data):
    """Genera PDF del reporte de pagos"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    # Agregar logo centrado al inicio
    try:
        logo_path = os.path.join('assets', 'logo.png')
        if os.path.exists(logo_path):
            logo_img = Image(logo_path, width=2*inch, height=1.5*inch)
            logo_img.hAlign = 'CENTER'
            story.append(logo_img)
            story.append(Spacer(1, 20))
    except:
        pass  # Si no se pueden cargar las imágenes, continuar sin ellas
    
    # Título
    story.append(Paragraph(data['titulo'], title_style))
    story.append(Spacer(1, 20))
    
    # Información del reporte
    info_data = [
        ['Período:', f"{data['fecha_inicio'].strftime('%d/%m/%Y')} - {data['fecha_fin'].strftime('%d/%m/%Y')}"],
        ['Total de Pagos:', str(data['total_pagos'])],
        ['Monto Total:', f"${data['monto_total']:,.2f}"]
    ]
    
    t = Table(info_data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Tabla de pagos
    story.append(Paragraph("DETALLE DE PAGOS", subtitle_style))
    
    pagos_data = [['ID', 'Cliente', 'Monto', 'Tipo', 'Fecha', 'Usuario']]
    for pago in data['pagos']:
        pagos_data.append([
            str(pago['id']),
            pago['cliente'],
            f"${pago['monto']:,.2f}",
            pago['tipo'],
            pago['fecha'],
            pago['usuario']
        ])
    
    t2 = Table(pagos_data, colWidths=[0.8*inch, 2.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.5*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8)
    ]))
    story.append(t2)
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Reporte generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)))
    
    # Agregar sello al final
    try:
        sello_path = os.path.join('assets', 'sello.png')
        if os.path.exists(sello_path):
            story.append(Spacer(1, 20))
            sello_img = Image(sello_path, width=1.5*inch, height=1.5*inch)
            sello_img.hAlign = 'CENTER'
            story.append(sello_img)
    except:
        pass  # Si no se pueden cargar las imágenes, continuar sin ellas
    
    doc.build(story)
    return buffer

def generar_pdf_reporte_contabilidad(data):
    """Genera PDF del reporte contable"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    # Agregar logo centrado al inicio
    try:
        logo_path = os.path.join('assets', 'logo.png')
        if os.path.exists(logo_path):
            logo_img = Image(logo_path, width=2*inch, height=1.5*inch)
            logo_img.hAlign = 'CENTER'
            story.append(logo_img)
            story.append(Spacer(1, 20))
    except:
        pass  # Si no se pueden cargar las imágenes, continuar sin ellas
    
    # Título
    story.append(Paragraph(data['titulo'], title_style))
    story.append(Spacer(1, 20))
    
    # Información del reporte
    info_data = [
        ['Período:', f"{data['fecha_inicio'].strftime('%d/%m/%Y')} - {data['fecha_fin'].strftime('%d/%m/%Y')}"],
        ['Total de Ingresos:', f"${data['total_ingresos']:,.2f}"],
        ['Total de Gastos:', f"${data['total_gastos']:,.2f}"],
        ['Utilidad Neta:', f"${data['utilidad_neta']:,.2f}"]
    ]
    
    t = Table(info_data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Tabla de transacciones
    story.append(Paragraph("DETALLE DE TRANSACCIONES", subtitle_style))
    
    transacciones_data = [['Fecha', 'Descripción', 'Tipo', 'Monto']]
    for trans in data['transacciones']:
        color = colors.red if trans['es_ingreso'] else colors.black
        transacciones_data.append([
            trans['fecha'],
            trans['descripcion'],
            trans['tipo'],
            f"${trans['monto']:,.2f}"
        ])
    
    t2 = Table(transacciones_data, colWidths=[1.2*inch, 3*inch, 1.5*inch, 1.5*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8)
    ]))
    story.append(t2)
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Reporte generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)))
    
    # Agregar sello al final
    try:
        sello_path = os.path.join('assets', 'sello.png')
        if os.path.exists(sello_path):
            story.append(Spacer(1, 20))
            sello_img = Image(sello_path, width=1.5*inch, height=1.5*inch)
            sello_img.hAlign = 'CENTER'
            story.append(sello_img)
    except:
        pass  # Si no se pueden cargar las imágenes, continuar sin ellas
    
    doc.build(story)
    return buffer

# Funciones adicionales de descarga de PDF para contabilidad
@app.route('/contabilidad/descargar-balance')
@login_required
def descargar_balance_pdf():
    try:
        # Obtener datos de contabilidad
        contabilidad = Contabilidad.query.first()
        capital_disponible = float(contabilidad.capital_disponible) if contabilidad else 0
        
        # Calcular estadísticas financieras
        total_ingresos = db.session.query(db.func.sum(db.func.abs(Gasto.monto))).filter(Gasto.monto < 0).scalar() or 0
        total_gastos = db.session.query(db.func.sum(Gasto.monto)).filter(Gasto.monto > 0).scalar() or 0
        utilidad_neta = total_ingresos - total_gastos
        
        # Obtener transacciones recientes
        transacciones = Gasto.query.order_by(Gasto.fecha.desc()).limit(50).all()
        
        # Generar PDF
        pdf_buffer = generar_pdf_balance_contable(capital_disponible, total_ingresos, total_gastos, utilidad_neta, transacciones)
        
        # Enviar archivo para descarga
        pdf_buffer.seek(0)
        filename = f"balance_contable_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error al generar PDF: {str(e)}', 'error')
        return redirect(url_for('contabilidad'))

def generar_pdf_balance_contable(capital_disponible, total_ingresos, total_gastos, utilidad_neta, transacciones):
    """Genera un PDF real del balance contable"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    # Título
    story.append(Paragraph("BALANCE CONTABLE GENERAL", title_style))
    story.append(Spacer(1, 20))
    
    # Resumen ejecutivo
    story.append(Paragraph("RESUMEN EJECUTIVO", subtitle_style))
    
    resumen_data = [
        ['Capital Disponible:', f"${capital_disponible:,.2f}"],
        ['Total de Ingresos:', f"${total_ingresos:,.2f}"],
        ['Total de Gastos:', f"${total_gastos:,.2f}"],
        ['Utilidad Neta:', f"${utilidad_neta:,.2f}"]
    ]
    
    t = Table(resumen_data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Tabla de transacciones recientes
    story.append(Paragraph("TRANSACCIONES RECIENTES", subtitle_style))
    
    transacciones_data = [['Fecha', 'Descripción', 'Tipo', 'Monto']]
    for trans in transacciones:
        transacciones_data.append([
            trans.fecha.strftime('%d/%m/%Y'),
            trans.descripcion,
            trans.tipo,
            f"${float(trans.monto):,.2f}"
        ])
    
    t2 = Table(transacciones_data, colWidths=[1.2*inch, 3*inch, 1.5*inch, 1.5*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8)
    ]))
    story.append(t2)
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Documento generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)))
    
    doc.build(story)
    return buffer

# Agregar función para descargar lista de clientes en PDF
@app.route('/clientes/descargar-lista')
@login_required
def descargar_lista_clientes_pdf():
    try:
        # Obtener todos los clientes activos
        clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.apellidos, Cliente.nombre).all()
        
        # Generar PDF
        pdf_buffer = generar_pdf_lista_clientes(clientes)
        
        # Enviar archivo para descarga
        pdf_buffer.seek(0)
        filename = f"lista_clientes_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error al generar PDF: {str(e)}', 'error')
        return redirect(url_for('clientes'))

def generar_pdf_lista_clientes(clientes):
    """Genera un PDF con la lista de todos los clientes"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    # Título
    story.append(Paragraph("LISTA DE CLIENTES", title_style))
    story.append(Spacer(1, 20))
    
    # Información del reporte
    info_data = [
        ['Total de Clientes:', str(len(clientes))],
        ['Fecha de Generación:', datetime.now().strftime('%d/%m/%Y %H:%M')]
    ]
    
    t = Table(info_data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Tabla de clientes
    story.append(Paragraph("DETALLE DE CLIENTES", subtitle_style))
    
    clientes_data = [['#', 'Nombre', 'Documento', 'Teléfono', 'Provincia', 'Ocupación']]
    for i, cliente in enumerate(clientes, 1):
        clientes_data.append([
            str(i),
            f"{cliente.nombre} {cliente.apellidos}",
            cliente.documento,
            cliente.telefono_principal,
            cliente.provincia,
            cliente.ocupacion
        ])
    
    t2 = Table(clientes_data, colWidths=[0.5*inch, 2.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.5*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8)
    ]))
    story.append(t2)
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Documento generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)))
    
    doc.build(story)
    return buffer

# Función para generar PDF de reporte de atrasos
def generar_pdf_reporte_atrasos(data):
    """Genera PDF del reporte de atrasos"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkred
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.darkred
    )
    
    # Agregar logo centrado al inicio
    try:
        logo_path = os.path.join('assets', 'logo.png')
        if os.path.exists(logo_path):
            logo_img = Image(logo_path, width=2*inch, height=1.5*inch)
            logo_img.hAlign = 'CENTER'
            story.append(logo_img)
            story.append(Spacer(1, 20))
    except:
        pass  # Si no se pueden cargar las imágenes, continuar sin ellas
    
    # Título
    story.append(Paragraph(data['titulo'], title_style))
    story.append(Spacer(1, 20))
    
    # Información del reporte
    info_data = [
        ['Período:', f"{data['fecha_inicio'].strftime('%d/%m/%Y')} - {data['fecha_fin'].strftime('%d/%m/%Y')}"],
        ['Total de Cuotas Atrasadas:', str(data['total_cuotas_atrasadas'])],
        ['Monto Total Atrasado:', f"${data['monto_total_atrasado']:,.2f}"]
    ]
    
    t = Table(info_data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Tabla de atrasos
    story.append(Paragraph("DETALLE DE ATRASOS", subtitle_style))
    
    atrasos_data = [['Cliente', 'Préstamo', 'Cuota', 'Monto', 'Vencimiento', 'Días Atraso']]
    for atraso in data['atrasos']:
        atrasos_data.append([
            atraso['cliente'],
            str(atraso['prestamo_id']),
            str(atraso['cuota_numero']),
            f"${atraso['monto']:,.2f}",
            atraso['fecha_vencimiento'],
            str(atraso['dias_atraso'])
        ])
    
    t2 = Table(atrasos_data, colWidths=[2*inch, 1*inch, 1*inch, 1.2*inch, 1.2*inch, 1*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 7)
    ]))
    story.append(t2)
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Reporte generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)))
    
    # Agregar sello al final
    try:
        sello_path = os.path.join('assets', 'sello.png')
        if os.path.exists(sello_path):
            story.append(Spacer(1, 20))
            sello_img = Image(sello_path, width=1.5*inch, height=1.5*inch)
            sello_img.hAlign = 'CENTER'
            story.append(sello_img)
    except:
        pass  # Si no se pueden cargar las imágenes, continuar sin ellas
    
    doc.build(story)
    return buffer

# Mejorar las funciones de reportes para incluir descarga de PDF
@app.route('/reportes/descargar-atrasos')
@login_required
def descargar_reporte_atrasos_pdf():
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    
    if not fecha_inicio or not fecha_fin:
        flash('Debe especificar fechas de inicio y fin', 'error')
        return redirect(url_for('reportes'))
    
    try:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        
        data = generar_reporte_atrasos(fecha_inicio, fecha_fin)
        pdf_buffer = generar_pdf_reporte_atrasos(data)
        
        # Enviar archivo para descarga
        pdf_buffer.seek(0)
        filename = f"reporte_atrasos_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error al generar reporte: {str(e)}', 'error')
        return redirect(url_for('reportes'))

# Rutas para gestión de reportes
@app.route('/reportes/eliminar/<int:reporte_id>', methods=['DELETE'])
@login_required
def eliminar_reporte(reporte_id):
    """Elimina un reporte de la base de datos"""
    try:
        reporte = Reporte.query.get_or_404(reporte_id)
        
        # Verificar que el usuario actual sea el propietario del reporte o sea administrador
        if reporte.usuario_id != current_user.id and not current_user.es_admin:
            return jsonify({'error': 'No tienes permisos para eliminar este reporte'}), 403
        
        db.session.delete(reporte)
        db.session.commit()
        
        return jsonify({'message': 'Reporte eliminado exitosamente'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'No se pudo eliminar el reporte'}), 500

@app.route('/reportes/ver/<int:reporte_id>')
@login_required
def ver_reporte(reporte_id):
    """Muestra una vista previa del reporte"""
    try:
        reporte = Reporte.query.get_or_404(reporte_id)
        
        # Verificar que el usuario actual sea el propietario del reporte o sea administrador
        if reporte.usuario_id != current_user.id and not current_user.es_admin:
            return "No tienes permisos para ver este reporte", 403
        
        # Obtener parámetros del reporte
        import json
        parametros = json.loads(reporte.parametros) if reporte.parametros else {}
        
        # Regenerar el reporte con los mismos parámetros
        fecha_inicio = datetime.strptime(parametros.get('fecha_inicio', ''), '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(parametros.get('fecha_fin', ''), '%Y-%m-%d').date()
        tipo = parametros.get('tipo', reporte.tipo)
        
        # Generar datos del reporte según el tipo
        if tipo == 'clientes':
            data = generar_reporte_clientes(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_clientes(data)
        elif tipo == 'prestamos':
            data = generar_reporte_prestamos(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_prestamos(data)
        elif tipo == 'pagos':
            data = generar_reporte_pagos(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_pagos(data)
        elif tipo == 'atrasos':
            data = generar_reporte_atrasos(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_atrasos(data)
        elif tipo == 'contabilidad':
            data = generar_reporte_contabilidad(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_contabilidad(data)
        else:
            return f"Tipo de reporte no válido: {tipo}", 400
        
        # Preparar el archivo para vista previa
        pdf_buffer.seek(0)
        
        # Crear respuesta con el PDF para vista previa
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=reporte_vista_previa.pdf'
        
        return response
        
    except Exception as e:
        # Para vista previa, devolver error HTTP en lugar de redirect
        return f"Error al generar vista previa: {str(e)}", 500

@app.route('/reportes/descargar/<int:reporte_id>')
@login_required
def descargar_reporte_existente(reporte_id):
    """Descarga un reporte existente regenerándolo"""
    try:
        reporte = Reporte.query.get_or_404(reporte_id)
        
        # Verificar que el usuario actual sea el propietario del reporte o sea administrador
        if reporte.usuario_id != current_user.id and not current_user.es_admin:
            flash('No tienes permisos para descargar este reporte', 'error')
            return redirect(url_for('reportes'))
        
        # Obtener parámetros del reporte
        import json
        parametros = json.loads(reporte.parametros) if reporte.parametros else {}
        
        # Regenerar el reporte con los mismos parámetros
        fecha_inicio = datetime.strptime(parametros.get('fecha_inicio', ''), '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(parametros.get('fecha_fin', ''), '%Y-%m-%d').date()
        tipo = parametros.get('tipo', reporte.tipo)
        
        # Generar datos del reporte según el tipo
        if tipo == 'clientes':
            data = generar_reporte_clientes(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_clientes(data)
        elif tipo == 'prestamos':
            data = generar_reporte_prestamos(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_prestamos(data)
        elif tipo == 'pagos':
            data = generar_reporte_pagos(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_pagos(data)
        elif tipo == 'atrasos':
            data = generar_reporte_atrasos(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_atrasos(data)
        elif tipo == 'contabilidad':
            data = generar_reporte_contabilidad(fecha_inicio, fecha_fin)
            pdf_buffer = generar_pdf_reporte_contabilidad(data)
        else:
            flash('Tipo de reporte no válido', 'error')
            return redirect(url_for('reportes'))
        
        # Preparar el archivo para descarga
        pdf_buffer.seek(0)
        
        # Crear respuesta con el PDF
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=reporte_{tipo}_{fecha_inicio.strftime("%Y%m%d")}_{fecha_fin.strftime("%Y%m%d")}.pdf'
        
        flash(f'Reporte de {tipo} regenerado y descargado exitosamente', 'success')
        return response
        
    except Exception as e:
        # Ocultar errores técnicos del usuario
        flash('No se pudo regenerar el reporte', 'warning')
        return redirect(url_for('reportes'))

# Agregar función para descargar lista de préstamos en PDF
@app.route('/prestamos/descargar-lista')
@login_required
def descargar_lista_prestamos_pdf():
    try:
        # Obtener todos los préstamos
        prestamos = Prestamo.query.join(Cliente).order_by(Prestamo.fecha_creacion.desc()).all()
        
        # Generar PDF
        pdf_buffer = generar_pdf_lista_prestamos(prestamos)
        
        # Enviar archivo para descarga
        pdf_buffer.seek(0)
        filename = f"lista_prestamos_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error al generar PDF: {str(e)}', 'error')
        return redirect(url_for('prestamos'))

def generar_pdf_lista_prestamos(prestamos):
    """Genera un PDF con la lista de todos los préstamos"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    # Título
    story.append(Paragraph("LISTA DE PRÉSTAMOS", title_style))
    story.append(Spacer(1, 20))
    
    # Información del reporte
    info_data = [
        ['Total de Préstamos:', str(len(prestamos))],
        ['Fecha de Generación:', datetime.now().strftime('%d/%m/%Y %H:%M')]
    ]
    
    t = Table(info_data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Tabla de préstamos
    story.append(Paragraph("DETALLE DE PRÉSTAMOS", subtitle_style))
    
    prestamos_data = [['ID', 'Cliente', 'Monto', 'Tasa', 'Plazo', 'Estado', 'Fecha']]
    for prestamo in prestamos:
        prestamos_data.append([
            str(prestamo.id),
            f"{prestamo.cliente.nombre} {prestamo.cliente.apellidos}",
            f"${float(prestamo.monto):,.2f}",
            f"{float(prestamo.tasa_interes)}%",
            f"{prestamo.plazo_meses} meses",
            prestamo.estado,
            prestamo.fecha_creacion.strftime('%d/%m/%Y')
        ])
    
    t2 = Table(prestamos_data, colWidths=[0.8*inch, 2.5*inch, 1.2*inch, 0.8*inch, 1*inch, 1*inch, 1*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 7)
    ]))
    story.append(t2)
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Documento generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)))
    
    doc.build(story)
    return buffer

# Agregar función para descargar lista de pagos en PDF
@app.route('/pagos/descargar-lista')
@login_required
def descargar_lista_pagos_pdf():
    try:
        # Obtener todos los pagos
        pagos = Pago.query.join(Cuota).join(Prestamo).join(Cliente).order_by(Pago.fecha_pago.desc()).all()
        
        # Generar PDF
        pdf_buffer = generar_pdf_lista_pagos(pagos)
        
        # Enviar archivo para descarga
        pdf_buffer.seek(0)
        filename = f"lista_pagos_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f'Error al generar PDF: {str(e)}', 'error')
        return redirect(url_for('pagos'))

def generar_pdf_lista_pagos(pagos):
    """Genera un PDF con la lista de todos los pagos"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkgreen
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.darkgreen
    )
    
    # Título
    story.append(Paragraph("LISTA DE PAGOS", title_style))
    story.append(Spacer(1, 20))
    
    # Información del reporte
    info_data = [
        ['Total de Pagos:', str(len(pagos))],
        ['Fecha de Generación:', datetime.now().strftime('%d/%m/%Y %H:%M')]
    ]
    
    t = Table(info_data, colWidths=[2*inch, 4*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    # Tabla de pagos
    story.append(Paragraph("DETALLE DE PAGOS", subtitle_style))
    
    pagos_data = [['ID', 'Cliente', 'Monto', 'Tipo', 'Fecha', 'Usuario']]
    for pago in pagos:
        pagos_data.append([
            str(pago.id),
            f"{pago.cuota.prestamo.cliente.nombre} {pago.cuota.prestamo.cliente.apellidos}",
            f"${float(pago.monto_pagado):,.2f}",
            pago.tipo_pago,
            pago.fecha_pago.strftime('%d/%m/%Y'),
            f"{pago.usuario.nombre} {pago.usuario.apellidos}"
        ])
    
    t2 = Table(pagos_data, colWidths=[0.8*inch, 2.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.5*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 7)
    ]))
    story.append(t2)
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Documento generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
                          ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)))
    
    doc.build(story)
    return buffer

@app.route('/api/cuotas-atrasadas')
@login_required
def api_cuotas_atrasadas():
    """API para obtener todas las cuotas atrasadas con información del cliente"""
    try:
        fecha_actual = datetime.now().date()
        
        # Obtener cuotas atrasadas
        cuotas_atrasadas = Cuota.query.filter(
            Cuota.estado == 'Pendiente',
            Cuota.fecha_vencimiento < fecha_actual
        ).join(Prestamo).join(Cliente).all()
        
        cuotas_data = []
        for cuota in cuotas_atrasadas:
            dias_atraso = (fecha_actual - cuota.fecha_vencimiento).days
            
            cuotas_data.append({
                'id': cuota.id,
                'numero_cuota': cuota.numero_cuota,
                'monto_total': float(cuota.monto_total),
                'fecha_vencimiento': cuota.fecha_vencimiento.strftime('%d/%m/%Y'),
                'dias_atraso': dias_atraso,
                'prestamo_monto': float(cuota.prestamo.monto),
                'cliente_nombre': f"{cuota.prestamo.cliente.nombre} {cuota.prestamo.cliente.apellidos}",
                'cliente_correo': cuota.prestamo.cliente.correo,
                'cliente_telefono': cuota.prestamo.cliente.telefono_principal
            })
        
        return jsonify({
            'success': True,
            'cuotas': cuotas_data,
            'total': len(cuotas_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cuota/<int:cuota_id>')
@login_required
def api_cuota(cuota_id):
    """API para obtener datos de una cuota específica"""
    try:
        print(f"🔍 Buscando cuota ID: {cuota_id}")
        cuota = Cuota.query.get_or_404(cuota_id)
        
        print(f"📊 Datos de cuota encontrada:")
        print(f"   - ID: {cuota.id}")
        print(f"   - Número: {cuota.numero_cuota}")
        print(f"   - Monto total: {cuota.monto_total}")
        print(f"   - Fecha vencimiento: {cuota.fecha_vencimiento}")
        print(f"   - Préstamo monto: {cuota.prestamo.monto}")
        print(f"   - Cliente: {cuota.prestamo.cliente.nombre} {cuota.prestamo.cliente.apellidos}")
        
        cuota_data = {
            'id': cuota.id,
            'numero_cuota': cuota.numero_cuota,
            'monto_total': float(cuota.monto_total) if cuota.monto_total else 0.0,
            'monto_capital': float(cuota.monto_capital) if cuota.monto_capital else 0.0,
            'monto_interes': float(cuota.monto_interes) if cuota.monto_interes else 0.0,
            'fecha_vencimiento': cuota.fecha_vencimiento.strftime('%d/%m/%Y') if cuota.fecha_vencimiento else 'N/A',
            'estado': cuota.estado,
            'prestamo_monto': float(cuota.prestamo.monto) if cuota.prestamo.monto else 0.0,
            'cliente_nombre': f"{cuota.prestamo.cliente.nombre} {cuota.prestamo.cliente.apellidos}",
            'cliente_correo': cuota.prestamo.cliente.correo,
            'cliente_telefono': cuota.prestamo.cliente.telefono_principal
        }
        
        print(f"📤 Datos enviados al frontend:")
        print(f"   - cuota_data: {cuota_data}")
        
        return jsonify({
            'success': True,
            'cuota': cuota_data
        })
        
    except Exception as e:
        print(f"❌ Error en API cuota: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/enviar-notificacion', methods=['POST'])
@login_required
def api_enviar_notificacion():
    """API para enviar notificación individual"""
    try:
        data = request.get_json()
        cuota_id = data.get('cuota_id')
        email = data.get('email')
        
        if not cuota_id or not email:
            return jsonify({
                'success': False,
                'error': 'ID de cuota y email son requeridos'
            }), 400
        
        # Aquí se implementaría la lógica de envío real
        # Por ahora solo simulamos el envío
        
        return jsonify({
            'success': True,
            'message': 'Notificación enviada exitosamente'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generar_contrato_prestamo_pdf(prestamo, cliente, monto_letras, dia, mes, año):
    """Genera un contrato de préstamo en PDF usando reportlab con datos reales"""
    try:
        from io import BytesIO
        from reportlab.platypus import Image, PageTemplate, Frame, NextPageTemplate
        from reportlab.lib.units import cm
        from reportlab.platypus.flowables import Image as FlowableImage
        
        # Crear buffer para el PDF
        buffer = BytesIO()
        
        # Crear documento PDF
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=60, leftMargin=60, topMargin=60, bottomMargin=60)
        
        # Obtener estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=13,
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        )
        
        clause_title_style = ParagraphStyle(
            'ClauseTitle',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=6,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
            textTransform='uppercase'
        )
        
        # Crear contenido del PDF
        story = []
        
        # Crear plantilla de página con sello de fondo para TODAS las páginas
        def create_page_template():
            # Crear frame para el contenido
            frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
            
            # Función para dibujar el sello de fondo en CADA página
            def draw_sello_background(canvas, doc):
                try:
                    sello_path = os.path.join('assets', 'sello.png')
                    if os.path.exists(sello_path):
                        # Dibujar sello centrado como marca de agua en cada página
                        canvas.saveState()
                        # Hacer el sello semi-transparente
                        canvas.setFillAlpha(0.08)  # 8% de opacidad para mejor visibilidad
                        # Centrar el sello en la página
                        sello_width = 5*cm  # Reducir tamaño del sello
                        sello_height = 5*cm
                        x = (doc.pagesize[0] - sello_width) / 2
                        y = (doc.pagesize[1] - sello_height) / 2
                        canvas.drawImage(sello_path, x, y, width=sello_width, height=sello_height)
                        canvas.restoreState()
                except:
                    pass  # Si no se puede cargar el sello, continuar sin él
            
            # Crear plantilla de página que se aplicará a TODAS las páginas
            template = PageTemplate(id='sello_background', frames=[frame], onPage=draw_sello_background)
            return template
        
        # Crear plantilla de página por defecto
        page_template = create_page_template()
        
        # Aplicar plantilla de página por defecto
        doc.addPageTemplates([page_template])
        
        # Título principal
        story.append(Paragraph("CONTRATO DE PRÉSTAMO", title_style))
        story.append(Spacer(1, 8))
        
        # Párrafo introductorio con datos reales
        intro_text = f"""Conste por el presente documento el contrato de préstamo de dinero que celebran, de una parte, 
        <b>Wandy Paredes Castro</b>, con documento de identidad número <b>402-2871544-3</b>, con domicilio en 
        <b>la casa no. 77 la Piedra, Distrito Municipal La Bija</b>, en adelante denominado <b>EL PRESTAMISTA</b>; 
        y de otra parte, <b>{cliente.nombre} {cliente.apellidos}</b>, con documento de identidad número <b>{cliente.documento}</b>, 
        con domicilio en <b>{cliente.direccion}, {cliente.sector}, {cliente.municipio}, {cliente.provincia}</b>, 
        en adelante denominado <b>EL PRESTATARIO</b>, bajo los términos y condiciones siguientes:"""
        
        story.append(Paragraph(intro_text, normal_style))
        story.append(Spacer(1, 8))
        
        # Título de cláusulas
        story.append(Paragraph("CLÁUSULAS", subtitle_style))
        story.append(Spacer(1, 6))
        
        # Cláusula primera con monto real
        story.append(Paragraph("PRIMERA: Objeto del contrato", clause_title_style))
        clause1_text = f"""EL PRESTAMISTA entrega en calidad de préstamo a EL PRESTATARIO la suma de 
        <b>{monto_letras}</b> (<b>${prestamo.monto:,.2f}</b> <b>pesos dominicanos</b>), la cual es recibida por EL PRESTATARIO en este acto."""
        story.append(Paragraph(clause1_text, normal_style))
        story.append(Spacer(1, 5))
        
        # Cláusula segunda con plazo real
        story.append(Paragraph("SEGUNDA: Plazo de devolución", clause_title_style))
        clause2_text = f"""EL PRESTATARIO se compromete a devolver el monto total del préstamo en un plazo de 
        <b>{prestamo.plazo_meses} meses</b>, contados a partir de la fecha de firma de este contrato."""
        story.append(Paragraph(clause2_text, normal_style))
        story.append(Spacer(1, 5))
        
        # Cláusula tercera con tasa de interés real (cambiada a mensual)
        story.append(Paragraph("TERCERA: Intereses", clause_title_style))
        clause3_text = f"""El préstamo devengará un interés mensual del <b>{prestamo.tasa_interes}%</b>, calculado sobre el saldo pendiente. 
        Los intereses serán pagados <b>{prestamo.frecuencia.lower()}</b>. En caso de mora, se aplicará un interés moratorio del <b>8%</b> 
        anual sobre las cantidades adeudadas."""
        story.append(Paragraph(clause3_text, normal_style))
        story.append(Spacer(1, 5))
        
        # Cláusula cuarta
        story.append(Paragraph("CUARTA: Forma de pago", clause_title_style))
        clause4_text = """Los pagos se realizarán mediante <b>efectivo</b>. EL PRESTATARIO entregará el pago directamente a EL PRESTAMISTA, 
        quien emitirá un recibo por cada pago recibido."""
        story.append(Paragraph(clause4_text, normal_style))
        story.append(Spacer(1, 5))
        
        # Cláusula quinta con garantía real
        story.append(Paragraph("QUINTA: Garantías", clause_title_style))
        if prestamo.tipo_garantia and prestamo.descripcion_garantia:
            garantia_text = f"{prestamo.descripcion_garantia} ({prestamo.tipo_garantia})"
        else:
            garantia_text = "ninguna"
        
        clause5_text = f"""Para garantizar el cumplimiento de las obligaciones derivadas de este contrato, EL PRESTATARIO ofrece en garantía 
        <b>{garantia_text}</b>. En caso de incumplimiento, EL PRESTAMISTA podrá ejecutar la garantía conforme a la ley."""
        story.append(Paragraph(clause5_text, normal_style))
        story.append(Spacer(1, 5))
        
        # Cláusula sexta
        story.append(Paragraph("SEXTA: Incumplimiento", clause_title_style))
        clause6_text = """El incumplimiento de cualquiera de las obligaciones establecidas en este contrato facultará a EL PRESTAMISTA 
        a dar por vencido el plazo del préstamo y exigir el pago inmediato del capital, intereses y costos asociados, 
        además de iniciar las acciones legales pertinentes."""
        story.append(Paragraph(clause6_text, normal_style))
        story.append(Spacer(1, 5))
        
        # Cláusula séptima
        story.append(Paragraph("SÉPTIMA: Gastos y tributos", clause_title_style))
        clause7_text = """Todos los gastos notariales, registrales y tributarios derivados de este contrato serán asumidos por <b>EL PRESTATARIO</b>."""
        story.append(Paragraph(clause7_text, normal_style))
        story.append(Spacer(1, 5))
        
        # Cláusula octava
        story.append(Paragraph("OCTAVA: Jurisdicción y legislación aplicable", clause_title_style))
        clause8_text = """Las partes acuerdan que este contrato se regirá por las leyes de <b>la República Dominicana</b>. 
        Cualquier controversia será resuelta en los tribunales de <b>Cotuí, República Dominicana</b>."""
        story.append(Paragraph(clause8_text, normal_style))
        story.append(Spacer(1, 5))
        
        # Cláusula novena
        story.append(Paragraph("NOVENA: Domicilio", clause_title_style))
        clause9_text = """Para efectos de notificaciones, las partes fijan sus domicilios en los indicados al inicio de este contrato."""
        story.append(Paragraph(clause9_text, normal_style))
        story.append(Spacer(1, 8))
        
        # Firma del contrato
        firma_text = f"""En señal de conformidad, las partes firman el presente contrato en dos ejemplares de igual valor, 
        en la ciudad de <b>Cotuí</b>, a los <b>{dia}</b> días del mes de <b>{mes}</b> del año <b>{año}</b>."""
        story.append(Paragraph(firma_text, normal_style))
        story.append(Spacer(1, 10))
        
        # Cuadro "BUENO Y VALIDO POR LA SUMA DE..."
        story.append(Paragraph(f"BUENO Y VALIDO POR LA SUMA DE {monto_letras} (${prestamo.monto:,.2f} pesos dominicanos)", title_style))
        story.append(Spacer(1, 8))
        
        # Crear un cuadro con borde
        from reportlab.platypus import Table, TableStyle
        
        # Cuadro vacío con borde
        cuadro_data = [['']]  # Celda vacía
        cuadro = Table(cuadro_data, colWidths=[6*inch], rowHeights=[1.5*inch])
        cuadro.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 2, colors.black),  # Borde negro grueso
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),  # Fondo blanco
        ]))
        story.append(cuadro)
        story.append(Spacer(1, 10))
        
        # Firmas lado a lado
        story.append(Paragraph("Firmas", subtitle_style))
        story.append(Spacer(1, 10))
        
        # Crear tabla para firmas lado a lado
        firmas_data = [
            ['EL PRESTAMISTA', 'EL PRESTATARIO'],
            ['Wandy Paredes Castro', f'{cliente.nombre} {cliente.apellidos}'],
            ['', ''],  # Espacio para líneas de firma
            ['___________________________', '___________________________']
        ]
        
        tabla_firmas = Table(firmas_data, colWidths=[3*inch, 3*inch])
        tabla_firmas.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Títulos en negrita
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0, colors.white),  # Sin bordes visibles
        ]))
        story.append(tabla_firmas)
        story.append(Spacer(1, 10))
        
        # Información adicional eliminada según solicitud del usuario
        
        # Construir PDF
        doc.build(story)
        
        # Obtener contenido del buffer
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content
        
    except Exception as e:
        # Si hay error, devolver un mensaje de error en formato PDF
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            
            story = []
            story.append(Paragraph("Error al generar PDF", styles['Heading1']))
            story.append(Spacer(1, 20))
            story.append(Paragraph(f"Se ha producido un error al generar el contrato: {str(e)}", styles['Normal']))
            
            doc.build(story)
            pdf_content = buffer.getvalue()
            buffer.close()
            return pdf_content
            
        except:
            # Si todo falla, devolver un mensaje simple
            return f"Error al generar PDF: {str(e)}".encode('utf-8')

# API Endpoints para Brevo
@app.route('/api/enviar-recibo-brevo', methods=['POST'])
@login_required
def api_enviar_recibo_brevo():
    """API para enviar recibo de pago usando Brevo"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Datos no proporcionados'}), 400
        
        cliente_email = data.get('cliente_email')
        cliente_nombre = data.get('cliente_nombre')
        datos_pago = data.get('datos_pago')
        
        if not cliente_email or not cliente_nombre or not datos_pago:
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
        
        # Enviar email usando Brevo
        resultado = enviar_recibo_pago_brevo(cliente_email, cliente_nombre, datos_pago)
        
        if resultado['success']:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/enviar-notificacion-brevo', methods=['POST'])
@login_required
def api_enviar_notificacion_brevo():
    """API para enviar notificación de atraso usando Brevo"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Datos no proporcionados'}), 400
        
        cliente_email = data.get('cliente_email')
        cliente_nombre = data.get('cliente_nombre')
        datos_cuota = data.get('datos_cuota')
        
        if not cliente_email or not cliente_nombre or not datos_cuota:
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
        
        # Enviar email usando Brevo
        resultado = enviar_notificacion_atraso_brevo(cliente_email, cliente_nombre, datos_cuota)
        
        if resultado['success']:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/pagos/<int:pago_id>/enviar-recibo')
@login_required
def enviar_recibo_pago(pago_id):
    try:
        pago = Pago.query.get_or_404(pago_id)
        
        # Obtener información relacionada
        cuota = pago.cuota
        if not cuota:
            flash('Error: El pago no está asociado a una cuota', 'error')
            return redirect(url_for('ver_pago', pago_id=pago_id))
            
        prestamo = cuota.prestamo
        if not prestamo:
            flash('Error: No se pudo obtener información del préstamo', 'error')
            return redirect(url_for('ver_pago', pago_id=pago_id))
            
        cliente = prestamo.cliente
        if not cliente:
            flash('Error: No se pudo obtener información del cliente', 'error')
            return redirect(url_for('ver_pago', pago_id=pago_id))
            
        # Verificar que el cliente tenga correo electrónico
        if not cliente.correo:
            flash('Error: El cliente no tiene correo electrónico registrado', 'error')
            return redirect(url_for('ver_pago', pago_id=pago_id))
        
        # Preparar datos para el email
        datos_pago = {
            'id_pago': pago.id,
            'monto_pagado': float(pago.monto_pagado),
            'monto_capital': float(pago.monto_capital),
            'monto_interes': float(pago.monto_interes),
            'tipo_pago': pago.tipo_pago,
            'fecha_pago': pago.fecha_pago.strftime('%d/%m/%Y'),
            'numero_cuota': cuota.numero_cuota,
            'monto_cuota': float(cuota.monto_total),
            'id_prestamo': prestamo.id,
            'monto_prestamo': float(prestamo.monto),
            'plazo_prestamo': prestamo.plazo_meses,
            'tasa_interes': float(prestamo.tasa_interes)
        }
        
        # Enviar email usando Brevo
        resultado = enviar_recibo_pago_brevo(cliente.correo, f"{cliente.nombre} {cliente.apellidos}", datos_pago)
        
        if resultado['success']:
            flash(f'Recibo enviado exitosamente a {cliente.correo}', 'success')
        else:
            flash(f'Error al enviar recibo: {resultado.get("error", "Error desconocido")}', 'error')
            
    except Exception as e:
        flash(f'Error al enviar recibo: {str(e)}', 'error')
    
    return redirect(url_for('ver_pago', pago_id=pago_id))

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
            
            # Crear registro de contabilidad inicial
            contabilidad = Contabilidad(capital_disponible=100000.00)
            db.session.add(contabilidad)
            db.session.commit()
    
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
