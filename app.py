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

# LOGO RUVE EN BASE64 - Ya no necesitas static/logo.png
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

REPORTE_HTML = STYLE + """<nav class="navbar p-3"><h4 style="color:#ff1493" class="m-0">📊 Reporte del Día</h4><div><a href="/dashboard" class="me-3">Dashboard</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4"><div class="card"><h3 style="color:#ff1493">Reporte - {{hoy.strftime('%d/%m/%Y')}}</h3>
<div class="row mt-4"><div class="col-md-6"><h5>Total Vendido Hoy: <span style="color:#25D366">${{total_hoy}}</span></h5><h6>Órdenes hoy: {{ventas_hoy|length}}</h6></div>
<div class="col-md-6 text-end no-print"><button onclick="window.print()" class="btn-rosa">🖨️ IMPRIMIR REPORTE</button> <a href="https://wa.me/?text={{whats_reporte}}" target="_blank" class="btn-whats p-2">📲 Enviar Reporte por WhatsApp</a></div></div>
<table class="table table-dark table-bordered mt-4"><tr><th>Hora</th><th>Cliente</th><th>Producto</th><th>Total</th></tr>{% for v in ventas_hoy %}<tr><td>{{v.fecha.strftime('%H:%M')}}</td><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td></tr>{% endfor %}</table></div></div>"""

PROD_HTML = STYLE + """<nav class="navbar p-3"><div class="d-flex align-items-center"><img src='""" + LOGO_B64 + """' style="width:35px;height:35px;border-radius:50%;margin-right:8px;background:white"><h4 style="color:#ff1493" class="m-0">Productos</h4></div><div><a href="/dashboard" class="me-3">Dashboard</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4"><div class="card"><h4>Agregar Producto</h4><form method="POST" class="row g-2"><div class="col-md-4"><input name="nombre" class="form-control" placeholder="Nombre producto" required></div><div class="col-md-3"><input name="precio" type="number" step="0.01" class="form-control" placeholder="Precio $" required></div><div class="col-md-2"><input name="stock" type="number" class="form-control" placeholder="Stock" required></div><div class="col-md-3"><button class="btn-rosa w-100">Agregar</button></div></form>
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
    cliente_nombre = request.form.get('cliente')
    if not cliente_nombre or cliente_nombre.strip() == "": cliente_nombre = "Mostrador"
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