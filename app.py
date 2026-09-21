from flask import Flask, request, redirect, session, render_template_string, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from collections import defaultdict
import os, urllib.parse, io

app = Flask(__name__)
app.secret_key = 'lechon-ruve-2026-final-fase4'

db_url = os.environ.get('DATABASE_URL', 'sqlite:///lechon.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True)
    password=db.Column(db.String(200))
    is_admin=db.Column(db.Boolean, default=False)
    rol=db.Column(db.String(20), default="cajero")

class Producto(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(100))
    precio=db.Column(db.Float)
    stock=db.Column(db.Integer, default=0)
    costo=db.Column(db.Float, default=0) # NUEVO FASE 4

class Venta(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    cliente=db.Column(db.String(100))
    producto_nombre=db.Column(db.String(100))
    cantidad=db.Column(db.Integer)
    total=db.Column(db.Float)
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    vendedor=db.Column(db.String(80), default="admin")
    costo_total=db.Column(db.Float, default=0) # NUEVO

class Config(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    whatsapp_btn=db.Column(db.Boolean, default=True)
    tickets=db.Column(db.Boolean, default=True)
    reporte_pdf=db.Column(db.Boolean, default=True)
    total_whatsapp=db.Column(db.Boolean, default=True)
    numero_whatsapp=db.Column(db.String(20), default="529831000000")
    mod_mesas=db.Column(db.Boolean, default=True)
    mod_cocina=db.Column(db.Boolean, default=True)
    mod_clientes=db.Column(db.Boolean, default=True)
    mod_reservas=db.Column(db.Boolean, default=True)
    mod_llevar=db.Column(db.Boolean, default=True)
    mod_dueno=db.Column(db.Boolean, default=True) # NUEVO

class Mesa(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(50))
    estado=db.Column(db.String(20), default="libre")
    total=db.Column(db.Float, default=0)

class Comanda(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    mesa_id=db.Column(db.Integer, db.ForeignKey('mesa.id'))
    producto_nombre=db.Column(db.String(100))
    cantidad=db.Column(db.Integer)
    estado=db.Column(db.String(20), default="cocina")
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    mesero=db.Column(db.String(80))
    mesa = db.relationship('Mesa', backref='comandas')

class Cliente(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(100))
    telefono=db.Column(db.String(20))
    visitas=db.Column(db.Integer, default=0)
    gasto_total=db.Column(db.Float, default=0)
    ultima_visita=db.Column(db.DateTime, default=datetime.utcnow)

class Reserva(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    cliente_nombre=db.Column(db.String(100))
    telefono=db.Column(db.String(20))
    fecha=db.Column(db.String(20))
    hora=db.Column(db.String(20))
    personas=db.Column(db.Integer)
    mesa_id=db.Column(db.Integer, db.ForeignKey('mesa.id'), nullable=True)
    estado=db.Column(db.String(20), default="pendiente")
    mesa = db.relationship('Mesa', backref='reservas')

class PedidoLlevar(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    cliente_nombre=db.Column(db.String(100))
    telefono=db.Column(db.String(20))
    producto_nombre=db.Column(db.String(100))
    cantidad=db.Column(db.Integer)
    total=db.Column(db.Float)
    tipo=db.Column(db.String(20), default="llevar")
    direccion=db.Column(db.String(200), default="")
    estado=db.Column(db.String(20), default="cocina")
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    vendedor=db.Column(db.String(80))
    costo_total=db.Column(db.Float, default=0)

class Gasto(db.Model): # NUEVO FASE 4
    id=db.Column(db.Integer, primary_key=True)
    concepto=db.Column(db.String(100))
    monto=db.Column(db.Float)
    categoria=db.Column(db.String(50), default="general") # renta, gas, insumos, personal, otro
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    usuario=db.Column(db.String(80))

def get_config():
    c=Config.query.first()
    if not c: c=Config(); db.session.add(c); db.session.commit()
    return c

with app.app_context():
    from sqlalchemy import text
    db.create_all()
    # Parches para no borrar
    try:
        db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS rol VARCHAR(20) DEFAULT \'cajero\'')); db.session.commit()
    except: db.session.rollback()
    try:
        db.session.execute(text('ALTER TABLE producto ADD COLUMN IF NOT EXISTS costo FLOAT DEFAULT 0')); db.session.commit()
    except: db.session.rollback()
    try:
        db.session.execute(text('ALTER TABLE venta ADD COLUMN IF NOT EXISTS costo_total FLOAT DEFAULT 0')); db.session.commit()
    except: db.session.rollback()
    try:
        db.session.execute(text('ALTER TABLE pedido_llevar ADD COLUMN IF NOT EXISTS costo_total FLOAT DEFAULT 0')); db.session.commit()
    except: db.session.rollback()
    for col in ['mod_mesas','mod_cocina','mod_clientes','mod_reservas','mod_llevar','mod_dueno']:
        try:
            db.session.execute(text(f'ALTER TABLE config ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT TRUE')); db.session.commit()
        except: db.session.rollback()
    try:
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password=generate_password_hash('admin123'), is_admin=True, rol="admin")); db.session.commit()
        else:
            u=User.query.filter_by(username='admin').first(); u.is_admin=True
            if not u.rol: u.rol="admin"
            db.session.commit()
    except: db.session.rollback()
    get_config()
    if Producto.query.count()==0:
        db.session.add_all([Producto(nombre='Lechón por Kilo', precio=350, stock=50, costo=180), Producto(nombre='Lechón Entero', precio=3500, stock=5, costo=1800), Producto(nombre='Torta de Lechón', precio=70, stock=30, costo=35)]); db.session.commit()
    if Mesa.query.count()==0:
        for i in range(1,13):
            db.session.add(Mesa(nombre=f"Mesa {i}", estado="libre", total=0))
        db.session.commit()

STYLE = """<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><style>
body{background:#000;color:white;font-family:Arial}.card{background:#111;border:2px solid #ff4d8a;border-radius:15px;padding:20px}
.btn-rosa{background:#ff4d8a;color:white;border:none;padding:10px 18px;border-radius:10px;font-weight:bold}
.btn-whats{background:#25D366;color:white;padding:6px 12px;border-radius:8px;text-decoration:none;font-size:12px;font-weight:bold}
.navbar{background:#000!important;border-bottom:2px solid #ff4d8a}
input,select{background:#222!important;color:white!important;border:1px solid #ff4d8a!important}
textarea{background:#222!important;color:white!important;border:1px solid #ff4d8a!important}
a{color:#ff4d8a;text-decoration:none}
.mesa-libre{border:3px solid #25D366;background:#0a1a0a;padding:20px;border-radius:15px;text-align:center;cursor:pointer}
.mesa-ocupada{border:3px solid #ff4d3a;background:#1a0a0a;padding:20px;border-radius:15px;text-align:center;cursor:pointer}
@media print{.no-print{display:none} body{background:white;color:black}}
</style>"""

def nav():
    cfg=get_config(); rol = session.get('rol','cajero'); is_admin = session.get('is_admin', False)
    links=""
    if cfg.mod_mesas and (is_admin or rol in ['admin','cajero','mesero']):
        links+= '<a href="/mesas" class="me-3" style="color:#00e5ff">🪑 Mesas</a>'
    if cfg.mod_cocina and (is_admin or rol in ['cocina','admin','cajero']):
        links+= '<a href="/cocina" class="me-3" style="color:#ffcc00">🔥 Cocina</a>'
    if cfg.mod_clientes and (is_admin or rol in ['admin','cajero','mesero']):
        links+= '<a href="/clientes" class="me-3" style="color:#00ffaa">👤 Clientes</a>'
    if cfg.mod_reservas and (is_admin or rol in ['admin','cajero','mesero']):
        links+= '<a href="/reservas" class="me-3" style="color:#aa88ff">📅 Reservas</a>'
    if cfg.mod_llevar and (is_admin or rol in ['admin','cajero','mesero']):
        links+= '<a href="/para_llevar" class="me-3" style="color:#ffaa00">🛵 Llevar</a>'
    if cfg.mod_dueno and is_admin:
        links+= '<a href="/dueno" class="me-3" style="color:#ff4d8a;font-weight:bold">💰 Dueño</a>'
    admin_links = f'<a href="/admin/config" class="me-3" style="color:#25D366">⚙️ Config</a><a href="/admin/usuarios" class="me-3" style="color:#ffcc00">👥 Usuarios</a>' if is_admin else ''
    prod_link = '<a href="/productos" class="me-3">Productos</a>' if is_admin else ''
    return f'<nav class="navbar p-3"><div class="d-flex align-items-center"><img src="/static/logo.png?v=ruve3" style="width:45px;height:45px;border-radius:50%;margin-right:10px;background:white;padding:3px"><h4 style="color:#ff4d8a" class="m-0">Ruve</h4> <small style="color:#aaa;margin-left:10px">{session.get("user")} ({rol})</small></div><div><a href="/dashboard" class="me-3">POS</a>{links}{prod_link}<a href="/ventas" class="me-3">Ventas</a><a href="/reporte" class="me-3">Reporte</a>{admin_links}<a href="/logout">Salir</a></div></nav>'

def check_mod(mod_name):
    cfg=get_config()
    if not getattr(cfg, mod_name, True):
        if mod_name=='mod_dueno' and not session.get('is_admin'):
            return redirect('/dashboard')
        if mod_name!='mod_dueno':
            return render_template_string(STYLE+nav()+f'<div class="container mt-5"><div class="card text-center"><h3 style="color:#ff4d3a">Módulo Deshabilitado</h3><p style="color:#aaa">El administrador ha deshabilitado este módulo. Actívalo en ⚙️ Config</p><a href="/dashboard" class="btn-rosa">Volver al POS</a></div></div>')
    return None

def make_whats_msg(v): return urllib.parse.quote(f"Hola {v.cliente}! 🐖 Tu pedido Ruve: {v.cantidad}x {v.producto_nombre} - ${v.total}. Ticket #{v.id}")
def admin_required():
    if 'user' not in session: return redirect('/')
    if not session.get('is_admin'): return redirect('/dashboard')
    return None

@app.route('/', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user']=u.username; session['is_admin']=u.is_admin; session['rol']=u.rol
            if u.rol == 'cocina': return redirect('/cocina')
            if u.rol == 'mesero': return redirect('/mesas')
            return redirect('/dashboard')
    return render_template_string(STYLE+f'<div class="container" style="max-width:420px;margin-top:25px"><div class="card text-center"><img src="/static/logo.png?v=ruve3" style="width:210px;height:210px;object-fit:contain;background:white;border-radius:50%;padding:8px;border:3px solid #ff4d8a;margin:0 auto"><h2 style="color:#ff4d8a" class="mt-3">LechonAlHornoRuve</h2><form method="POST" class="mt-4 text-start"><input name="username" class="form-control mb-3" placeholder="Usuario" required><input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required><button class="btn-rosa w-100">ENTRAR</button></form></div></div>')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    cfg=get_config(); productos=Producto.query.all()
    hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    if session.get('is_admin'):
        ventas = Venta.query.order_by(Venta.id.desc()).limit(12).all()
        total_hoy = sum([v.total for v in Venta.query.filter(Venta.fecha>=hoy).all()]); num_ventas = Venta.query.count()
    else:
        ventas_q = Venta.query.filter_by(vendedor=session.get('user'))
        ventas = ventas_q.order_by(Venta.id.desc()).limit(12).all()
        total_hoy = sum([v.total for v in ventas_q.filter(Venta.fecha>=hoy).all()]); num_ventas = ventas_q.count()
    html=STYLE+nav()+"""<div class="container mt-4"><div class="row"><div class="col-md-4"><div class="card text-center"><h6>{% if is_admin %}Ventas Hoy (Todos){% else %}Mis Ventas Hoy{% endif %}</h6><h2 style="color:#ff4d8a">${{total_hoy}}</h2></div></div><div class="col-md-4"><div class="card text-center"><h6>Productos</h6><h2 style="color:#ff4d8a">{{num_prod}}</h2></div></div><div class="col-md-4"><div class="card text-center"><h6>{% if is_admin %}Tickets Totales{% else %}Mis Tickets{% endif %}</h6><h2 style="color:#ff4d8a">{{num_ventas}}</h2></div></div></div>
    <div class="card mt-4"><h5 style="color:#ff4d8a">Vender Rápido - Chetumal ({{session.get('user')}})</h5>
    <form action="/vender" method="POST" class="row g-2 mt-3"><div class="col-md-3"><input name="cliente" class="form-control" placeholder="👤 Cliente" list="clientes-list"><datalist id="clientes-list">{% for c in clientes %}<option value="{{c.nombre}}">{% endfor %}</datalist></div><div class="col-md-4"><select name="producto_id" class="form-control" required>{% for p in productos %}<option value="{{p.id}}">{{p.nombre}} - ${{p.precio}} (Stock: {{p.stock}}) {% if p.stock <= 3 %}⚠️ BAJO{% endif %}</option>{% endfor %}</select></div><div class="col-md-2"><input name="cantidad" type="number" value="1" min="1" class="form-control"></div><div class="col-md-3"><button class="btn-rosa w-100">💰 VENDER</button></div></form></div>
    <div class="card mt-4"><h5>{% if is_admin %}Últimas Ventas{% else %}Mis Últimas Ventas{% endif %}</h5><table class="table table-dark table-bordered mt-3"><tr><th>Cliente</th><th>Producto</th><th>Total</th>{% if is_admin %}<th>Vendedor</th>{% endif %}<th>Acciones</th></tr>
    {% for v in ventas %}<tr><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td>{% if is_admin %}<td>{{v.vendedor}}</td>{% endif %}<td>{% if cfg.tickets %}<a href="/ticket/{{v.id}}" class="btn-rosa" style="font-size:11px">TICKET</a>{% endif %}{% if cfg.whatsapp_btn %}<a href="https://wa.me/?text={{v.msj}}" target="_blank" class="btn-whats ms-1">WA</a>{% endif %}</td></tr>{% endfor %}</table></div></div>"""
    for v in ventas: v.msj=make_whats_msg(v)
    return render_template_string(html, productos=productos, ventas=ventas, total_hoy=total_hoy, num_prod=Producto.query.count(), num_ventas=num_ventas, cfg=cfg, is_admin=session.get('is_admin'), clientes=Cliente.query.all())

# --- MESAS Y COCINA ---
@app.route('/mesas')
def mesas_view():
    if 'user' not in session: return redirect('/')
    chk=check_mod('mod_mesas');
    if chk: return chk
    mesas = Mesa.query.all()
    return render_template_string(STYLE+nav()+"""
    <div class="container mt-4"><div class="card"><h4 style="color:#00e5ff">🪑 Control de Mesas</h4>
    <div class="row g-3 mt-2">{% for m in mesas %}<div class="col-md-3"><div class="{{'mesa-libre' if m.estado=='libre' else 'mesa-ocupada'}}" onclick="window.location='/mesa/{{m.id}}'"><h5>{{m.nombre}}</h5><p style="margin:0">{{m.estado|upper}} {% if m.estado!='libre' %}- ${{m.total}}{% endif %}</p><small>{{m.comandas|selectattr('estado','ne','entregado')|list|length}} platillos</small></div></div>{% endfor %}</div></div></div>
    """, mesas=mesas)

@app.route('/mesa/<int:id>', methods=['GET','POST'])
def mesa_detalle(id):
    if 'user' not in session: return redirect('/')
    chk=check_mod('mod_mesas');
    if chk: return chk
    mesa = Mesa.query.get(id); productos = Producto.query.all()
    if request.method=='POST':
        prod = Producto.query.get(int(request.form['producto_id'])); cant = int(request.form['cantidad'])
        com = Comanda(mesa_id=mesa.id, producto_nombre=prod.nombre, cantidad=cant, mesero=session.get('user'), estado="cocina")
        mesa.estado="ocupada"; mesa.total = (mesa.total or 0) + (prod.precio*cant)
        prod.stock = prod.stock - cant
        db.session.add(com); db.session.commit()
        return redirect(f'/mesa/{id}')
    return render_template_string(STYLE+nav()+"""
    <div class="container mt-4"><div class="row"><div class="col-md-7"><div class="card"><h4>{{mesa.nombre}} - {{mesa.estado|upper}} - Total: ${{mesa.total}}</h4>
    <table class="table table-dark mt-3"><tr><th>Producto</th><th>Cant</th><th>Estado</th><th>Mesero</th></tr>
    {% for c in mesa.comandas %}{% if c.estado!='entregado' %}<tr><td>{{c.producto_nombre}}</td><td>{{c.cantidad}}</td><td><span style="color:{% if c.estado=='cocina' %}#ff4d3a{% else %}#25D366{% endif %}">{{c.estado}}</span></td><td>{{c.mesero}}</td></tr>{% endif %}{% endfor %}</table>
    <div class="d-flex gap-2 no-print"><a href="/mesa/{{mesa.id}}/cobrar" class="btn-rosa">💰 COBRAR Y LIBERAR</a><a href="/mesas" class="btn btn-dark">Volver a Mesas</a></div>
    </div></div><div class="col-md-5"><div class="card"><h5 style="color:#00e5ff">Agregar Platillo (Se envía a cocina)</h5><form method="POST" class="mt-3"><select name="producto_id" class="form-control mb-3" required>{% for p in productos %}<option value="{{p.id}}">{{p.nombre}} - ${{p.precio}} ({{p.stock}})</option>{% endfor %}</select><input name="cantidad" type="number" value="1" min="1" class="form-control mb-3" required><button class="btn-rosa w-100">🍽️ MANDAR A COCINA</button></form></div></div></div></div>
    """, mesa=mesa, productos=productos)

@app.route('/mesa/<int:id>/cobrar')
def mesa_cobrar(id):
    if 'user' not in session: return redirect('/')
    mesa = Mesa.query.get(id)
    for c in mesa.comandas:
        if c.estado!= 'entregado':
            prod = Producto.query.filter_by(nombre=c.producto_nombre).first()
            precio = prod.precio if prod else 0
            costo = (prod.costo if prod and prod.costo else 0) * c.cantidad
            v = Venta(cliente=mesa.nombre, producto_nombre=c.producto_nombre, cantidad=c.cantidad, total=precio*c.cantidad, vendedor=session.get('user'), costo_total=costo)
            db.session.add(v); c.estado='entregado'
            cli = Cliente.query.filter_by(nombre=mesa.nombre).first()
            if not cli:
                cli = Cliente(nombre=mesa.nombre, telefono="", visitas=0, gasto_total=0)
                db.session.add(cli)
            cli.visitas+=1; cli.gasto_total+=v.total; cli.ultima_visita=datetime.utcnow()
    mesa.estado='libre'; mesa.total=0; db.session.commit()
    return redirect('/mesas')

@app.route('/cocina')
def cocina_view():
    if 'user' not in session: return redirect('/')
    chk=check_mod('mod_cocina');
    if chk: return chk
    comandas = Comanda.query.filter(Comanda.estado=='cocina').order_by(Comanda.fecha.asc()).all()
    llevar = PedidoLlevar.query.filter(PedidoLlevar.estado=='cocina').order_by(PedidoLlevar.fecha.asc()).all()
    return render_template_string(STYLE+nav()+"""
    <div class="container mt-4"><div class="card" style="border-color:#ffcc00"><h3 style="color:#ffcc00">🔥 KDS - Cocina ({{comandas|length + llevar|length}} pendientes)</h3>
    <div class="row g-3 mt-2">
    {% for c in comandas %}<div class="col-md-4"><div class="card" style="background:#1a1a0a;border-color:#ff4d3a"><h6 style="color:#00e5ff">{{c.mesa.nombre}}</h6><h4 style="color:white">{{c.cantidad}}x {{c.producto_nombre}}</h4><small>Mesero: {{c.mesero}} - {{c.fecha.strftime('%H:%M')}}</small><a href="/cocina/listo/{{c.id}}" class="btn-rosa w-100 mt-3" style="background:#25D366">✅ LISTO</a></div></div>{% endfor %}
    {% for p in llevar %}<div class="col-md-4"><div class="card" style="background:#1a1500;border-color:#ffaa00"><h6 style="color:#ffaa00">🛵 {{p.tipo|upper}} - {{p.cliente_nombre}}</h6><h4 style="color:white">{{p.cantidad}}x {{p.producto_nombre}}</h4><small>{{p.telefono}} {% if p.direccion %}- {{p.direccion}}{% endif %} - {{p.fecha.strftime('%H:%M')}}</small><a href="/llevar/listo/{{p.id}}" class="btn-rosa w-100 mt-3" style="background:#ffaa00;color:black">✅ LISTO LLEVAR</a></div></div>{% endfor %}
    {% if not comandas and not llevar %}<div class="col-12 text-center p-4"><h4 style="color:#25D366">Todo al día 🟢</h4></div>{% endif %}
    </div></div></div><script>setTimeout(()=>location.reload(), 15000);</script>
    """, comandas=comandas, llevar=llevar)

@app.route('/cocina/listo/<int:id>')
def cocina_listo(id):
    if 'user' not in session: return redirect('/')
    c = Comanda.query.get(id); c.estado='listo'; db.session.commit()
    return redirect('/cocina')

@app.route('/clientes', methods=['GET','POST'])
def clientes_view():
    if 'user' not in session: return redirect('/')
    chk=check_mod('mod_clientes');
    if chk: return chk
    if request.method=='POST':
        nombre=request.form['nombre'].strip(); tel=request.form['telefono'].strip()
        if not Cliente.query.filter_by(nombre=nombre).first():
            db.session.add(Cliente(nombre=nombre, telefono=tel, visitas=0, gasto_total=0)); db.session.commit()
        return redirect('/clientes')
    clientes=Cliente.query.order_by(Cliente.gasto_total.desc()).all()
    return render_template_string(STYLE+nav()+"""
    <div class="container mt-4"><div class="row"><div class="col-md-4"><div class="card"><h5 style="color:#00ffaa">👤 Nuevo Cliente</h5><form method="POST" class="mt-3"><input name="nombre" class="form-control mb-3" placeholder="Nombre" required><input name="telefono" class="form-control mb-3" placeholder="WhatsApp 10 dígitos" required><button class="btn-rosa w-100" style="background:#00ffaa;color:black">Guardar Cliente</button></form></div></div>
    <div class="col-md-8"><div class="card"><h5>Clientes Frecuentes ({{clientes|length}})</h5><table class="table table-dark table-bordered mt-3"><tr><th>Nombre</th><th>Tel</th><th>Visitas</th><th>Gastado</th><th>Acción</th></tr>
    {% for c in clientes %}<tr><td>{{c.nombre}}</td><td>{{c.telefono}}</td><td>{{c.visitas}}</td><td>${{c.gasto_total}}</td><td><a href="https://wa.me/52{{c.telefono}}?text={{'Hola '+c.nombre+'! 🐖 Ruve te saluda'}}" target="_blank" class="btn-whats">WA</a></td></tr>{% endfor %}</table></div></div></div></div>
    """, clientes=clientes)

@app.route('/reservas', methods=['GET','POST'])
def reservas_view():
    if 'user' not in session: return redirect('/')
    chk=check_mod('mod_reservas');
    if chk: return chk
    mesas=Mesa.query.all()
    if request.method=='POST':
        r=Reserva(cliente_nombre=request.form['cliente_nombre'], telefono=request.form['telefono'], fecha=request.form['fecha'], hora=request.form['hora'], personas=int(request.form['personas']), mesa_id=int(request.form['mesa_id']) if request.form['mesa_id'] else None, estado="pendiente")
        db.session.add(r); db.session.commit(); return redirect('/reservas')
    reservas=Reserva.query.order_by(Reserva.fecha.desc()).all()
    return render_template_string(STYLE+nav()+"""
    <div class="container mt-4"><div class="row"><div class="col-md-4"><div class="card"><h5 style="color:#aa88ff">📅 Nueva Reserva</h5><form method="POST" class="mt-3"><input name="cliente_nombre" class="form-control mb-2" placeholder="Cliente" required list="cli"><datalist id="cli">{% for c in clientes %}<option value="{{c.nombre}}">{% endfor %}</datalist>
    <input name="telefono" class="form-control mb-2" placeholder="Tel" required><input name="fecha" type="date" class="form-control mb-2" required><input name="hora" type="time" class="form-control mb-2" required><input name="personas" type="number" class="form-control mb-2" placeholder="Personas" required><select name="mesa_id" class="form-control mb-3"><option value="">Mesa automática</option>{% for m in mesas %}<option value="{{m.id}}">{{m.nombre}} ({{m.estado}})</option>{% endfor %}</select><button class="btn-rosa w-100" style="background:#aa88ff;color:black">Guardar Reserva</button></form></div></div>
    <div class="col-md-8"><div class="card"><h5>Reservas</h5><table class="table table-dark mt-3"><tr><th>Cliente</th><th>Fecha</th><th>Hora</th><th>Pers</th><th>Mesa</th><th>Estado</th></tr>
    {% for r in reservas %}<tr><td>{{r.cliente_nombre}}<br><small>{{r.telefono}}</small></td><td>{{r.fecha}}</td><td>{{r.hora}}</td><td>{{r.personas}}</td><td>{{r.mesa.nombre if r.mesa else 'Auto'}}</td><td><span style="color:#ffcc00">{{r.estado}}</span> <a href="/reserva/confirmar/{{r.id}}" style="color:#25D366">✓</a> <a href="/reserva/cancelar/{{r.id}}" style="color:red">X</a></td></tr>{% endfor %}</table></div></div></div></div>
    """, reservas=reservas, mesas=mesas, clientes=Cliente.query.all())

@app.route('/reserva/confirmar/<int:id>')
def reserva_confirmar(id):
    r=Reserva.query.get(id); r.estado='confirmada'; db.session.commit(); return redirect('/reservas')
@app.route('/reserva/cancelar/<int:id>')
def reserva_cancelar(id):
    r=Reserva.query.get(id); r.estado='cancelada'; db.session.commit(); return redirect('/reservas')

@app.route('/para_llevar', methods=['GET','POST'])
def para_llevar_view():
    if 'user' not in session: return redirect('/')
    chk=check_mod('mod_llevar');
    if chk: return chk
    productos=Producto.query.all()
    if request.method=='POST':
        prod=Producto.query.get(int(request.form['producto_id'])); cant=int(request.form['cantidad'])
        total=prod.precio*cant; costo=(prod.costo or 0)*cant
        p=PedidoLlevar(cliente_nombre=request.form['cliente_nombre'], telefono=request.form['telefono'], producto_nombre=prod.nombre, cantidad=cant, total=total, tipo=request.form['tipo'], direccion=request.form.get('direccion',''), estado='cocina', vendedor=session.get('user'), costo_total=costo)
        prod.stock-=cant
        db.session.add(p); db.session.commit()
        cli=Cliente.query.filter_by(nombre=request.form['cliente_nombre']).first()
        if not cli:
            cli=Cliente(nombre=request.form['cliente_nombre'], telefono=request.form['telefono'], visitas=0, gasto_total=0)
            db.session.add(cli)
        cli.visitas+=1; cli.gasto_total+=total; cli.ultima_visita=datetime.utcnow(); db.session.commit()
        return redirect('/para_llevar')
    pedidos=PedidoLlevar.query.order_by(PedidoLlevar.fecha.desc()).limit(30).all()
    return render_template_string(STYLE+nav()+"""
    <div class="container mt-4"><div class="row"><div class="col-md-4"><div class="card"><h5 style="color:#ffaa00">🛵 Nuevo Pedido Para Llevar</h5><form method="POST" class="mt-3">
    <input name="cliente_nombre" class="form-control mb-2" placeholder="Cliente" required list="cli2"><datalist id="cli2">{% for c in clientes %}<option value="{{c.nombre}}">{% endfor %}</datalist>
    <input name="telefono" class="form-control mb-2" placeholder="Tel WhatsApp" required><select name="producto_id" class="form-control mb-2" required>{% for p in productos %}<option value="{{p.id}}">{{p.nombre}} - ${{p.precio}}</option>{% endfor %}</select>
    <input name="cantidad" type="number" value="1" min="1" class="form-control mb-2" required><select name="tipo" class="form-control mb-2"><option value="llevar">Cliente recoge</option><option value="domicilio">Envío a domicilio</option></select>
    <textarea name="direccion" class="form-control mb-3" placeholder="Dirección si es domicilio"></textarea><button class="btn-rosa w-100" style="background:#ffaa00;color:black">🍽️ MANDAR A COCINA</button></form></div></div>
    <div class="col-md-8"><div class="card"><h5>Pedidos Para Llevar ({{pedidos|length}})</h5><table class="table table-dark mt-3"><tr><th>Cliente</th><th>Pedido</th><th>Tipo</th><th>Estado</th><th>Acción</th></tr>
    {% for p in pedidos %}<tr><td>{{p.cliente_nombre}}<br><small>{{p.telefono}}</small></td><td>{{p.cantidad}}x {{p.producto_nombre}} - ${{p.total}}</td><td>{{p.tipo}}</td><td style="color:{% if p.estado=='cocina' %}#ff4d3a{% else %}#25D366{% endif %}">{{p.estado}}</td><td>{% if p.estado!='entregado' %}<a href="/llevar/cobrar/{{p.id}}" class="btn-rosa" style="font-size:11px">COBRAR</a>{% endif %}</td></tr>{% endfor %}</table></div></div></div></div>
    """, productos=productos, pedidos=pedidos, clientes=Cliente.query.all())

@app.route('/llevar/listo/<int:id>')
def llevar_listo(id):
    p=PedidoLlevar.query.get(id); p.estado='listo'; db.session.commit(); return redirect('/cocina')
@app.route('/llevar/cobrar/<int:id>')
def llevar_cobrar(id):
    p=PedidoLlevar.query.get(id)
    v=Venta(cliente=p.cliente_nombre+f" ({p.tipo})", producto_nombre=p.producto_nombre, cantidad=p.cantidad, total=p.total, vendedor=session.get('user'), costo_total=p.costo_total)
    db.session.add(v); p.estado='entregado'; db.session.commit()
    return redirect('/para_llevar')

# --- FASE 4 DUEÑO ---
@app.route('/dueno', methods=['GET','POST'])
def dueno_dashboard():
    if 'user' not in session: return redirect('/')
    if not session.get('is_admin'): return redirect('/dashboard')
    chk=check_mod('mod_dueno')
    if chk: return chk
    hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    if request.method=='POST':
        g=Gasto(concepto=request.form['concepto'], monto=float(request.form['monto']), categoria=request.form['categoria'], usuario=session.get('user'))
        db.session.add(g); db.session.commit(); return redirect('/dueno')
    ventas_hoy=Venta.query.filter(Venta.fecha>=hoy).all()
    gastos_hoy=Gasto.query.filter(Gasto.fecha>=hoy).all()
    total_ventas=sum([v.total for v in ventas_hoy])
    total_costos=sum([v.costo_total or 0 for v in ventas_hoy])
    total_gastos=sum([g.monto for g in gastos_hoy])
    ganancia_bruta=total_ventas-total_costos
    ganancia_neta=ganancia_bruta-total_gastos
    margen = (ganancia_bruta/total_ventas*100) if total_ventas>0 else 0
    # Top productos
    por_prod=defaultdict(lambda: {'cant':0,'venta':0,'costo':0})
    for v in ventas_hoy:
        por_prod[v.producto_nombre]['cant']+=v.cantidad
        por_prod[v.producto_nombre]['venta']+=v.total
        por_prod[v.producto_nombre]['costo']+=v.costo_total or 0
    top = sorted(por_prod.items(), key=lambda x: x[1]['venta'], reverse=True)
    return render_template_string(STYLE+nav()+"""
    <div class="container mt-4">
    <div class="card" style="border-color:#ff4d8a"><h3 style="color:#ff4d8a">💰 Dashboard del Dueño - Hoy {{hoy.strftime('%d/%m/%Y')}}</h3>
    <div class="row g-3 mt-3">
        <div class="col-md-3"><div class="card" style="background:#0a1a0a;border-color:#00e5ff"><h6 style="color:#00e5ff">VENTAS HOY</h6><h2>${{total_ventas}}</h2><small>{{ventas_hoy|length}} tickets</small></div></div>
        <div class="col-md-3"><div class="card" style="background:#1a0a0a;border-color:#ff4d3a"><h6 style="color:#ff4d3a">COSTO PRODUCTOS</h6><h2>${{total_costos}}</h2><small>Lo que te costó</small></div></div>
        <div class="col-md-3"><div class="card" style="background:#1a1a0a;border-color:#ffcc00"><h6 style="color:#ffcc00">GASTOS OPERATIVOS</h6><h2>${{total_gastos}}</h2><small>Renta, gas, etc</small></div></div>
        <div class="col-md-3"><div class="card" style="background:#0a1a0f;border-color:#25D366"><h6 style="color:#25D366">GANANCIA NETA HOY</h6><h2 style="color:#25D366">${{ganancia_neta}}</h2><small>Margen {{'%.1f'|format(margen)}}%</small></div></div>
    </div>
    </div>

    <div class="row mt-4">
        <div class="col-md-8"><div class="card"><h5 style="color:#00e5ff">📊 Ventas por Producto Hoy (Ganancia Bruta)</h5><table class="table table-dark mt-3"><tr><th>Producto</th><th>Cant</th><th>Ventas</th><th>Costo</th><th>Ganancia</th><th>Margen</th></tr>
        {% for nombre, d in top %}<tr><td>{{nombre}}</td><td>{{d.cant}}</td><td>${{d.venta}}</td><td>${{d.costo}}</td><td style="color:#25D366">${{d.venta-d.costo}}</td><td>{{'%.0f'|format((d.venta-d.costo)/d.venta*100 if d.venta>0 else 0)}}%</td></tr>{% endfor %}</table></div></div>
        <div class="col-md-4"><div class="card" style="border-color:#ffcc00"><h5 style="color:#ffcc00">💸 Registrar Gasto de Hoy</h5><form method="POST" class="mt-3"><input name="concepto" class="form-control mb-2" placeholder="Concepto Ej: Gas LP" required><input name="monto" type="number" step="0.01" class="form-control mb-2" placeholder="Monto $" required>
        <select name="categoria" class="form-control mb-3"><option value="insumos">Insumos</option><option value="gas">Gas</option><option value="renta">Renta</option><option value="personal">Personal</option><option value="general">General</option></select><button class="btn-rosa w-100" style="background:#ffcc00;color:black">Agregar Gasto</button></form>
        <table class="table table-dark mt-3"><tr><th>Concepto</th><th>Monto</th><th></th></tr>{% for g in gastos_hoy %}<tr><td>{{g.concepto}}<br><small style="color:#aaa">{{g.categoria}}</small></td><td>${{g.monto}}</td><td><a href="/gasto/eliminar/{{g.id}}" style="color:red">X</a></td></tr>{% endfor %}</table>
        {% if gastos_hoy %}<p style="color:#ffcc00">Total gastos hoy: ${{total_gastos}}</p>{% endif %}
        </div></div>
    </div>
    </div>
    """, total_ventas=total_ventas, total_costos=total_costos, total_gastos=total_gastos, ganancia_bruta=ganancia_bruta, ganancia_neta=ganancia_neta, margen=margen, ventas_hoy=ventas_hoy, gastos_hoy=gastos_hoy, top=top, hoy=datetime.now())

@app.route('/gasto/eliminar/<int:id>')
def gasto_eliminar(id):
    if not session.get('is_admin'): return redirect('/dashboard')
    g=Gasto.query.get(id); db.session.delete(g); db.session.commit(); return redirect('/dueno')

@app.route('/vender', methods=['POST'])
def vender():
    if 'user' not in session: return redirect('/')
    cfg=get_config(); prod=Producto.query.get(int(request.form['producto_id']))
    cliente_nombre=(request.form.get('cliente') or "Mostrador").strip() or "Mostrador"
    costo=(prod.costo or 0)*int(request.form['cantidad'])
    v=Venta(cliente=cliente_nombre, producto_nombre=prod.nombre, cantidad=int(request.form['cantidad']), total=prod.precio*int(request.form['cantidad']), vendedor=session.get('user'), costo_total=costo)
    prod.stock = prod.stock - v.cantidad
    db.session.add(v); db.session.commit()
    cli=Cliente.query.filter_by(nombre=cliente_nombre).first()
    if not cli:
        cli=Cliente(nombre=cliente_nombre, telefono="", visitas=0, gasto_total=0)
        db.session.add(cli)
    cli.visitas+=1; cli.gasto_total+=v.total; cli.ultima_visita=datetime.utcnow(); db.session.commit()
    if cfg.tickets: return redirect(f'/ticket/{v.id}')
    return redirect('/dashboard')

@app.route('/ticket/<int:id>')
def ticket(id):
    if 'user' not in session: return redirect('/')
    cfg=get_config();
    if not cfg.tickets: return redirect('/dashboard')
    v=Venta.query.get(id)
    if not session.get('is_admin') and v.vendedor!= session.get('user'): return redirect('/dashboard')
    msj=make_whats_msg(v)
    ganancia=v.total-(v.costo_total or 0)
    return render_template_string(STYLE+f'<div class="container" style="max-width:380px;margin-top:20px"><div class="card" style="background:white;color:black;border:2px dashed black"><div class="text-center"><img src="/static/logo.png?v=ruve3" style="width:110px"><h5 style="font-weight:bold">LECHÓN AL HORNO RUVE</h5><small>Vend: {v.vendedor}</small></div><hr style="border-top:1px dashed black"><p><b>Ticket #{v.id}</b><br>Cliente: {v.cliente}<br>Vendedor: {v.vendedor}<br>Fecha: {v.fecha.strftime("%d/%m/%Y %H:%M")}<br>Producto: {v.producto_nombre}<br>Cant: {v.cantidad}<br><b>Total: ${v.total}</b><br><small style="color:#666">{"Ganancia: $"+str(ganancia) if session.get("is_admin") else ""}</small></p><div class="text-center no-print"><button onclick="window.print()" class="btn-rosa">🖨️ IMPRIMIR</button>'+(f'<a href="https://wa.me/?text={msj}" target="_blank" class="btn-whats ms-2 p-2">📲 WA</a>' if cfg.whatsapp_btn else '')+f'<a href="/dashboard" class="btn btn-dark ms-2">Volver</a></div></div></div>')

@app.route('/productos', methods=['GET','POST'])
def productos_route():
    if 'user' not in session: return redirect('/')
    if not session.get('is_admin'): return redirect('/dashboard')
    if request.method=='POST':
        db.session.add(Producto(nombre=request.form['nombre'], precio=float(request.form['precio']), stock=int(request.form['stock']), costo=float(request.form.get('costo',0)))); db.session.commit(); return redirect('/productos')
    return render_template_string(STYLE+nav()+"""<div class="container mt-4"><div class="card"><h5>Productos (Solo Admin) - Ahora con Costo</h5><form method="POST" class="row g-2 mt-2"><div class="col-md-3"><input name="nombre" class="form-control" placeholder="Nombre" required></div><div class="col-md-2"><input name="precio" type="number" step="0.01" class="form-control" placeholder="Precio Venta" required></div><div class="col-md-2"><input name="costo" type="number" step="0.01" class="form-control" placeholder="Costo" required value="0"></div><div class="col-md-2"><input name="stock" type="number" class="form-control" placeholder="Stock" required></div><div class="col-md-3"><button class="btn-rosa w-100">Agregar</button></div></form>
    <table class="table table-dark table-bordered mt-4"><tr><th>Nombre</th><th>Venta</th><th>Costo</th><th>Ganancia</th><th>Margen</th><th>Stock</th><th></th></tr>
    {% for p in productos %}<tr><td>{{p.nombre}}</td><td>${{p.precio}}</td><td>${{p.costo}}</td><td style="color:#25D366">${{p.precio-p.costo}}</td><td>{{'%.0f'|format((p.precio-p.costo)/p.precio*100 if p.precio>0 else 0)}}%</td><td style="{% if p.stock <= 3 %}color:#ffcc00;font-weight:bold{% endif %}">{{p.stock}}</td><td><a href="/eliminar_producto/{{p.id}}" style="color:red">X</a> <a href="/producto/editar/{{p.id}}" style="color:#00e5ff">Editar</a></td></tr>{% endfor %}</table></div></div>""", productos=Producto.query.all())

@app.route('/producto/editar/<int:id>', methods=['GET','POST'])
def producto_editar(id):
    if not session.get('is_admin'): return redirect('/dashboard')
    p=Producto.query.get(id)
    if request.method=='POST':
        p.nombre=request.form['nombre']; p.precio=float(request.form['precio']); p.costo=float(request.form.get('costo',0)); p.stock=int(request.form['stock']); db.session.commit(); return redirect('/productos')
    return render_template_string(STYLE+nav()+"""<div class="container mt-4" style="max-width:600px"><div class="card"><h5>Editar Producto</h5><form method="POST" class="mt-3"><input name="nombre" class="form-control mb-3" value="{{p.nombre}}" required><div class="row"><div class="col-md-6"><label>Precio Venta</label><input name="precio" type="number" step="0.01" class="form-control mb-3" value="{{p.precio}}" required></div><div class="col-md-6"><label>Costo</label><input name="costo" type="number" step="0.01" class="form-control mb-3" value="{{p.costo}}" required></div></div><label>Stock</label><input name="stock" type="number" class="form-control mb-3" value="{{p.stock}}" required><button class="btn-rosa w-100">Guardar</button></form></div></div>""", p=p)

@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):
    if not session.get('is_admin'): return redirect('/dashboard')
    p=Producto.query.get(id)
    if p: db.session.delete(p); db.session.commit()
    return redirect('/productos')

@app.route('/ventas')
def ventas_route():
    if 'user' not in session: return redirect('/')
    cfg=get_config()
    if session.get('is_admin'): ventas=Venta.query.order_by(Venta.id.desc()).all()
    else: ventas=Venta.query.filter_by(vendedor=session.get('user')).order_by(Venta.id.desc()).all()
    for v in ventas: v.msj=make_whats_msg(v)
    return render_template_string(STYLE+nav()+"""
    <div class="container mt-4"><div class="card"><h5>{% if is_admin %}Historial Completo - Total: ${{total}}{% else %}Mi Historial - Total: ${{total}}{% endif %} {% if is_admin %}<small style="color:#25D366">(Ganancia: ${{ganancia}})</small>{% endif %}</h5>
    <table class="table table-dark table-bordered mt-3"><tr><th>Cliente</th><th>Producto</th><th>Total</th>{% if is_admin %}<th>Costo</th><th>Ganancia</th><th>Vendedor</th>{% endif %}<th>Acciones</th></tr>
    {% for v in ventas %}<tr><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td>{% if is_admin %}<td>${{v.costo_total or 0}}</td><td style="color:#25D366">${{v.total - (v.costo_total or 0)}}</td><td>{{v.vendedor}}</td>{% endif %}<td>{% if cfg.tickets %}<a href="/ticket/{{v.id}}" class="btn-rosa" style="font-size:11px">TICKET</a>{% endif %}{% if cfg.whatsapp_btn %}<a href="https://wa.me/?text={{v.msj}}" target="_blank" class="btn-whats ms-1">WA</a>{% endif %}</td></tr>{% endfor %}</table></div></div>
    """, ventas=ventas, total=sum([v.total for v in ventas]), ganancia=sum([v.total-(v.costo_total or 0) for v in ventas]), cfg=cfg, is_admin=session.get('is_admin'))

@app.route('/reporte')
def reporte():
    if 'user' not in session: return redirect('/')
    cfg=get_config(); hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    if session.get('is_admin'): ventas_hoy=Venta.query.filter(Venta.fecha>=hoy).order_by(Venta.fecha.desc()).all()
    else: ventas_hoy=Venta.query.filter(Venta.fecha>=hoy, Venta.vendedor==session.get('user')).order_by(Venta.fecha.desc()).all()
    total_hoy=sum([v.total for v in ventas_hoy]); total_costo=sum([v.costo_total or 0 for v in ventas_hoy])
    por_vendedor=defaultdict(list)
    for v in ventas_hoy: por_vendedor[v.vendedor].append(v)
    cierre=[];
    for vend, vs in por_vendedor.items(): cierre.append({'vendedor':vend, 'total':sum([x.total for x in vs]), 'costo':sum([x.costo_total or 0 for x in vs]), 'ganancia':sum([x.total-(x.costo_total or 0) for x in vs]), 'cantidad':len(vs)})
    cierre=sorted(cierre, key=lambda x: x['total'], reverse=True)
    msg=f"📊 CIERRE RUVE {datetime.now().strftime('%d/%m')} Total: ${total_hoy} - Costo: ${total_costo} - Ganancia: ${total_hoy-total_costo} - {len(ventas_hoy)} ventas. "
    for c in cierre: msg+=f" {c['vendedor']}: ${c['total']} ({c['cantidad']}) |"
    msg_enc=urllib.parse.quote(msg)
    return render_template_string(STYLE+nav()+"""
    <div class="container mt-4"><div class="card"><h4>{% if is_admin %}Total Hoy (Todos):{% else %}Mi Total Hoy:{% endif %} <span style="color:#25D366">${{total_hoy}}</span> ({{ventas_hoy|length}} ventas) {% if is_admin %}<small style="color:#aaa">Costo ${{total_costo}} | Ganancia ${{total_hoy-total_costo}}</small>{% endif %}</h4>
    <div class="no-print mt-3"><button onclick="window.print()" class="btn-rosa me-2">🖨️ IMPRIMIR</button>{% if cfg.reporte_pdf %}<a href="/reporte_pdf" class="btn btn-light me-2">📄 PDF</a>{% endif %}{% if cfg.total_whatsapp and is_admin %}<a href="https://wa.me/{{cfg.numero_whatsapp}}?text={{msg_enc}}" target="_blank" class="btn-whats p-2">📲 Mandar CIERRE a mi WhatsApp</a>{% endif %}{% if is_admin %}<a href="/dueno" class="btn-rosa ms-2" style="background:#ff4d8a">💰 Ver Ganancia Neta</a>{% endif %}</div></div>
    {% if is_admin %}<div class="card mt-4" style="border-color:#ffcc00"><h5 style="color:#ffcc00">💰 CIERRE POR VENDEDOR - HOY</h5><div class="row mt-3">{% for c in cierre %}<div class="col-md-4 mb-3"><div class="card" style="border-color:#ffcc00;background:#1a1a0a"><h6 style="color:#ffcc00">{{c.vendedor}}</h6><h3>${{c.total}}</h3><small style="color:#aaa">Costo ${{c.costo}} | Ganancia </small><small style="color:#25D366">${{c.ganancia}}</small><br><small>{{c.cantidad}} ventas</small></div></div>{% endfor %}</div>{% if not cierre %}<p style="color:#666">Aún no hay ventas hoy</p>{% endif %}</div>{% endif %}
    <div class="card mt-4"><h5>{% if is_admin %}Detalle Completo{% else %}Mi Detalle de Hoy{% endif %}</h5><table class="table table-dark table-bordered mt-3"><tr><th>Hora</th><th>Cliente</th><th>Producto</th><th>Total</th>{% if is_admin %}<th>Ganancia</th><th>Vendedor</th>{% endif %}</tr>
    {% for v in ventas_hoy %}<tr><td>{{v.fecha.strftime('%H:%M')}}</td><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td>{% if is_admin %}<td style="color:#25D366">${{v.total-(v.costo_total or 0)}}</td><td><b style="color:#ffcc00">{{v.vendedor}}</b></td>{% endif %}</tr>{% endfor %}</table></div></div>
    """, ventas_hoy=ventas_hoy, total_hoy=total_hoy, total_costo=total_costo, cfg=cfg, msg_enc=msg_enc, cierre=cierre, is_admin=session.get('is_admin'))

@app.route('/reporte_pdf')
def reporte_pdf():
    if 'user' not in session: return redirect('/')
    cfg=get_config()
    if not cfg.reporte_pdf: return redirect('/reporte')
    hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    if session.get('is_admin'): ventas=Venta.query.filter(Venta.fecha>=hoy).all()
    else: ventas=Venta.query.filter(Venta.fecha>=hoy, Venta.vendedor==session.get('user')).all()
    total=sum([v.total for v in ventas])
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    buffer=io.BytesIO(); c=canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 16); c.drawString(50,750,f"RUVE - {'COMPLETO' if session.get('is_admin') else 'MI REPORTE'} - {session.get('user')}")
    c.setFont("Helvetica", 12); c.drawString(50,730,f"Fecha: {datetime.now().strftime('%d/%m/%Y')} - Total: ${total} - Ventas: {len(ventas)}"); y=700
    for v in ventas:
        c.drawString(50,y,f"{v.fecha.strftime('%H:%M')} - {v.cliente} - {v.cantidad}x {v.producto_nombre} - ${v.total} {('- '+v.vendedor) if session.get('is_admin') else ''}"); y-=20
        if y<50: c.showPage(); y=750
    c.save(); buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"reporte_{session.get('user')}_{datetime.now().strftime('%d%m%Y')}.pdf", mimetype='application/pdf')

