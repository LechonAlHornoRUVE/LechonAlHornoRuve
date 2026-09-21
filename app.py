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

# LOGO RUVE - versión tiny que sí carga
LOGO_B64 = "data:image/jpeg;base64,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"

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
            db.session.add_all([Producto(nombre='Lechón por Kilo', precio=350, stock=20), Producto(nombre='Lechón Entero', precio=3500, stock=5), Producto(nombre='Torta Lechon', precio=50, stock=50)])
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
a{color:#ff1493;text-decoration:none}
@media print{ .no-print{display:none} body{background:white;color:black} }
</style>
"""

LOGIN_HTML = STYLE + """
<div class="container" style="max-width:420px;margin-top:30px">
<div class="card text-center">
<img src='""" + LOGO_B64 + """' style="width:180px;height:180px;object-fit:contain;margin:0 auto 15px auto;display:block;border-radius:50%;border:3px solid #ff1493;background:white;padding:5px">
<h2 style="color:#ff1493;margin:0">LechonAlHornoRuve</h2>
<p style="font-size:12px;color:#aaa;margin-top:5px">EL SABOR HACE LA DIFERENCIA 🔥</p>
<form method="POST" class="mt-4 text-start">
<input name="username" class="form-control mb-3" placeholder="Usuario" required>
<input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required>
<button class="btn-rosa w-100">ENTRAR</button>
</form>{% if error %}<p style="color:red" class="mt-3">{{error}}</p>{% endif %}<small style="color:#666">admin / admin123</small></div></div>
"""

DASH_HTML = STYLE + """
<nav class="navbar p-3"><div class="d-flex align-items-center"><img src='""" + LOGO_B64 + """' style="width:40px;height:40px;border-radius:50%;margin-right:10px;background:white;padding:2px"><h4 style="color:#ff1493" class="m-0">LechonAlHornoRuve</h4></div>
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
<div class="text-center"><img src='""" + LOGO_B64 + """' style="width:80px;border-radius:50%"><h4 class="mt-2">LECHÓN AL HORNO RUVE</h4><p style="font-size:12px">Chetumal - EL SABOR HACE LA DIFERENCIA</p></div><hr>
<p><b>Ticket:</b> #{{v.id}}<br><b>Cliente:</b> {{v.cliente}}<br><b>Fecha:</b> {{v.fecha.strftime('%d/%m/%Y %H:%M')}}<br><b>Producto:</b> {{v.producto_nombre}}<br><b>Cantidad:</b> {{v.cantidad}}<br><b>Total:</b> ${{v.total}}</p><hr>
<p class="text-center">¡Gracias por su compra!<br>🔥 Recién horneado</p>
<div class="text-center no-print mt-3"><button onclick="window.print()" class="btn-rosa">🖨️ IMPRIMIR</button> <a href="/dashboard" class="btn btn-dark">Volver</a></div>
</div></div>
"""

REPORTE_HTML = STYLE + """<nav class="navbar p-3"><h4 style="color:#ff1493" class="m-0">📊 Reporte</h4><div><a href="/dashboard" class="me-3">Dashboard</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4"><div class="card"><h3 style="color:#ff1493">Reporte - {{hoy.strftime('%d/%m/%Y')}}</h3>
<div class="row mt-4"><div class="col-md-6"><h5>Total Hoy: <span style="color:#25D366">${{total_hoy}}</span></h5></div>
<div class="col-md-6 text-end no-print"><button onclick="window.print()" class="btn-rosa">🖨️ IMPRIMIR</button> <a href="https://wa.me/?text={{whats_reporte}}" target="_blank" class="btn-whats p-2">📲 WA</a></div></div>
<table class="table table-dark table-bordered mt-4"><tr><th>Hora</th><th>Cliente</th><th>Producto</th><th>Total</th></tr>{% for v in ventas_hoy %}<tr><td>{{v.fecha.strftime('%H:%M')}}</td><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td></tr>{% endfor %}</table></div></div>"""

PROD_HTML = STYLE + """<nav class="navbar p-3"><div class="d-flex align-items-center"><img src='""" + LOGO_B64 + """' style="width:35px;height:35px;border-radius:50%;margin-right:8px;background:white"><h4 style="color:#ff1493" class="m-0">Productos</h4></div><div><a href="/dashboard" class="me-3">Dashboard</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4"><div class="card"><h4>Agregar Producto</h4><form method="POST" class="row g-2"><div class="col-md-4"><input name="nombre" class="form-control" placeholder="Nombre" required></div><div class="col-md-3"><input name="precio" type="number" step="0.01" class="form-control" placeholder="Precio $" required></div><div class="col-md-2"><input name="stock" type="number" class="form-control" placeholder="Stock" required></div><div class="col-md-3"><button class="btn-rosa w-100">Agregar</button></div></form>
<table class="table table-dark table-bordered mt-4"><tr><th>Nombre</th><th>Precio</th><th>Stock</th><th></th></tr>{% for p in productos %}<tr><td>{{p.nombre}}</td><td>${{p.precio}}</td><td>{{p.stock}}</td><td><a href="/eliminar_producto/{{p.id}}" style="color:red">Eliminar</a></td></tr>{% endfor %}</table></div></div>"""

VENTAS_HTML = STYLE + """<nav class="navbar p-3"><h4 style="color:#ff1493" class="m-0">🐖 Historial</h4><div><a href="/dashboard" class="me-3">Dashboard</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4"><div class="card"><h4>Total: <span style="color:#ff1493">${{total}}</span></h4><table class="table table-dark table-bordered mt-3"><tr><th>Cliente</th><th>Producto</th><th>Total</th><th>Acciones</th></tr>{% for v in ventas %}<tr><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td><td><a href="/ticket/{{v.id}}" class="btn-rosa" style="font-size:11px">TICKET</a> <a href="https://wa.me/?text={{v.whats}}" target="_blank" class="btn-whats">WA</a></td></tr>{% endfor %}</table></div></div>"""

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
    cliente_nombre = request.form.get('cliente') or "Mostrador"
    if cliente_nombre.strip() == "": cliente_nombre = "Mostrador"
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