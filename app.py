from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ruve-2026-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ruve.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ================= MODELOS =================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    rol = db.Column(db.String(20), default="cajero")
    nombre = db.Column(db.String(100), default="")
    email = db.Column(db.String(100), default="")

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'))
    imagen = db.Column(db.String(200), default="")

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total = db.Column(db.Float, default=0)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    mesa = db.Column(db.String(50), default="Mostrador")
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# ================= TEMPLATES =================
BASE_NAV = """
<div style="background:#000;border-bottom:2px solid #ff2d78;padding:10px 15px;display:flex;justify-content:space-between;align-items:center;color:white;">
  <div><b style="color:#ff4d8d;font-size:22px;">Ruve</b> <span style="margin-left:10px;">{{ current_user.username }} ({{ current_user.rol.upper() }})</span></div>
  <div style="display:flex;gap:15px;">
    <a href="/dashboard" style="color:#ff5c9e;text-decoration:none;">POS</a>
    <a href="/config" style="color:#4eff88;text-decoration:none;">⚙️ Config</a>
    <a href="/usuarios" style="color:orange;text-decoration:none;">👥 Usuarios</a>
    <a href="/logout" style="color:white;text-decoration:none;">Salir</a>
  </div>
</div>
"""

CONFIG_TEMPLATE = BASE_NAV + """
<style>
body{background:#0a0a0a;color:white;font-family:Arial;margin:0;}
.config-container{max-width:900px;margin:30px auto;background:#111;border:2px solid #ff2d78;border-radius:12px;padding:25px;box-shadow:0 0 20px rgba(255,45,120,0.4);}
.config-container h2{color:#ff4d8d;text-align:center;margin-bottom:20px;}
.config-container label{color:#ff8ab6;margin-top:12px;display:block;}
.config-container input{width:100%;padding:10px;background:#000;border:1px solid #ff2d78;border-radius:8px;color:white;margin-top:5px;}
.btn-guardar{width:100%;background:#ff2d78;color:white;border:none;padding:12px;border-radius:8px;margin-top:20px;font-weight:bold;cursor:pointer;font-size:16px;}
.btn-guardar:hover{background:#ff1a6e;}
details{background:#000;border:1px solid #ff2d78;border-radius:8px;margin-top:12px;padding:12px;}
summary{cursor:pointer;color:#ff4d8d;font-weight:bold;font-size:16px;list-style:none;}
summary::-webkit-details-marker{display:none;}
.tool-item{padding:8px 10px;margin:6px 0;background:#1a1a1a;border-radius:6px;display:flex;justify-content:space-between;align-items:center;}
.tool-item a{color:#4eff88;text-decoration:none;font-size:14px;}
</style>
<div class="config-container">
  <h2>⚙️ Configuración Administrador</h2>
  
  <label>Nombre del Negocio</label>
  <input type="text" value="Lechón al Horno Ruve">
  <label>Ticket - Mensaje Footer</label>
  <input type="text" value="¡Gracias por su compra!">
  
  <!-- LISTA DESPLEGABLE DE HERRAMIENTAS ADMIN -->
  <h3 style="color:#ff4d8d;margin-top:25px;">🛠️ Herramientas de Administrador</h3>
  
  <details>
    <summary>📂 1. Herramientas de Base de Datos ▼</summary>
    <div class="tool-item"><span>Respaldar Base de Datos</span><a href="/admin/backup">Ejecutar</a></div>
    <div class="tool-item"><span>Limpiar Ventas Antiguas (>90 días)</span><a href="/admin/limpiar_ventas">Limpiar</a></div>
    <div class="tool-item"><span>Reiniciar Stock a 0</span><a href="/admin/reset_stock">Reset</a></div>
  </details>

  <details>
    <summary>👥 2. Herramientas de Usuarios ▼</summary>
    <div class="tool-item"><span>Ver Todos los Usuarios</span><a href="/usuarios">Ver</a></div>
    <div class="tool-item"><span>Crear Cajero Rápido</span><a href="/usuarios/nuevo">Crear</a></div>
    <div class="tool-item"><span>Resetear Contraseñas</span><a href="/admin/reset_pass">Reset</a></div>
  </details>

  <details>
    <summary>🖨️ 3. Herramientas de Sistema y Tickets ▼</summary>
    <div class="tool-item"><span>Probar Impresora Térmica</span><a href="/admin/test_print">Probar</a></div>
    <div class="tool-item"><span>Limpiar Todos los Tickets Abiertos</span><a href="/admin/limpiar_tickets">Limpiar</a></div>
    <div class="tool-item"><span>Ver Log de Errores</span><a href="/admin/logs">Ver Logs</a></div>
  </details>

  <details>
    <summary>📊 4. Herramientas de Reportes Dueño ▼</summary>
    <div class="tool-item"><span>Reporte Completo en PDF</span><a href="/reporte">Generar PDF</a></div>
    <div class="tool-item"><span>Corte de Caja Hoy</span><a href="/ventas">Ver Corte</a></div>
    <div class="tool-item"><span>Productos con Stock Bajo</span><a href="/productos?filtro=bajo">Ver</a></div>
  </details>

  <button class="btn-guardar">💾 GUARDAR CONFIGURACIÓN</button>
</div>
"""