@app.route('/admin/config', methods=['GET','POST'])
def admin_config():
    chk=admin_required()
    if chk: return chk
    cfg=get_config()
    if request.method=='POST':
        cfg.whatsapp_btn = 'whatsapp_btn' in request.form; cfg.tickets = 'tickets' in request.form; cfg.reporte_pdf = 'reporte_pdf' in request.form; cfg.total_whatsapp = 'total_whatsapp' in request.form
        cfg.mod_mesas = 'mod_mesas' in request.form; cfg.mod_cocina = 'mod_cocina' in request.form; cfg.mod_clientes = 'mod_clientes' in request.form; cfg.mod_reservas = 'mod_reservas' in request.form; cfg.mod_llevar = 'mod_llevar' in request.form; cfg.mod_dueno = 'mod_dueno' in request.form
        cfg.numero_whatsapp = request.form.get('numero_whatsapp','').strip() or cfg.numero_whatsapp; db.session.commit(); return redirect('/admin/config')
    return render_template_string(STYLE+nav()+"""<div class="container mt-4" style="max-width:700px"><div class="card"><h4 style="color:#ff4d8a">⚙️ Configuración Admin</h4>
    <h6 class="mt-4" style="color:#aaa">FUNCIONES GENERALES</h6>
    <form method="POST" class="mt-2">
    <label style="display:flex;align-items:center;border:2px solid #333;border-radius:12px;padding:12px;margin-bottom:10px;cursor:pointer;background:#0a0a0a"><input type="checkbox" name="whatsapp_btn" style="width:24px;height:24px;accent-color:#ff4d8a" {{'checked' if cfg.whatsapp_btn}}><span style="margin-left:12px"><b>📲 Botón WhatsApp</b></span></label>
    <label style="display:flex;align-items:center;border:2px solid #333;border-radius:12px;padding:12px;margin-bottom:10px;cursor:pointer;background:#0a0a0a"><input type="checkbox" name="tickets" style="width:24px;height:24px;accent-color:#ff4d8a" {{'checked' if cfg.tickets}}><span style="margin-left:12px"><b>🎫 Tickets</b></span></label>
    <label style="display:flex;align-items:center;border:2px solid #333;border-radius:12px;padding:12px;margin-bottom:10px;cursor:pointer;background:#0a0a0a"><input type="checkbox" name="reporte_pdf" style="width:24px;height:24px;accent-color:#ff4d8a" {{'checked' if cfg.reporte_pdf}}><span style="margin-left:12px"><b>📄 Reporte PDF</b></span></label>
    <label style="display:flex;align-items:center;border:2px solid #333;border-radius:12px;padding:12px;margin-bottom:15px;cursor:pointer;background:#0a0a0a"><input type="checkbox" name="total_whatsapp" style="width:24px;height:24px;accent-color:#ff4d8a" {{'checked' if cfg.total_whatsapp}}><span style="margin-left:12px"><b>💰 Total a mi WhatsApp</b></span></label>

    <h6 class="mt-4" style="color:#00e5ff">MÓDULOS - Prender / Apagar</h6>
    <label style="display:flex;align-items:center;border:2px solid #00e5ff;border-radius:12px;padding:12px;margin-bottom:10px;cursor:pointer;background:#001a1a"><input type="checkbox" name="mod_mesas" style="width:28px;height:28px;accent-color:#00e5ff" {{'checked' if cfg.mod_mesas}}><span style="margin-left:12px"><b>🪑 Mesas</b></span></label>
    <label style="display:flex;align-items:center;border:2px solid #ffcc00;border-radius:12px;padding:12px;margin-bottom:10px;cursor:pointer;background:#1a1a00"><input type="checkbox" name="mod_cocina" style="width:28px;height:28px;accent-color:#ffcc00" {{'checked' if cfg.mod_cocina}}><span style="margin-left:12px"><b>🔥 Cocina KDS</b></span></label>
    <label style="display:flex;align-items:center;border:2px solid #00ffaa;border-radius:12px;padding:12px;margin-bottom:10px;cursor:pointer;background:#001a0f"><input type="checkbox" name="mod_clientes" style="width:28px;height:28px;accent-color:#00ffaa" {{'checked' if cfg.mod_clientes}}><span style="margin-left:12px"><b>👤 Clientes</b></span></label>
    <label style="display:flex;align-items:center;border:2px solid #aa88ff;border-radius:12px;padding:12px;margin-bottom:10px;cursor:pointer;background:#0f0a1a"><input type="checkbox" name="mod_reservas" style="width:28px;height:28px;accent-color:#aa88ff" {{'checked' if cfg.mod_reservas}}><span style="margin-left:12px"><b>📅 Reservas</b></span></label>
    <label style="display:flex;align-items:center;border:2px solid #ffaa00;border-radius:12px;padding:12px;margin-bottom:10px;cursor:pointer;background:#1a1000"><input type="checkbox" name="mod_llevar" style="width:28px;height:28px;accent-color:#ffaa00" {{'checked' if cfg.mod_llevar}}><span style="margin-left:12px"><b>🛵 Para Llevar</b></span></label>
    <label style="display:flex;align-items:center;border:3px solid #ff4d8a;border-radius:12px;padding:12px;margin-bottom:20px;cursor:pointer;background:#1a0010"><input type="checkbox" name="mod_dueno" style="width:28px;height:28px;accent-color:#ff4d8a" {{'checked' if cfg.mod_dueno}}><span style="margin-left:12px"><b>💰 Dashboard Dueño</b> - Costos y Ganancia Neta (solo admin)</span></label>

    <div class="mb-4"><label style="color:#ff4d8a">Tu número WhatsApp:</label><input name="numero_whatsapp" class="form-control mt-2" value="{{cfg.numero_whatsapp}}"></div>
    <button class="btn-rosa w-100" style="padding:14px">💾 GUARDAR CONFIGURACIÓN</button></form></div></div>""", cfg=cfg)

