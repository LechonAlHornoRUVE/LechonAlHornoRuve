from flask import Flask, request, redirect, session, render_template_string, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'lechon-ruve-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lechon.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# MODELOS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(200))

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    precio = db.Column(db.Float)
    stock = db.Column(db.Integer, default=0)

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente = db.Column(db.String(100))
    producto_nombre = db.Column(db.String(100))
    cantidad = db.Column(db.Integer)
    total = db.Column(db.Float)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

try:
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password=generate_password_hash('admin123')))
            db.session.commit()
        # Productos iniciales si no hay
        if Producto.query.count() == 0:
            db.session.add_all([
                Producto(nombre='Lechón por Kilo', precio=350, stock=20),
                Producto(nombre='Lechón Entero', precio=3500, stock=5),
                Producto(nombre='Tacos de Lechón (orden)', precio=120, stock=50),
            ])
            db.session.commit()
except: pass

# ESTILOS BASE
STYLE = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#000;color:white;font-family:Arial}
.card{background:#111;border:2px solid #ff1493;border-radius:15px;padding:20px}
.btn-rosa{background:#ff1493;color:white;border:none;padding:8px 15px;border-radius:8px;font-weight:bold}
.btn-rosa:hover{background:#ff69b4;color:white}
.navbar{background:#000!important;border-bottom:2px solid #ff1493}
.table-dark{--bs-table-bg:#111}
input,select{background:#222!important;color:white!important;border:1px solid #ff1493!important}
a{color:#ff1493;text-decoration:none}
</style>
"""

def check_login():
    if 'user' not in session: return False
    return True

LOGIN_HTML = STYLE + """
<div class="container" style="max-width:400px;margin-top:80px">
<div class="card text-center"><h2 style="color:#ff1493">🐖 LechonAlHornoRuve</h2>
<form method="POST" class="mt-4 text-start">
<input name="username" class="form-control mb-3" placeholder="Usuario" required>
<input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required>
<button class="btn-rosa w-100">ENTRAR</button>
</form>{% if error %}<p style="color:red" class="mt-3">{{error}}</p>{% endif %}<small>admin / admin123</small></div></div>
"""

DASH_HTML = STYLE + """
<nav class="navbar p-3"><h4 style="color:#ff1493" class="m-0">🐖 LechonAlHornoRuve</h4>
<div><a href="/productos" class="me-3">Productos</a><a href="/ventas" class="me-3">Ventas</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4">
<div class="row">
<div class="col-md-4"><div class="card text-center"><h5>Ventas Hoy</h5><h2 style="color:#ff1493">${{total_hoy}}</h2></div></div>
<div class="col-md-4"><div class="card text-center"><h5>Productos</h5><h2 style="color:#ff1493">{{num_prod}}</h2></div></div>
<div class="col-md-4"><div class="card text-center"><h5>Órdenes</h5><h2 style="color:#ff1493">{{num_ventas}}</h2></div></div>
</div>
<div class="card mt-4"><h4 style="color:#ff1493">Vender Rápido - Chetumal</h4>
<form action="/vender" method="POST" class="row g-2 mt-2">
<div class="col-md-3"><input name="cliente" class="form-control" placeholder="Cliente" required></div>
<div class="col-md-3"><select name="producto_id" class="form-control" required>{% for p in productos %}<option value="{{p.id}}">{{p.nombre}} - ${{p.precio}}</option>{% endfor %}</select></div>
<div class="col-md-2"><input name="cantidad" type="number" value="1" min="1" class="form-control" required></div>
<div class="col-md-4"><button class="btn-rosa w-100">💰 REGISTRAR VENTA</button></div>
</form></div>
<div class="card mt-4"><h5>Últimas Ventas</h5><table class="table table-dark table-bordered mt-3"><tr><th>Cliente</th><th>Producto</th><th>Cant</th><th>Total</th><th>Fecha</th></tr>{% for v in ventas %}<tr><td>{{v.cliente}}</td><td>{{v.producto_nombre}}</td><td>{{v.cantidad}}</td><td>${{v.total}}</td><td>{{v.fecha.strftime('%d/%m %H:%M')}}</td></tr>{% endfor %}</table></div>
</div>
"""

PROD_HTML = STYLE + """
<nav class="navbar p-3"><h4 style="color:#ff1493" class="m-0">🐖 Productos</h4><div><a href="/dashboard" class="me-3">Dashboard</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4"><div class="card">
<h4>Agregar Producto</h4><form method="POST" class="row g-2"><div class="col-md-4"><input name="nombre" class="form-control" placeholder="Nombre" required></div><div class="col-md-3"><input name="precio" type="number" step="0.01" class="form-control" placeholder="Precio" required></div><div class="col-md-2"><input name="stock" type="number" class="form-control" placeholder="Stock" required></div><div class="col-md-3"><button class="btn-rosa w-100">Agregar</button></div></form>
<table class="table table-dark table-bordered mt-4"><tr><th>ID</th><th>Nombre</th><th>Precio</th><th>Stock</th><th>Acción</th></tr>{% for p in productos %}<tr><td>{{p.id}}</td><td>{{p.nombre}}</td><td>${{p.precio}}</td><td>{{p.stock}}</td><td><a href="/eliminar_producto/{{p.id}}" style="color:red">Eliminar</a></td></tr>{% endfor %}</table></div></div>
"""

VENTAS_HTML = STYLE + """
<nav class="navbar p-3"><h4 style="color:#ff1493" class="m-0">🐖 Historial Ventas</h4><div><a href="/dashboard" class="me-3">Dashboard</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4"><div class="card"><h4>Total Vendido: <span style="color:#ff1493">${{total}}</span></h4><table class="table table-dark table-bordered mt-3"><tr><th>ID</th><th>Cliente</th><th>Producto</th><th>Cantidad</th><th>Total</th><th>Fecha</th></tr>{% for v in ventas %}<tr><td>{{v.id}}</td><td>{{v.cliente}}</td><td>{{v.producto_nombre}}</td><td>{{v.cantidad}}</td><td>${{v.total}}</td><td>{{v.fecha.strftime('%d/%m/%Y %H:%M')}}</td></tr>{% endfor %}</table></div></div>
"""

@app.route('/', methods=['GET','POST'])
def login():
    error=None
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user']=u.username
            return redirect('/dashboard')
        error="Datos incorrectos"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/dashboard')
def dashboard():
    if not check_login(): return redirect('/')
    productos=Producto.query.all()
    ventas=Venta.query.order_by(Venta.id.desc()).limit(10).all()
    total_hoy = sum([v.total for v in Venta.query.filter(Venta.fecha >= datetime.now().replace(hour=0,minute=0,second=0)).all()])
    return render_template_string(DASH_HTML, productos=productos, ventas=ventas, total_hoy=total_hoy, num_prod=Producto.query.count(), num_ventas=Venta.query.count())

@app.route('/productos', methods=['GET','POST'])
def productos():
    if not check_login(): return redirect('/')
    if request.method=='POST':
        p=Producto(nombre=request.form['nombre'], precio=float(request.form['precio']), stock=int(request.form['stock']))
        db.session.add(p); db.session.commit()
        return redirect('/productos')
    return render_template_string(PROD_HTML, productos=Producto.query.all())

@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):
    if not check_login(): return redirect('/')
    p=Producto.query.get(id)
    if p: db.session.delete(p); db.session.commit()
    return redirect('/productos')

@app.route('/vender', methods=['POST'])
def vender():
    if not check_login(): return redirect('/')
    prod=Producto.query.get(int(request.form['producto_id']))
    cant=int(request.form['cantidad'])
    total=prod.precio * cant
    v=Venta(cliente=request.form['cliente'], producto_nombre=prod.nombre, cantidad=cant, total=total)
    if prod.stock >= cant: prod.stock -= cant
    db.session.add(v); db.session.commit()
    return redirect('/dashboard')

@app.route('/ventas')
def ventas():
    if not check_login(): return redirect('/')
    ventas=Venta.query.order_by(Venta.id.desc()).all()
    total=sum([v.total for v in ventas])
    return render_template_string(VENTAS_HTML, ventas=ventas, total=total)

@app.route('/logout')
def logout():
    session.clear(); return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))