DASHBOARD_TEMPLATE = BASE_NAV + """
<style>body{background:#0a0a0a;color:white;font-family:Arial;margin:0;} .pos{display:flex;height:calc(100vh - 50px);}</style>
<div class="pos">
  <div style="width:32%;background:#111;border-right:2px solid #ff2d78;padding:10px;">POS - Mesa: Mostrador - Aquí va tu ticket</div>
  <div style="width:68%;padding:15px;display:flex;gap:10px;flex-wrap:wrap;">
    {% for p in productos %}
    <div style="background:#1a1a1a;border:1px solid #ff2d78;border-radius:10px;padding:10px;width:150px;text-align:center;">
      <div style="font-weight:bold;color:#ff4d8d;">{{ p.nombre }}</div><div>${{ p.precio }} | Stock {{ p.stock }}</div>
    </div>
    {% endfor %}
  </div>
</div>
"""

# ================= RUTAS =================
@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            login_user(u)
            return redirect('/dashboard')
        flash('Usuario o clave incorrecta')
    return render_template_string("""
    <body style="background:#000;display:flex;justify-content:center;align-items:center;height:100vh;font-family:Arial;">
    <form method="post" style="background:#111;border:2px solid #ff2d78;padding:30px;border-radius:12px;width:300px;">
      <h2 style="color:#ff4d8d;text-align:center;">Ruve Login</h2>
      <input name="username" placeholder="Usuario" style="width:100%;padding:10px;margin:10px 0;background:#000;border:1px solid #ff2d78;color:white;border-radius:6px;">
      <input name="password" type="password" placeholder="Contraseña" style="width:100%;padding:10px;margin:10px 0;background:#000;border:1px solid #ff2d78;color:white;border-radius:6px;">
      <button style="width:100%;background:#ff2d78;color:white;padding:10px;border:none;border-radius:6px;font-weight:bold;">Entrar</button>
    </form></body>
    """)

@app.route('/dashboard')
@login_required
def dashboard():
    productos = Producto.query.all()
    return render_template_string(DASHBOARD_TEMPLATE, productos=productos)

@app.route('/config')
@login_required
def config():
    if not current_user.is_admin:
        return "Solo admin", 403
    return render_template_string(CONFIG_TEMPLATE)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# Admin tools dummy
@app.route('/admin/<accion>')
@login_required
def admin_accion(accion):
    if not current_user.is_admin:
        return "Solo admin", 403
    return f"Acción {accion} ejecutada correctamente - <a href='/config'>Volver a Config</a>"

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password=generate_password_hash('admin123'), is_admin=True, rol='admin', nombre='Administrador')
        db.session.add(admin)
        db.session.commit()
    if not Categoria.query.first():
        for cat in ["Lechón","Tortas","Órdenes","Bebidas","Extras"]:
            db.session.add(Categoria(nombre=cat))
        db.session.commit()
    if not Producto.query.first():
        db.session.add(Producto(nombre="Lechón Entero", precio=3500, stock=4, categoria_id=1))
        db.session.add(Producto(nombre="Lechón por Kilo", precio=350, stock=45, categoria_id=1))
        db.session.add(Producto(nombre="Torta de Lechón", precio=70, stock=27, categoria_id=2))
        db.session.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False)