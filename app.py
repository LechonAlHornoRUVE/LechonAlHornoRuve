import os
from flask import Flask, request, redirect, url_for, session, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'lechon-al-horno-ruve-secret-2026')

# FIX DEFINITIVO PARA EL ERROR 502 DE RENDER
database_url = os.environ.get('DATABASE_URL', '').strip()
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
if not database_url:
    database_url = "sqlite:///lechon.db"

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# MODELOS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100))
    producto = db.Column(db.String(100))
    cantidad = db.Column(db.Integer)
    total = db.Column(db.Float)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

# CREAR TABLAS Y ADMIN
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password=generate_password_hash('admin123'))
        db.add(admin)
        db.session.commit()

# HTML - TEMA NEGRO CON ROSADO
BASE_STYLE = """
<style>
body { background: #0a0a0a; color: white; font-family: Arial; }
.card { background: #1a1a1a; border: 2px solid #ff1493; border-radius: 15px; padding: 20px; margin-top: 30px; }
.btn-rosa { background: #ff1493; color: white; border: none; width: 100%; padding: 10px; border-radius: 8px; font-weight: bold; }
.btn-rosa:hover { background: #ff69b4; }
input { background: #2a2a2a !important; color: white !important; border: 1px solid #ff1493 !important; }
h2, h3 { color: #ff1493; }
.navbar { background: #000 !important; border-bottom: 2px solid #ff1493; }
</style>
"""

LOGIN_HTML = BASE_STYLE + """
<div class="container" style="max-width:400px">
  <div class="card">
    <h2 class="text-center">🐖 LechonAlHornoRuve</h2>
    <p class="text-center">Iniciar Sesión</p>
    <form method="POST">
      <input name="username" class="form-control mb-3" placeholder="Usuario" required>
      <input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required>
      <button class="btn-rosa">ENTRAR</button>
    </form>
    {% if error %}<p style="color:red; margin-top:10px">{{error}}</p>{% endif %}
    <p class="mt-3 text-center" style="font-size:12px">admin / admin123</p>
  </div>
</div>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
"""

DASHBOARD_HTML = BASE_STYLE + """
<nav class="navbar p-3"><h3 class="m-0">🐖 LechonAlHornoRuve</h3><a href="/logout" style="color:#ff1493">Salir</a></nav>
<div class="container">
  <div class="card">
    <h3>Bienvenido, {{user}}</h3>
    <p>Sistema de Ventas de Lechón al Horno - Chetumal</p>
    <hr style="border-color:#ff1493">
    <h4>Ventas Recientes</h4>
    <table class="table table-dark table-bordered">
      <tr><th>ID</th><th>Cliente</th><th>Producto</th><th>Total</th><th>Fecha</th></tr>
      {% for v in ventas %}
      <tr><td>{{v.id}}</td><td>{{v.cliente}}</td><td>{{v.producto}}</td><td>${{v.total}}</td><td>{{v.fecha.strftime('%d/%m')}}</td></tr>
      {% else %}
      <tr><td colspan="5" class="text-center">Sin ventas aún</td></tr>
      {% endfor %}
    </table>
  </div>
</div>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
"""

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user'] = u.username
            return redirect('/dashboard')
        error = "Usuario o contraseña incorrectos"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    ventas = Venta.query.order_by(Venta.id.desc()).all()
    return render_template_string(DASHBOARD_HTML, user=session['user'], ventas=ventas)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)