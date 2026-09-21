from flask import Flask, request, redirect, session, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, urllib.parse

app = Flask(__name__)
app.secret_key = 'lechon-ruve-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lechon.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
        if Producto.query.count() == 0:
            db.session.add_all([
                Producto(nombre='Lechón por Kilo', precio=350, stock=20),
                Producto(nombre='Lechón Entero', precio=3500, stock=5),
                Producto(nombre='Torta Lechon', precio=50, stock=50),
            ])
            db.session.commit()
except: pass

STYLE = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#000;color:white;font-family:Arial}
.card{background:#111;border:2px solid #ff1493;border-radius:15px;padding:20px}
.btn-rosa{background:#ff1493;color:white;border:none;padding:8px 15px;border-radius:8px;font-weight:bold}
.btn-rosa:hover{background:#ff69b4;color:white}
.btn-whats{background:#25D366;color:white;border:none;padding:5px 10px;border-radius:6px;font-size:12px}
.navbar{background:#000!important;border-bottom:2px solid #ff1493}
.table-dark{--bs-table-bg:#111}
input,select{background:#222!important;color:white!important;border:1px solid #ff1493!important}
::placeholder{color:#bbb!important;opacity:1}
input::placeholder{color:#bbb!important}
a{color:#ff1493;text-decoration:none}
@media print{ .no-print{display:none} body{background:white;color:black} }
</style>
"""

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
<div><a href="/productos" class="me-2">Productos</a><a href="/ventas" class="me-2">Ventas</a><a href="/reporte" class="me-2">Reporte</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4">
<div class="row">
<div class="col-md-4"><div class="card text-center"><h5>Ventas Hoy</h5><h2 style="color:#ff1493">${{total_hoy}}</h2><a href="/reporte" class="btn-rosa mt-2 d-block" style="font-size:12px">VER REPORTE DEL DÍA</a></div></div>
<div class="col-md-4"><div class="card text-center"><h5>Productos</h5><h2 style="color:#ff1493">{{num_prod}}</h2></div></div>
<div class="col-md-4"><div class="card text-center"><h5>Órdenes</h5><h2 style="color:#ff1493">{{num_ventas}}</h2></div></div>
</div>
<div class="card mt-4"><h4 style="color:#ff1493">Vender Rápido - Chetumal</h4>
<form action="/vender" method="POST" class="row g-2 mt-2">
<div class="col-md-3"><input name="cliente" class="form-control" placeholder="👤 Cliente (opcional) Ej: Mostrador"></div>
<div class="col-md-3"><select name="producto_id" class="form-control" required>{% for p in productos %}<option value="{{p.id}}">{{p.nombre}} - ${{p.precio}}</option>{% endfor %}</select></div>
<div class="col-md-2"><input name="cantidad" type="number" value="1" min="1" class="form-control" required></div>
<div class="col-md-4"><button class="btn-rosa w-100">💰 REGISTRAR VENTA</button></div>
</form></div>
<div class="card mt-4"><h5>Últimas Ventas</h5><table class="table table-dark table-bordered mt-3"><tr><th>Cliente</th><th>Producto</th><th>Total</th><th>Acciones</th></tr>
{% for v in ventas %}<tr><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td>
<td><a href="/ticket/{{v.id}}" class="btn-rosa" style="font-size:11px;padding:4px 8px">🎫 TICKET</a> <a href="https://wa.me/?text={{v.whats}}" target="_blank" class="btn-whats">WhatsApp</a></td></tr>{% endfor %}</table></div>
</div>
"""

TICKET_HTML = STYLE + """
<div class="container" style="max-width:400px;margin-top:20px">
<div class="card" id="ticket" style="background:white;color:black;border:2px dashed black">
<h4 class="text-center">🐖 LECHÓN AL HORNO RUVE</h4><p class="text-center" style="font-size:12px">Chetumal, Quintana Roo<br>Tel: 983-XXX-XXXX</p><hr>
<p><b>Ticket:</b> #{{v.id}}<br><b>Cliente:</b> {{v.cliente}}<br><b>Fecha:</b> {{v.fecha.strftime('%d/%m/%Y %H:%M')}}<br><b>Producto:</b> {{v.producto_nombre}}<br><b>Cantidad:</b> {{v.cantidad}}<br><b>Total:</b> ${{v.total}}</p><hr>
<p class="text-center">¡Gracias por su compra!<br>🔥 Recién horneado</p>
<div class="text-center no-print mt-3"><button onclick="window.print()" class="btn-rosa">🖨️ IMPRIMIR</button> <a href="/dashboard" class="btn btn-dark">Volver</a></div>
</div></div>
"""

REPORTE_HTML = STYLE + """
<nav class="navbar p-3"><h4 style="color:#ff1493" class="m-0">📊 Reporte del Día</h4><div><a href="/dashboard" class="me-3">Dashboard</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4"><div class="card">
<h3 style="color:#ff1493">Reporte - {{hoy.strftime('%d/%m/%Y')}}</h3>
<div class="row mt-4"><div class="col-md-6"><h5>Total Vendido Hoy: <span style="color:#25D366">${{total_hoy}}</span></h5><h6>Órdenes hoy: {{ventas_hoy|length}}</h6></div>
<div class="col-md-6 text-end no-print"><button onclick="window.print()" class="btn-rosa">🖨️ IMPRIMIR REPORTE</button> <a href="https://wa.me/?text={{whats_reporte}}" target="_blank" class="btn-whats p-2">📲 Enviar Reporte por WhatsApp</a></div></div>
<table class="table table-dark table-bordered mt-4"><tr><th>Hora</th><th>Cliente</th><th>Producto</th><th>Total</th></tr>{% for v in ventas_hoy %}<tr><td>{{v.fecha.strftime('%H:%M')}}</td><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td></tr>{% endfor %}</table>
</div></div>
"""

PROD_HTML = STYLE + """
<nav class="navbar p-3"><h4 style="color:#ff1493" class="m-0">🐖 Productos</h4><div><a href="/dashboard" class="me-3">Dashboard</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4"><div class="card">
<h4>Agregar Producto</h4><form method="POST" class="row g-2"><div class="col-md-4"><input name="nombre" class="form-control" placeholder="Nombre producto" required></div><div class="col-md-3"><input name="precio" type="number" step="0.01" class="form-control" placeholder="Precio $" required></div><div class="col-md-2"><input name="stock" type="number" class="form-control" placeholder="Stock" required></div><div class="col-md-3"><button class="btn-rosa w-100">Agregar</button></div></form>
<table class="table table-dark table-bordered mt-4"><tr><th>Nombre</th><th>Precio</th><th>Stock</th><th></th></tr>{% for p in productos %}<tr><td>{{p.nombre}}</td><td>${{p.precio}}</td><td>{{p.stock}}</td><td><a href="/eliminar_producto/{{p.id}}" style="color:red">Eliminar</a></td></tr>{% endfor %}</table></div></div>
"""

VENTAS_HTML = STYLE + """
<nav class="navbar p-3"><h4 style="color:#ff1493" class="m-0">🐖 Historial</h4><div><a href="/dashboard" class="me-3">Dashboard</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4"><div class="card"><h4>Total: <span style="color:#ff1493">${{total}}</span></h4><table class="table table-dark table-bordered mt-3"><tr><th>Cliente</th><th>Producto</th><th>Total</th><th>Acciones</th></tr>{% for v in ventas %}<tr><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td><td><a href="/ticket/{{v.id}}" class="btn-rosa" style="font-size:11px">TICKET</a> <a href="https://wa.me/?text={{v.whats}}" target="_blank" class="btn-whats">WA</a></td></tr>{% endfor %}</table></div></div>
"""

def make_whats(v):
    txt = f"Hola {v.cliente}! 🐖 Tu pedido de LechonAlHornoRuve: {v.cantidad}x {v.producto_nombre} - Total ${v.total}. Gracias! Ticket #{v.id}"
    return urllib.parse.quote(txt)

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
    if 'user' not in session: return redirect('/')
    productos=Producto.query.all()
    ventas=Venta.query.order_by(Venta.id.desc()).limit(10).all()
    for v in ventas: v.whats = make_whats(v)
    hoy = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    total_hoy = sum([v.total for v in Venta.query.filter(Venta.fecha >= hoy).all()])
    return render_template_string(DASH_HTML, productos=productos, ventas=ventas, total_hoy=total_hoy, num_prod=Producto.query.count(), num_ventas=Venta.query.count())

@app.route('/productos', methods=['GET','POST'])
def productos_route():
    if 'user' not in session: return redirect('/')
    if request.method=='POST':
        p=Producto(nombre=request.form['nombre'], precio=float(request.form['precio']), stock=int(request.form['stock']))
        db.session.add(p); db.session.commit()
        return redirect('/productos')
    return render_template_string(PROD_HTML, productos=Producto.query.all())

@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):
    if 'user' not in session: return redirect('/')
    p=Producto.query.get(id)
    if p: db.session.delete(p); db.session.commit()
    return redirect('/productos')

@app.route('/vender', methods=['POST'])
def vender():
    if 'user' not in session: return redirect('/')
    prod=Producto.query.get(int(request.form['producto_id']))
    cant=int(request.form['cantidad'])
    total=prod.precio * cant
    cliente_nombre = request.form.get('cliente')
    if not cliente_nombre or cliente_nombre.strip() == "":
        cliente_nombre = "Mostrador"
    v=Venta(cliente=cliente_nombre, producto_nombre=prod.nombre, cantidad=cant, total=total)
    if prod.stock >= cant: prod.stock -= cant
    db.session.add(v); db.session.commit()
    return redirect(f'/ticket/{v.id}')

@app.route('/ventas')
def ventas_route():
    if 'user' not in session: return redirect('/')
    ventas=Venta.query.order_by(Venta.id.desc()).all()
    for v in ventas: v.whats = make_whats(v)
    total=sum([v.total for v in ventas])
    return render_template_string(VENTAS_HTML, ventas=ventas, total=total)

@app.route('/ticket/<int:id>')
def ticket(id):
    if 'user' not in session: return redirect('/')
    v=Venta.query.get(id)
    return render_template_string(TICKET_HTML, v=v)

@app.route('/reporte')
def reporte():
    if 'user' not in session: return redirect('/')
    hoy = datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    ventas_hoy = Venta.query.filter(Venta.fecha >= hoy).order_by(Venta.fecha.desc()).all()
    total_hoy = sum([v.total for v in ventas_hoy])
    txt = f"📊 REPORTE LECHON RUVE {datetime.now().strftime('%d/%m/%Y')} - Total: ${total_hoy} - {len(ventas_hoy)} ventas"
    whats_reporte = urllib.parse.quote(txt)
    return render_template_string(REPORTE_HTML, ventas_hoy=ventas_hoy, total_hoy=total_hoy, hoy=datetime.now(), whats_reporte=whats_reporte)

@app.route('/logout')
def logout():
    session.clear(); return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))