@app.route('/admin/usuarios', methods=['GET','POST'])
def admin_usuarios():
    chk=admin_required()
    if chk: return chk
    if request.method=='POST':
        if User.query.filter_by(username=request.form['username']).first():
            return render_template_string(STYLE+nav()+'<div class="container mt-4"><div class="card"><h5 style="color:red">Ese usuario ya existe</h5><a href="/admin/usuarios" class="btn-rosa">Volver</a></div></div>')
        es_admin = 'is_admin' in request.form; rol = request.form.get('rol','cajero')
        if es_admin: rol='admin'
        db.session.add(User(username=request.form['username'].strip(), password=generate_password_hash(request.form['password']), is_admin=es_admin, rol=rol)); db.session.commit(); return redirect('/admin/usuarios')
    return render_template_string(STYLE+nav()+"""<div class="container mt-4"><div class="row"><div class="col-md-4"><div class="card"><h5 style="color:#ffcc00">👥 Crear Usuario</h5><form method="POST" class="mt-3"><input name="username" class="form-control mb-3" placeholder="Usuario" required><input name="password" class="form-control mb-3" type="text" placeholder="Contraseña" required>
    <select name="rol" class="form-control mb-3"><option value="cajero">Cajero (cobra y factura)</option><option value="mesero">Mesero (toma pedidos)</option><option value="cocina">Personal de Cocina (KDS)</option></select>
    <label style="display:flex;align-items:center;cursor:pointer;margin-bottom:15px"><input type="checkbox" name="is_admin" style="width:20px;height:20px;accent-color:#ff4d8a"> <span style="margin-left:10px">Es administrador / Dueño (acceso total)</span></label><button class="btn-rosa w-100">Crear Usuario</button></form></div></div><div class="col-md-8"><div class="card"><h5>Usuarios Actuales</h5><table class="table table-dark table-bordered mt-3"><tr><th>Usuario</th><th>Rol</th><th>Acción</th></tr>{% for u in usuarios %}<tr><td>{{u.username}}</td><td>{% if u.is_admin %}<span style="color:#25D366">ADMIN / DUEÑO</span>{% else %}{{u.rol|upper}}{% endif %}</td><td>{% if u.username!='admin' %}<a href="/admin/usuarios/eliminar/{{u.id}}" style="color:red" onclick="return confirm('¿Eliminar?')">Eliminar</a>{% else %}<small style="color:#555">No se puede</small>{% endif %}</td></tr>{% endfor %}</table></div></div></div></div>""", usuarios=User.query.all())

@app.route('/admin/usuarios/eliminar/<int:id>')
def eliminar_usuario(id):
    chk=admin_required()
    if chk: return chk
    u=User.query.get(id)
    if u and u.username!='admin': db.session.delete(u); db.session.commit()
    return redirect('/admin/usuarios')

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))