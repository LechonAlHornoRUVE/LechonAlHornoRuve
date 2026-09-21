from flask import Flask, request, redirect, session, render_template_string, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from collections import defaultdict
import os, urllib.parse, io

app = Flask(__name__)
app.secret_key = 'ruve-mesero-edita-ticket'

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
    costo=db.Column(db.Float, default=0)
class Venta(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    cliente=db.Column(db.String(100))
    producto_nombre=db.Column(db.String(100))
    cantidad=db.Column(db.Integer)
    total=db.Column(db.Float)
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    vendedor=db.Column(db.String(80), default="admin")
    costo_total=db.Column(db.Float, default=0)
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
    mod_dueno=db.Column(db.Boolean, default=True)
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
class Gasto(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    concepto=db.Column(db.String(100))
    monto=db.Column(db.Float)
    categoria=db.Column(db.String(50), default="general")
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    usuario=db.Column(db.String(80))

def get_config():
    c=Config.query.first()
    if not c: c=Config(); db.session.add(c); db.session.commit()
    return c

with app.app_context():
    from sqlalchemy import text
    db.create_all()
    try: db.session.execute(text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS rol VARCHAR(20) DEFAULT \'cajero\'')); db.session.commit()
    except: db.session.rollback()
    try: db.session.execute(text('ALTER TABLE producto ADD COLUMN IF NOT EXISTS costo FLOAT DEFAULT 0')); db.session.commit()
    except: db.session.rollback()
    try: db.session.execute(text('ALTER TABLE venta ADD COLUMN IF NOT EXISTS costo_total FLOAT DEFAULT 0')); db.session.commit()
    except: db.session.rollback()
    try: db.session.execute(text('ALTER TABLE pedido_llevar ADD COLUMN IF NOT EXISTS costo_total FLOAT DEFAULT 0')); db.session.commit()
    except: db.session.rollback()
    for col in ['mod_mesas','mod_cocina','mod_clientes','mod_reservas','mod_llevar','mod_dueno']:
        try: db.session.execute(text(f'ALTER TABLE config ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT TRUE')); db.session.commit()
        except: db.session.rollback()
    try:
        admin_u = User.query.filter_by(username='admin').first()
        if not admin_u:
            db.session.add(User(username='admin', password=generate_password_hash('admin123'), is_admin=True, rol="admin")); db.session.commit()
        else:
            admin_u.is_admin=True; admin_u.rol="admin"; db.session.commit()
    except: db.session.rollback()
    get_config()
    if Producto.query.count()==0:
        db.session.add_all([Producto(nombre='Lechón por Kilo', precio=350, stock=50, costo=180), Producto(nombre='Lechón Entero', precio=3500, stock=5, costo=1800), Producto(nombre='Torta de Lechón', precio=70, stock=30, costo=35), Producto(nombre='Orden Lechón', precio=120, stock=20, costo=60), Producto(nombre='Refresco', precio=25, stock=100, costo=12), Producto(nombre='Salsa Extra', precio=15, stock=50, costo=5)]); db.session.commit()
    if Mesa.query.count()==0:
        for i in range(1,13):
            db.session.add(Mesa(nombre=f"Mesa {i}", estado="libre", total=0))
        db.session.commit()

STYLE_BASE = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#000;color:white;font-family:Arial}
.card{background:#111;border:2px solid #ff4d8a;border-radius:15px;padding:20px}
.btn-rosa{background:#ff4d8a;color:white;border:none;padding:10px 18px;border-radius:10px;font-weight:bold}
.navbar{background:#000!important;border-bottom:2px solid #ff4d8a}
input,select{background:#222!important;color:white!important;border:1px solid #ff4d8a!important}
textarea{background:#222!important;color:white!important;border:1px solid #ff4d8a!important}
a{color:#ff4d8a;text-decoration:none}
@media print{.no-print{display:none} body{background:white;color:black}}
.pos-container{display:flex;height:calc(100vh - 70px);gap:10px;padding:10px}
.pos-left{width:38%;background:#0f0f0f;border:2px solid #ff4d8a;border-radius:15px;display:flex;flex-direction:column}
.pos-center{width:12%;display:flex;flex-direction:column;gap:8px}
.pos-right{width:50%;background:#0f0f0f;border:2px solid #333;border-radius:15px;padding:10px;overflow-y:auto}
.cat-btn{background:#222;color:white;font-weight:bold;padding:14px;border:2px solid #333;border-radius:8px;cursor:pointer;text-align:center}
.cat-btn.active{background:#ff4d8a;color:white;border-color:#ff4d8a}
.prod-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.prod-card{background:#1a1a1a;border:2px solid #333;border-radius:12px;padding:10px;text-align:center;cursor:pointer}
.prod-card:hover{border-color:#ff4d8a}
.prod-card img{width:70px;height:70px;object-fit:cover;border-radius:10px;background:white;padding:5px}
.prod-card h6{color:#ff4d8a;margin:8px 0 2px 0;font-size:13px;font-weight:bold}
.ticket-header{background:#111;padding:12px;border-bottom:2px solid #ff4d8a;border-radius:15px 15px 0 0}
.ticket-body{flex:1;overflow-y:auto;padding:10px;background:white;color:black}
.ticket-footer{background:#111;padding:12px;border-top:2px solid #ff4d8a}
.ticket-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px dashed #ccc;font-size:13px}
.btn-cash{background:#25D366;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:48%}
.btn-pay{background:#3f51b5;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:48%}
.btn-suspend{background:#ff9800;color:black;font-weight:bold;padding:10px;border:none;border-radius:8px;width:100%;margin-top:8px}
.qty-btn{border:none;background:#ff4d8a;color:white;border-radius:5px;padding:2px 8px;font-weight:bold}
.qty-btn.minus{background:#555}
</style>
"""

def nav():
    cfg=get_config(); rol = session.get('rol','cajero'); is_admin = session.get('is_admin', False)
    rol_display = 'ADMIN' if is_admin else rol.upper()
    links=""
    if cfg.mod_mesas and (is_admin or rol in ['admin','cajero','mesero']): links+= '<a href="/mesas" class="me-3" style="color:#00e5ff">🪑 Mesas</a>'
    if cfg.mod_cocina and (is_admin or rol in ['cocina','admin','cajero']): links+= '<a href="/cocina" class="me-3" style="color:#ffcc00">🔥 Cocina</a>'
    if cfg.mod_clientes and (is_admin or rol in ['admin','cajero','mesero']): links+= '<a href="/clientes" class="me-3" style="color:#00ffaa">👤 Clientes</a>'
    if cfg.mod_reservas and (is_admin or rol in ['admin','cajero','mesero']): links+= '<a href="/reservas" class="me-3" style="color:#aa88ff">📅 Reservas</a>'
    if cfg.mod_llevar and (is_admin or rol in ['admin','cajero','mesero']): links+= '<a href="/para_llevar" class="me-3" style="color:#ffaa00">🛵 Llevar</a>'
    if cfg.mod_dueno and is_admin: links+= '<a href="/dueno" class="me-3" style="color:#ff4d8a;font-weight:bold">💰 Dueño</a>'
    admin_links = f'<a href="/admin/config" class="me-3" style="color:#25D366">⚙️ Config</a><a href="/admin/usuarios" class="me-3" style="color:#ffcc00">👥 Usuarios</a>' if is_admin else ''
    prod_link = '<a href="/productos" class="me-3">Productos</a>' if is_admin else ''
    return f'<nav class="navbar p-3 no-print"><div class="d-flex align-items-center"><img src="/static/logo.png?v=ruve3" style="width:45px;height:45px;border-radius:50%;margin-right:10px;background:white;padding:3px"><h4 style="color:#ff4d8a" class="m-0">Ruve</h4> <small style="color:#aaa;margin-left:10px">{session.get("user")} ({rol_display})</small></div><div><a href="/dashboard" class="me-3">POS</a>{links}{prod_link}<a href="/ventas" class="me-3">Ventas</a><a href="/reporte" class="me-3">Reporte</a>{admin_links}<a href="/logout">Salir</a></div></nav>'

def check_mod(mod_name):
    cfg=get_config()
    if not getattr(cfg, mod_name, True):
        if mod_name=='mod_dueno' and not session.get('is_admin'): return redirect('/dashboard')
        if mod_name!='mod_dueno':
            return render_template_string(STYLE_BASE+nav()+f'<div class="container mt-5"><div class="card text-center"><h3 style="color:#ff4d3a">Módulo Deshabilitado</h3><a href="/dashboard" class="btn-rosa">Volver</a></div></div>')
    return None

def make_whats_msg(v): return urllib.parse.quote(f"Hola {v.cliente}! 🐖 Tu pedido Ruve: {v.cantidad}x {v.producto_nombre} - ${v.total}. Ticket #{v.id}")
def admin_required():
    if 'user' not in session: return redirect('/')
    if not session.get('is_admin'): return redirect('/dashboard')
    return None
def get_categoria(nombre):
    n=nombre.lower()
    if 'lech' in n: return 'lechon'
    if 'torta' in n: return 'tortas'
    if 'orden' in n: return 'ordenes'
    if 'refresco' in n or 'coca' in n or 'bebida' in n or 'agua' in n: return 'bebidas'
    return 'extras'
def get_mesa_carrito(mesa_id):
    key = f'mesa_carrito_{mesa_id}'
    return session.get(key, [])
def set_mesa_carrito(mesa_id, carrito):
    key = f'mesa_carrito_{mesa_id}'
    session[key]=carrito

@app.route('/', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user']=u.username; session['is_admin']=u.is_admin
            if u.is_admin:
                session['rol']='admin'
                if u.rol!= 'admin': u.rol='admin'; db.session.commit()
            else:
                session['rol']=u.rol or 'cajero'
            session['carrito']=[]
            if not u.is_admin and u.rol == 'cocina': return redirect('/cocina')
            if not u.is_admin and u.rol == 'mesero': return redirect('/mesas')
            return redirect('/dashboard')
    return render_template_string(STYLE_BASE+f'<div class="container" style="max-width:420px;margin-top:25px"><div class="card text-center"><img src="/static/logo.png?v=ruve3" style="width:210px;height:210px;object-fit:contain;background:white;border-radius:50%;padding:8px;border:3px solid #ff4d8a;margin:0 auto"><h2 style="color:#ff4d8a" class="mt-3">LechonAlHornoRuve</h2><form method="POST" class="mt-4 text-start"><input name="username" class="form-control mb-3" placeholder="Usuario" required><input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required><button class="btn-rosa w-100">ENTRAR</button></form></div></div>')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    cfg=get_config()
    productos=Producto.query.all()
    for p in productos: p.categoria = get_categoria(p.nombre)
    carrito=session.get('carrito',[])
    total = sum([x['precio']*x['cant'] for x in carrito])
    hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    if session.get('is_admin'):
        ventas = Venta.query.filter(Venta.fecha>=hoy).order_by(Venta.id.desc()).limit(8).all()
        total_hoy = sum([v.total for v in Venta.query.filter(Venta.fecha>=hoy).all()])
    else:
        ventas = Venta.query.filter_by(vendedor=session.get('user')).filter(Venta.fecha>=hoy).order_by(Venta.id.desc()).limit(8).all()
        total_hoy = sum([v.total for v in Venta.query.filter_by(vendedor=session.get('user')).filter(Venta.fecha>=hoy).all()])
    for v in ventas: v.msj=make_whats_msg(v)
    html = STYLE_BASE+nav()+"""
<div class="pos-container no-print">
    <div class="pos-left">
        <div class="ticket-header">
            <div style="display:flex;justify-content:space-between"><small style="color:#aaa">Mesa: Mostrador</small><small style="color:#aaa">{{fecha}} {{hora}}</small></div>
            <div class="d-flex gap-2 mt-2">
                <input id="clienteInput" class="form-control" placeholder="👤 Cliente (Mostrador)" value="{{cliente_actual}}" list="clientes-list">
                <datalist id="clientes-list">{% for c in clientes %}<option value="{{c.nombre}}">{% endfor %}</datalist>
            </div>
        </div>
        <div class="ticket-body">
            <div style="display:flex;justify-content:space-between;font-weight:bold;border-bottom:2px solid black;padding-bottom:5px;font-size:11px"><span style="width:5%">#</span><span style="width:40%">Artículo</span><span style="width:15%">Precio</span><span style="width:20%">Cant</span><span style="width:15%">Total</span><span style="width:5%">X</span></div>
            {% for item in carrito %}
                <div class="ticket-row">
                    <span style="width:5%;color:green">{{loop.index}}</span>
                    <span style="width:40%">{{item.nombre}}</span>
                    <span style="width:15%">${{item.precio}}</span>
                    <span style="width:20%">
                        <button class="qty-btn minus" onclick="window.location='/pos/cant/{{loop.index0}}/-1'">-</button>
                        <b>{{item.cant}}</b>
                        <button class="qty-btn" onclick="window.location='/pos/cant/{{loop.index0}}/1'">+</button>
                    </span>
                    <span style="width:15%">${{item.precio*item.cant}}</span>
                    <span style="width:5%"><a href="/pos/remove/{{loop.index0}}" style="color:red;font-weight:bold">X</a></span>
                </div>
            {% endfor %}
            {% if not carrito %}<p style="color:#888;text-align:center;margin-top:30px">Toca un producto a la derecha para agregar al ticket</p>{% endif %}
        </div>
        <div class="ticket-footer">
            <div style="color:#aaa;font-size:12px">
                <div style="display:flex;justify-content:space-between"><span>Total</span><span>${{total}}</span></div>
                <hr style="border-color:#ff4d8a">
                <div style="display:flex;justify-content:space-between;font-weight:bold;color:white;font-size:18px"><span>Total a Pagar</span><span>${{total}}</span></div>
            </div>
            <div style="display:flex;gap:8px;margin-top:12px">
                <button onclick="pagar('efectivo')" class="btn-cash">💵 Venta Efectivo</button>
                <button onclick="pagar('tarjeta')" class="btn-pay">💳 Cobrar</button>
            </div>
            <button onclick="window.location='/pos/clear'" class="btn-suspend">🗑️ Limpiar Ticket</button>
        </div>
    </div>
    <div class="pos-center">
        <button class="cat-btn active" onclick="filtrar('todos')" id="btn-todos">Todos</button>
        <button class="cat-btn" onclick="filtrar('lechon')" id="btn-lechon">Lechón</button>
        <button class="cat-btn" onclick="filtrar('tortas')" id="btn-tortas">Tortas</button>
        <button class="cat-btn" onclick="filtrar('ordenes')" id="btn-ordenes">Órdenes</button>
        <button class="cat-btn" onclick="filtrar('bebidas')" id="btn-bebidas">Bebidas</button>
        <button class="cat-btn" onclick="filtrar('extras')" id="btn-extras">Extras</button>
        <div style="margin-top:auto;background:#111;border:1px solid #ff4d8a;border-radius:10px;padding:10px">
            <small style="color:#ff4d8a">Ventas Hoy</small><h5>${{total_hoy}}</h5>
            {% for v in ventas %}<div style="font-size:10px;color:#aaa">{{v.cliente}} - ${{v.total}} <a href="/ticket/{{v.id}}" style="color:#ff4d8a">TK</a> {% if is_admin %}<a href="/eliminar_venta/{{v.id}}" style="color:red">🗑️</a>{% endif %}</div>{% endfor %}
        </div>
    </div>
    <div class="pos-right">
        <div class="prod-grid" id="prodGrid">
            {% for p in productos %}
            <div class="prod-card" data-cat="{{p.categoria}}" onclick="window.location='/pos/add/{{p.id}}'">
                <img src="/static/logo.png?v=ruve3" alt="{{p.nombre}}">
                <h6>{{p.nombre}}</h6>
                <small>${{p.precio}} | Stock {{p.stock}}</small>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
<script>
function filtrar(cat){
    document.querySelectorAll('.cat-btn').forEach(b=>b.classList.remove('active'));
    document.getElementById('btn-'+cat).classList.add('active');
    document.querySelectorAll('.prod-card').forEach(card=>{
        if(cat==='todos' || card.dataset.cat===cat){card.style.display='block';} else {card.style.display='none';}
    });
}
function pagar(tipo){
    let cliente = document.getElementById('clienteInput').value || 'Mostrador';
    fetch('/pos/pagar', {method:'POST',headers:{'Content-Type':'application/json'},body: JSON.stringify({cliente: cliente, tipo: tipo})}).then(r=>r.json()).then(data=>{
        if(data.ok){ if(data.ticket_id){ window.location = '/ticket/'+data.ticket_id; } else { window.location = '/dashboard'; } } else { alert(data.error); }
    });
}
</script>
"""
    return render_template_string(html, productos=productos, carrito=carrito, total=total, total_hoy=total_hoy, ventas=ventas, fecha=datetime.now().strftime("%d/%m/%Y"), hora=datetime.now().strftime("%H:%M"), clientes=Cliente.query.all(), cliente_actual=session.get('cliente_actual',''), is_admin=session.get('is_admin'), cfg=cfg)

@app.route('/pos/add/<int:id>')
def pos_add(id):
    if 'user' not in session: return redirect('/')
    prod=Producto.query.get(id)
    if not prod or prod.stock<=0: return redirect('/dashboard')
    carrito=session.get('carrito',[])
    found=False
    for item in carrito:
        if item['id']==prod.id:
            item['cant']+=1; found=True; break
    if not found:
        carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':prod.precio,'costo':prod.costo or 0,'cant':1})
    session['carrito']=carrito
    return redirect('/dashboard')
@app.route('/pos/cant/<int:index>/<int:delta>')
def pos_cant(index, delta):
    carrito=session.get('carrito',[])
    if 0 <= index < len(carrito):
        carrito[index]['cant']+=delta
        if carrito[index]['cant']<=0: carrito.pop(index)
        session['carrito']=carrito
    return redirect('/dashboard')
@app.route('/pos/remove/<int:index>')
def pos_remove(index):
    carrito=session.get('carrito',[])
    if 0 <= index < len(carrito):
        carrito.pop(index); session['carrito']=carrito
    return redirect('/dashboard')
@app.route('/pos/clear')
def pos_clear():
    session['carrito']=[]; return redirect('/dashboard')
@app.route('/pos/pagar', methods=['POST'])
def pos_pagar():
    if 'user' not in session: return jsonify({'ok':False,'error':'No login'})
    data=request.get_json()
    cliente=(data.get('cliente') or 'Mostrador').strip() or 'Mostrador'
    carrito=session.get('carrito',[])
    if not carrito: return jsonify({'ok':False,'error':'Ticket vacío'})
    last_ticket_id=None
    for item in carrito:
        prod=Producto.query.get(item['id'])
        if not prod or prod.stock < item['cant']: return jsonify({'ok':False,'error':f'Sin stock {item["nombre"]}'})
        costo=(prod.costo or 0)*item['cant']
        v=Venta(cliente=cliente, producto_nombre=prod.nombre, cantidad=item['cant'], total=prod.precio*item['cant'], vendedor=session.get('user'), costo_total=costo)
        prod.stock-=item['cant']; db.session.add(v); db.session.flush(); last_ticket_id=v.id
        cli=Cliente.query.filter_by(nombre=cliente).first()
        if not cli:
            cli=Cliente(nombre=cliente, telefono="", visitas=0, gasto_total=0); db.session.add(cli)
        cli.visitas+=1; cli.gasto_total+=v.total; cli.ultima_visita=datetime.utcnow()
    db.session.commit(); session['carrito']=[]; session['cliente_actual']=cliente
    return jsonify({'ok':True,'ticket_id':last_ticket_id})
@app.route('/eliminar_venta/<int:id>')
def eliminar_venta(id):
    if 'user' not in session: return redirect('/')
    if not session.get('is_admin'): return redirect('/dashboard')
    v=Venta.query.get(id)
    if v:
        prod=Producto.query.filter_by(nombre=v.producto_nombre).first()
        if prod: prod.stock = (prod.stock or 0) + v.cantidad
        db.session.delete(v); db.session.commit()
    return redirect(request.referrer or '/ventas')

# --- MESAS VISUAL FOTO + MESERO EDITABLE ---
@app.route('/mesas')
def mesas_view():
    if 'user' not in session: return redirect('/')
    chk=check_mod('mod_mesas')
    if chk: return chk
    mesas = Mesa.query.all()
    for m in mesas:
        if m.estado == 'libre':
            m.estado_label = 'Disponible'
            m.estado_class = 'disponible'
        elif m.estado == 'ocupada':
            m.estado_label = 'Ocupada'
            m.estado_class = 'ocupada'
        else:
            m.estado_label = 'Cerrada'
            m.estado_class = 'cerrada'
    return render_template_string(STYLE_BASE+nav()+"""
<style>
.mesas-wrapper{background:#f5f6f8;min-height:calc(100vh - 70px);padding:0;display:flex}
.mesas-main{flex:1;padding:0}
.mesas-header-top{background:#1e8a3d;padding:8px 12px;display:flex;gap:8px;align-items:center;color:white;flex-wrap:wrap}
.mesas-areas{background:white;padding:10px 12px;display:flex;gap:8px;align-items:center;border-bottom:1px solid #e0e0e0;flex-wrap:wrap}
.area-pill{padding:6px 14px;border-radius:20px;border:1px solid #ddd;background:white;font-size:12px;cursor:pointer;color:#333}
.area-pill.vip{background:#0f2b0f;color:white}
.mesas-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(145px,1fr));gap:14px;padding:14px}
.mesa-card{border-radius:12px;padding:10px;cursor:pointer;min-height:145px;display:flex;flex-direction:column;justify-content:space-between;transition:0.15s;border:2px solid;box-shadow:0 2px 6px rgba(0,0,0,0.08)}
.mesa-card:hover{transform:translateY(-3px)}
.mesa-card.disponible{background:#e8f5e9;border-color:#2e7d32}
.mesa-card.ocupada{background:#fde8e8;border-color:#c62828}
.mesa-card.cerrada{background:#fff3e0;border-color:#ef6c00}
.mesa-top{display:flex;justify-content:space-between;align-items:center;font-size:12px;font-weight:bold;color:#111}
.badge-estado{padding:3px 8px;border-radius:12px;font-size:10px;color:white;font-weight:bold}
.badge-estado.disponible{background:#2e7d32}
.badge-estado.ocupada{background:#c62828}
.badge-estado.cerrada{background:#ef6c00}
.mesa-icon-wrap{display:flex;justify-content:center;margin:10px 0}
.mesa-icon-circle{width:58px;height:58px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;color:white;background:#2e7d32}
.mesa-card.ocupada.mesa-icon-circle{background:#c62828}
.mesa-card.cerrada.mesa-icon-circle{background:#ef6c00}
.mesa-bottom{background:white;border-radius:8px;padding:5px 6px;text-align:center;font-size:11px;color:#333;display:flex;align-items:center;justify-content:center;min-height:26px}
.venta-rapida-bar{width:62px;background:#1e8a3d;color:white;display:flex;align-items:center;justify-content:center;writing-mode:vertical-rl;text-orientation:mixed;font-weight:bold;letter-spacing:3px;font-size:16px;cursor:pointer}
</style>
<div class="mesas-wrapper">
    <div class="mesas-main">
        <div class="mesas-header-top">
            <span style="background:rgba(255,255,255,0.2);padding:5px 10px;border-radius:20px;font-size:12px">🕘 {{hora}}</span>
            <span style="background:#ff6f00;padding:5px 12px;border-radius:20px;font-size:12px">🪑 Salones ✓</span>
            <span style="background:#1565c0;padding:5px 12px;border-radius:20px;font-size:12px">🚚 Delivery</span>
            <span style="margin-left:auto;display:flex;gap:6px">
                <span style="background:white;color:#1e8a3d;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:bold">⊕ Nueva</span>
                <span style="background:#5c6bc0;padding:5px 12px;border-radius:20px;font-size:12px">📋 Menus</span>
                <span style="background:rgba(255,255,255,0.2);padding:5px 12px;border-radius:20px;font-size:12px">💾 Guardar</span>
            </span>
        </div>
        <div class="mesas-areas">
            <span style="background:#e8f5e9;padding:5px 10px;border-radius:6px;font-size:12px;color:#2e7d32;font-weight:bold">📍 Areas</span>
            <span class="area-pill vip">★ VIP</span>
            <span class="area-pill">☕ Sofietje Lobby</span>
            <span class="area-pill" style="background:#0f2b0f;color:white">🏷️ GENERAL ({{mesas|length}})</span>
        </div>
        <div class="mesas-grid">
            {% for m in mesas %}
            <div class="mesa-card {{m.estado_class}}" onclick="window.location='/mesa/{{m.id}}'">
                <div class="mesa-top"><span>{{m.nombre}}</span><span class="badge-estado {{m.estado_class}}">{{m.estado_label}}</span></div>
                <div style="font-size:10px;color:#777;margin-top:3px">{% if m.estado_class == 'ocupada' %}•••• ${{m.total}}{% else %}••• Libre{% endif %}</div>
                <div class="mesa-icon-wrap"><div class="mesa-icon-circle">{% if m.estado_class == 'ocupada' %}🍴{% elif m.estado_class == 'cerrada' %}🔒{% else %}🪑{% endif %}</div></div>
                <div class="mesa-bottom">{% if m.estado_class == 'ocupada' %}👤 {{m.comandas[0].mesero if m.comandas else 'Mesero'}} - ${{m.total}}{% else %}👤 Libre{% endif %}</div>
            </div>
            {% endfor %}
        </div>
    </div>
    <div class="venta-rapida-bar" onclick="window.location='/dashboard'">VENTA RÁPIDA</div>
</div>
""", mesas=mesas, hora=datetime.now().strftime("%H:%M"))

# NUEVO: MESA DETALLE CON TICKET EDITABLE PARA MESERO
@app.route('/mesa/<int:id>')
def mesa_detalle(id):
    if 'user' not in session: return redirect('/')
    chk=check_mod('mod_mesas')
    if chk: return chk
    mesa = Mesa.query.get(id)
    productos = Producto.query.all()
    for p in productos: p.categoria = get_categoria(p.nombre)
    carrito = get_mesa_carrito(id)
    total_nuevo = sum([x['precio']*x['cant'] for x in carrito])
    comandas_activas = [c for c in mesa.comandas if c.estado!= 'entregado']
    total_mesa = mesa.total or 0

    return render_template_string(STYLE_BASE+nav()+"""
<style>
.mesa-detalle-wrap{display:flex;gap:10px;padding:10px;height:calc(100vh - 70px)}
.mesa-left{width:40%;background:#0f0f0f;border:2px solid #00e5ff;border-radius:15px;display:flex;flex-direction:column}
.mesa-center{width:20%;display:flex;flex-direction:column;gap:8px}
.mesa-right{width:40%;background:#0f0f0f;border:2px solid #333;border-radius:15px;padding:10px;overflow-y:auto}
.mesa-ticket-header{background:#111;padding:12px;border-bottom:2px solid #00e5ff;border-radius:15px 15px 0 0}
.mesa-ticket-body{flex:1;overflow-y:auto;padding:10px;background:white;color:black;min-height:200px}
.mesa-ticket-footer{background:#111;padding:12px;border-top:2px solid #00e5ff}
.prod-grid-mesa{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.prod-card-mesa{background:#1a1a1a;border:2px solid #333;border-radius:10px;padding:8px;text-align:center;cursor:pointer}
.prod-card-mesa:hover{border-color:#00e5ff}
</style>
<div class="mesa-detalle-wrap no-print">
    <div class="mesa-left">
        <div class="mesa-ticket-header">
            <h5 style="color:#00e5ff;margin:0">🪑 {{mesa.nombre}} - {{mesa.estado|upper}}</h5>
            <small style="color:#aaa">Total Mesa: ${{total_mesa}} - Mesero: {{session.get('user')}}</small>
            <div style="margin-top:8px">
                <div style="font-weight:bold;color:#00e5ff;font-size:12px">PEDIDOS YA EN COCINA ({{comandas_activas|length}})</div>
                {% for c in comandas_activas %}
                <div style="display:flex;justify-content:space-between;font-size:12px;color:#aaa;border-bottom:1px dashed #333;padding:4px 0">
                    <span>{{c.cantidad}}x {{c.producto_nombre}}</span><span style="color:{% if c.estado=='cocina' %}#ff4d3a{% else %}#25D366{% endif %}">{{c.estado}}</span>
                </div>
                {% endfor %}
                {% if not comandas_activas %}<small style="color:#666">No hay pedidos en cocina aún</small>{% endif %}
            </div>
            <hr style="border-color:#333">
            <div style="font-weight:bold;color:#ffcc00;font-size:13px">🎫 NUEVO TICKET - Editable por mesero</div>
        </div>
        <div class="mesa-ticket-body">
            <div style="display:flex;justify-content:space-between;font-weight:bold;border-bottom:2px solid black;padding-bottom:5px;font-size:11px"><span style="width:40%">Artículo</span><span style="width:15%">Precio</span><span style="width:25%">Cant</span><span style="width:15%">Total</span><span style="width:5%">X</span></div>
            {% for item in carrito %}
            <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px dashed #ccc;font-size:12px">
                <span style="width:40%">{{item.nombre}}</span>
                <span style="width:15%">${{item.precio}}</span>
                <span style="width:25%">
                    <a href="/mesa/{{mesa.id}}/cant/{{loop.index0}}/-1" class="qty-btn minus" style="text-decoration:none">-</a>
                    <b style="margin:0 5px">{{item.cant}}</b>
                    <a href="/mesa/{{mesa.id}}/cant/{{loop.index0}}/1" class="qty-btn" style="text-decoration:none">+</a>
                </span>
                <span style="width:15%">${{item.precio*item.cant}}</span>
                <span style="width:5%"><a href="/mesa/{{mesa.id}}/remove/{{loop.index0}}" style="color:red;font-weight:bold">X</a></span>
            </div>
            {% endfor %}
            {% if not carrito %}<p style="color:#888;text-align:center;margin-top:30px">Toca productos a la derecha.<br>El mesero puede agregar, quitar y modificar cantidad aquí antes de enviar a cocina.</p>{% endif %}
        </div>
        <div class="mesa-ticket-footer">
            <div style="display:flex;justify-content:space-between;color:white;font-weight:bold;font-size:16px"><span>Total Nuevo</span><span>${{total_nuevo}}</span></div>
            <div style="display:flex;gap:8px;margin-top:10px">
                <a href="/mesa/{{mesa.id}}/enviar" class="btn-rosa w-100" style="background:#00e5ff;color:black;text-align:center;text-decoration:none;padding:12px;border-radius:8px;font-weight:bold">🍽️ MANDAR A COCINA ({{carrito|length}} items)</a>
            </div>
            <div style="display:flex;gap:8px;margin-top:8px">
                <a href="/mesa/{{mesa.id}}/clear" style="background:#555;color:white;text-align:center;text-decoration:none;padding:8px;border-radius:8px;width:50%">Limpiar Ticket</a>
                <a href="/mesas" style="background:#222;color:white;text-align:center;text-decoration:none;padding:8px;border-radius:8px;width:50%">Volver Mesas</a>
            </div>
            <a href="/mesa/{{mesa.id}}/cobrar" class="btn-rosa w-100 mt-2" style="background:#25D366;text-align:center;text-decoration:none;display:block">💰 COBRAR Y LIBERAR MESA ${{total_mesa + total_nuevo}}</a>
        </div>
    </div>
    <div class="mesa-center">
        <button class="cat-btn active" onclick="filtrarMesa('todos')" id="mbtn-todos">Todos</button>
        <button class="cat-btn" onclick="filtrarMesa('lechon')" id="mbtn-lechon">Lechón</button>
        <button class="cat-btn" onclick="filtrarMesa('tortas')" id="mbtn-tortas">Tortas</button>
        <button class="cat-btn" onclick="filtrarMesa('ordenes')" id="mbtn-ordenes">Órdenes</button>
        <button class="cat-btn" onclick="filtrarMesa('bebidas')" id="mbtn-bebidas">Bebidas</button>
        <button class="cat-btn" onclick="filtrarMesa('extras')" id="mbtn-extras">Extras</button>
        <div style="margin-top:auto;background:#111;border:1px solid #00e5ff;border-radius:10px;padding:10px">
            <small style="color:#00e5ff">Mesa {{mesa.nombre}}</small><br>
            <small style="color:#aaa">Estado: {{mesa.estado}}</small><br>
            <small style="color:#aaa">Total: ${{total_mesa}}</small><br>
            <small style="color:#aaa">Nuevo: ${{total_nuevo}}</small>
        </div>
    </div>
    <div class="mesa-right">
        <small style="color:#aaa">Toca para agregar al ticket de la mesa - Mesero puede editar antes de enviar</small>
        <div class="prod-grid-mesa" style="margin-top:10px">
            {% for p in productos %}
            <div class="prod-card-mesa" data-cat="{{p.categoria}}" onclick="window.location='/mesa/{{mesa.id}}/add/{{p.id}}'">
                <img src="/static/logo.png?v=ruve3" style="width:50px;height:50px;background:white;border-radius:8px;padding:3px">
                <h6 style="color:#00e5ff;margin:6px 0 2px 0;font-size:12px">{{p.nombre}}</h6>
                <small style="color:#aaa">${{p.precio}} | Stock {{p.stock}}</small>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
<script>
function filtrarMesa(cat){
    document.querySelectorAll('.mesa-center.cat-btn').forEach(b=>b.classList.remove('active'));
    document.getElementById('mbtn-'+cat).classList.add('active');
    document.querySelectorAll('.prod-card-mesa').forEach(card=>{
        if(cat==='todos' || card.dataset.cat===cat){card.style.display='block';} else {card.style.display='none';}
    });
}
</script>
""", mesa=mesa, productos=productos, carrito=carrito, total_nuevo=total_nuevo, total_mesa=total_mesa, comandas_activas=comandas_activas)

# RUTAS PARA MESERO EDITAR TICKET
@app.route('/mesa/<int:mesa_id>/add/<int:prod_id>')
def mesa_add(mesa_id, prod_id):
    if 'user' not in session: return redirect('/')
    prod=Producto.query.get(prod_id)
    if not prod or prod.stock<=0: return redirect(f'/mesa/{mesa_id}')
    carrito=get_mesa_carrito(mesa_id)
    found=False
    for item in carrito:
        if item['id']==prod.id:
            item['cant']+=1; found=True; break
    if not found:
        carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':prod.precio,'costo':prod.costo or 0,'cant':1})
    set_mesa_carrito(mesa_id, carrito)
    return redirect(f'/mesa/{mesa_id}')

@app.route('/mesa/<int:mesa_id>/cant/<int:index>/<int:delta>')
def mesa_cant(mesa_id, index, delta):
    carrito=get_mesa_carrito(mesa_id)
    if 0 <= index < len(carrito):
        carrito[index]['cant']+=delta
        if carrito[index]['cant']<=0:
            carrito.pop(index)
        set_mesa_carrito(mesa_id, carrito)
    return redirect(f'/mesa/{mesa_id}')

@app.route('/mesa/<int:mesa_id>/remove/<int:index>')
def mesa_remove(mesa_id, index):
    carrito=get_mesa_carrito(mesa_id)
    if 0 <= index < len(carrito):
        carrito.pop(index)
        set_mesa_carrito(mesa_id, carrito)
    return redirect(f'/mesa/{mesa_id}')

@app.route('/mesa/<int:mesa_id>/clear')
def mesa_clear(mesa_id):
    set_mesa_carrito(mesa_id, [])
    return redirect(f'/mesa/{mesa_id}')

@app.route('/mesa/<int:mesa_id>/enviar')
def mesa_enviar(mesa_id):
    if 'user' not in session: return redirect('/')
    mesa=Mesa.query.get(mesa_id)
    carrito=get_mesa_carrito(mesa_id)
    if not carrito:
        return redirect(f'/mesa/{mesa_id}')
    for item in carrito:
        prod=Producto.query.get(item['id'])
        if not prod or prod.stock < item['cant']:
            continue
        com=Comanda(mesa_id=mesa.id, producto_nombre=prod.nombre, cantidad=item['cant'], mesero=session.get('user'), estado="cocina")
        mesa.estado="ocupada"
        mesa.total = (mesa.total or 0) + (prod.precio*item['cant'])
        prod.stock = prod.stock - item['cant']
        db.session.add(com)
    db.session.commit()
    set_mesa_carrito(mesa_id, [])
    return redirect(f'/mesa/{mesa_id}')

@app.route('/mesa/<int:id>/cobrar')
def mesa_cobrar(id):
    if 'user' not in session: return redirect('/')
    mesa = Mesa.query.get(id)
    # cobrar también lo que esté en carrito pendiente
    carrito=get_mesa_carrito(id)
    for item in carrito:
        prod=Producto.query.get(item['id'])
        if prod:
            com=Comanda(mesa_id=mesa.id, producto_nombre=prod.nombre, cantidad=item['cant'], mesero=session.get('user'), estado="cocina")
            mesa.total = (mesa.total or 0) + (prod.precio*item['cant'])
            prod.stock = prod.stock - item['cant']
            db.session.add(com)
    db.session.commit()
    set_mesa_carrito(id, [])
    # ahora cobra todo lo de la mesa
    for c in mesa.comandas:
        if c.estado!= 'entregado':
            prod = Producto.query.filter_by(nombre=c.producto_nombre).first()
            precio = prod.precio if prod else 0
            costo = (prod.costo if prod and prod.costo else 0) * c.cantidad
            v = Venta(cliente=mesa.nombre, producto_nombre=c.producto_nombre, cantidad=c.cantidad, total=precio*c.cantidad, vendedor=session.get('user'), costo_total=costo)
            db.session.add(v); c.estado='entregado'
    mesa.estado='libre'; mesa.total=0; db.session.commit()
    return redirect('/mesas')

@app.route('/cocina')
def cocina_view():
    if 'user' not in session: return redirect('/')
    chk=check_mod('mod_cocina')
    if chk: return chk
    comandas = Comanda.query.filter(Comanda.estado=='cocina').order_by(Comanda.fecha.asc()).all()
    llevar = PedidoLlevar.query.filter(PedidoLlevar.estado=='cocina').order_by(PedidoLlevar.fecha.asc()).all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4"><div class="card" style="border-color:#ffcc00"><h3 style="color:#ffcc00">🔥 Cocina - {{comandas|length + llevar|length}} pendientes</h3><div class="row g-3 mt-2">{% for c in comandas %}<div class="col-md-4"><div class="card" style="background:#1a1a0a;border-color:#ff4d3a"><h6 style="color:#00e5ff">{{c.mesa.nombre}}</h6><h4>{{c.cantidad}}x {{c.producto_nombre}}</h4><small>{{c.mesero}} - {{c.fecha.strftime('%H:%M')}}</small><a href="/cocina/listo/{{c.id}}" class="btn-rosa w-100 mt-3" style="background:#25D366">✅ LISTO</a></div></div>{% endfor %}{% for p in llevar %}<div class="col-md-4"><div class="card" style="background:#1a1500;border-color:#ffaa00"><h6 style="color:#ffaa00">🛵 {{p.tipo|upper}} - {{p.cliente_nombre}}</h6><h4>{{p.cantidad}}x {{p.producto_nombre}}</h4><small>{{p.telefono}} - {{p.fecha.strftime('%H:%M')}}</small><a href="/llevar/listo/{{p.id}}" class="btn-rosa w-100 mt-3" style="background:#ffaa00;color:black">✅ LISTO LLEVAR</a></div></div>{% endfor %}{% if not comandas and not llevar %}<div class="col-12 text-center p-4"><h4 style="color:#25D366">Todo al día 🟢</h4></div>{% endif %}</div></div></div><script>setTimeout(()=>location.reload(), 15000);</script>""", comandas=comandas, llevar=llevar)

@app.route('/cocina/listo/<int:id>')
def cocina_listo(id):
    c = Comanda.query.get(id); c.estado='listo'; db.session.commit()
    return redirect('/cocina')

@app.route('/clientes', methods=['GET','POST'])
def clientes_view():
    if 'user' not in session: return redirect('/')
    chk=check_mod('mod_clientes')
    if chk: return chk
    if request.method=='POST':
        nombre=request.form['nombre'].strip(); tel=request.form['telefono'].strip()
        if not Cliente.query.filter_by(nombre=nombre).first():
            db.session.add(Cliente(nombre=nombre, telefono=tel, visitas=0, gasto_total=0)); db.session.commit()
        return redirect('/clientes')
    clientes=Cliente.query.order_by(Cliente.gasto_total.desc()).all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4"><div class="row"><div class="col-md-4"><div class="card"><h5 style="color:#00ffaa">👤 Nuevo Cliente</h5><form method="POST" class="mt-3"><input name="nombre" class="form-control mb-3" placeholder="Nombre" required><input name="telefono" class="form-control mb-3" placeholder="WhatsApp" required><button class="btn-rosa w-100" style="background:#00ffaa;color:black">Guardar</button></form></div></div><div class="col-md-8"><div class="card"><h5>Clientes ({{clientes|length}})</h5><table class="table table-dark table-bordered mt-3"><tr><th>Nombre</th><th>Tel</th><th>Visitas</th><th>Gastado</th></tr>{% for c in clientes %}<tr><td>{{c.nombre}}</td><td>{{c.telefono}}</td><td>{{c.visitas}}</td><td>${{c.gasto_total}}</td></tr>{% endfor %}</table></div></div></div></div>""", clientes=clientes)

@app.route('/reservas', methods=['GET','POST'])
def reservas_view():
    if 'user' not in session: return redirect('/')
    chk=check_mod('mod_reservas')
    if chk: return chk
    mesas=Mesa.query.all()
    if request.method=='POST':
        r=Reserva(cliente_nombre=request.form['cliente_nombre'], telefono=request.form['telefono'], fecha=request.form['fecha'], hora=request.form['hora'], personas=int(request.form['personas']), mesa_id=int(request.form['mesa_id']) if request.form['mesa_id'] else None, estado="pendiente")
        db.session.add(r); db.session.commit(); return redirect('/reservas')
    reservas=Reserva.query.order_by(Reserva.fecha.desc()).all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4"><div class="row"><div class="col-md-4"><div class="card"><h5 style="color:#aa88ff">📅 Nueva Reserva</h5><form method="POST" class="mt-3"><input name="cliente_nombre" class="form-control mb-2" placeholder="Cliente" required><input name="telefono" class="form-control mb-2" placeholder="Tel" required><input name="fecha" type="date" class="form-control mb-2" required><input name="hora" type="time" class="form-control mb-2" required><input name="personas" type="number" class="form-control mb-2" placeholder="Personas" required><select name="mesa_id" class="form-control mb-3"><option value="">Mesa automática</option>{% for m in mesas %}<option value="{{m.id}}">{{m.nombre}}</option>{% endfor %}</select><button class="btn-rosa w-100" style="background:#aa88ff;color:black">Guardar</button></form></div></div><div class="col-md-8"><div class="card"><h5>Reservas</h5><table class="table table-dark mt-3"><tr><th>Cliente</th><th>Fecha</th><th>Hora</th><th>Pers</th><th>Mesa</th><th>Estado</th></tr>{% for r in reservas %}<tr><td>{{r.cliente_nombre}}</td><td>{{r.fecha}}</td><td>{{r.hora}}</td><td>{{r.personas}}</td><td>{{r.mesa.nombre if r.mesa else 'Auto'}}</td><td>{{r.estado}}</td></tr>{% endfor %}</table></div></div></div></div>""", reservas=reservas, mesas=mesas)

@app.route('/para_llevar', methods=['GET','POST'])
def para_llevar_view():
    if 'user' not in session: return redirect('/')
    chk=check_mod('mod_llevar')
    if chk: return chk
    productos=Producto.query.all()
    if request.method=='POST':
        prod=Producto.query.get(int(request.form['producto_id'])); cant=int(request.form['cantidad'])
        total=prod.precio*cant; costo=(prod.costo or 0)*cant
        p=PedidoLlevar(cliente_nombre=request.form['cliente_nombre'], telefono=request.form['telefono'], producto_nombre=prod.nombre, cantidad=cant, total=total, tipo=request.form['tipo'], direccion=request.form.get('direccion',''), estado='cocina', vendedor=session.get('user'), costo_total=costo)
        prod.stock-=cant; db.session.add(p); db.session.commit()
        return redirect('/para_llevar')
    pedidos=PedidoLlevar.query.order_by(PedidoLlevar.fecha.desc()).limit(30).all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4"><div class="row"><div class="col-md-4"><div class="card"><h5 style="color:#ffaa00">🛵 Nuevo Pedido Para Llevar</h5><form method="POST" class="mt-3"><input name="cliente_nombre" class="form-control mb-2" placeholder="Cliente" required><input name="telefono" class="form-control mb-2" placeholder="Tel" required><select name="producto_id" class="form-control mb-2" required>{% for p in productos %}<option value="{{p.id}}">{{p.nombre}} - ${{p.precio}}</option>{% endfor %}</select><input name="cantidad" type="number" value="1" min="1" class="form-control mb-2" required><select name="tipo" class="form-control mb-2"><option value="llevar">Recoge</option><option value="domicilio">Domicilio</option></select><textarea name="direccion" class="form-control mb-3" placeholder="Dirección"></textarea><button class="btn-rosa w-100" style="background:#ffaa00;color:black">MANDAR A COCINA</button></form></div></div><div class="col-md-8"><div class="card"><h5>Pedidos Llevar</h5><table class="table table-dark mt-3"><tr><th>Cliente</th><th>Pedido</th><th>Tipo</th><th>Estado</th><th></th></tr>{% for p in pedidos %}<tr><td>{{p.cliente_nombre}}</td><td>{{p.cantidad}}x {{p.producto_nombre}} - ${{p.total}}</td><td>{{p.tipo}}</td><td>{{p.estado}}</td><td>{% if p.estado!='entregado' %}<a href="/llevar/cobrar/{{p.id}}" class="btn-rosa" style="font-size:11px">COBRAR</a>{% endif %}</td></tr>{% endfor %}</table></div></div></div></div>""", productos=productos, pedidos=pedidos)

@app.route('/llevar/listo/<int:id>')
def llevar_listo(id): p=PedidoLlevar.query.get(id); p.estado='listo'; db.session.commit(); return redirect('/cocina')
@app.route('/llevar/cobrar/<int:id>')
def llevar_cobrar(id):
    p=PedidoLlevar.query.get(id)
    v=Venta(cliente=p.cliente_nombre+f" ({p.tipo})", producto_nombre=p.producto_nombre, cantidad=p.cantidad, total=p.total, vendedor=session.get('user'), costo_total=p.costo_total)
    db.session.add(v); p.estado='entregado'; db.session.commit()
    return redirect('/para_llevar')

@app.route('/dueno', methods=['GET','POST'])
def dueno_dashboard():
    if 'user' not in session: return redirect('/')
    if not session.get('is_admin'): return redirect('/dashboard')
    hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    if request.method=='POST':
        g=Gasto(concepto=request.form['concepto'], monto=float(request.form['monto']), categoria=request.form['categoria'], usuario=session.get('user'))
        db.session.add(g); db.session.commit(); return redirect('/dueno')
    ventas_hoy=Venta.query.filter(Venta.fecha>=hoy).all()
    gastos_hoy=Gasto.query.filter(Gasto.fecha>=hoy).all()
    total_ventas=sum([v.total for v in ventas_hoy]); total_costos=sum([v.costo_total or 0 for v in ventas_hoy]); total_gastos=sum([g.monto for g in gastos_hoy])
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4"><div class="card"><h3>💰 Dueño - Hoy</h3><div class="row g-3 mt-3"><div class="col-md-3"><div class="card"><h6>VENTAS</h6><h2>${{total_ventas}}</h2></div></div><div class="col-md-3"><div class="card"><h6>COSTOS</h6><h2>${{total_costos}}</h2></div></div><div class="col-md-3"><div class="card"><h6>GASTOS</h6><h2>${{total_gastos}}</h2></div></div><div class="col-md-3"><div class="card" style="border-color:#25D366"><h6 style="color:#25D366">GANANCIA NETA</h6><h2 style="color:#25D366">${{total_ventas-total_costos-total_gastos}}</h2></div></div></div></div>
    <div class="row mt-4"><div class="col-md-8"><div class="card"><h5>Ventas Hoy</h5><table class="table table-dark mt-3"><tr><th>Cliente</th><th>Producto</th><th>Total</th><th>Ganancia</th><th></th></tr>{% for v in ventas_hoy %}<tr><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td><td style="color:#25D366">${{v.total-(v.costo_total or 0)}}</td><td><a href="/eliminar_venta/{{v.id}}" style="color:red">🗑️</a></td></tr>{% endfor %}</table></div></div><div class="col-md-4"><div class="card"><h5>Gasto</h5><form method="POST" class="mt-3"><input name="concepto" class="form-control mb-2" placeholder="Concepto" required><input name="monto" type="number" step="0.01" class="form-control mb-2" placeholder="Monto" required><select name="categoria" class="form-control mb-3"><option value="general">General</option><option value="gas">Gas</option><option value="renta">Renta</option><option value="personal">Personal</option><option value="insumos">Insumos</option></select><button class="btn-rosa w-100">Agregar</button></form><table class="table table-dark mt-3"><tr><th>Concepto</th><th>Monto</th><th></th></tr>{% for g in gastos_hoy %}<tr><td>{{g.concepto}}</td><td>${{g.monto}}</td><td><a href="/gasto/eliminar/{{g.id}}" style="color:red">X</a></td></tr>{% endfor %}</table></div></div></div></div>""", total_ventas=total_ventas, total_costos=total_costos, total_gastos=total_gastos, ventas_hoy=ventas_hoy, gastos_hoy=gastos_hoy)

@app.route('/gasto/eliminar/<int:id>')
def gasto_eliminar(id):
    if not session.get('is_admin'): return redirect('/dashboard')
    g=Gasto.query.get(id); db.session.delete(g); db.session.commit(); return redirect('/dueno')

@app.route('/vender', methods=['POST'])
def vender():
    if 'user' not in session: return redirect('/')
    prod=Producto.query.get(int(request.form['producto_id']))
    cliente_nombre=(request.form.get('cliente') or "Mostrador").strip() or "Mostrador"
    costo=(prod.costo or 0)*int(request.form['cantidad'])
    v=Venta(cliente=cliente_nombre, producto_nombre=prod.nombre, cantidad=int(request.form['cantidad']), total=prod.precio*int(request.form['cantidad']), vendedor=session.get('user'), costo_total=costo)
    prod.stock = prod.stock - v.cantidad
    db.session.add(v); db.session.commit()
    cfg=get_config()
    if cfg.tickets: return redirect(f'/ticket/{v.id}')
    return redirect('/dashboard')

@app.route('/ticket/<int:id>')
def ticket(id):
    if 'user' not in session: return redirect('/')
    cfg=get_config()
    if not cfg.tickets: return redirect('/dashboard')
    v=Venta.query.get(id)
    if not session.get('is_admin') and v.vendedor!= session.get('user'): return redirect('/dashboard')
    return render_template_string(STYLE_BASE+f'<div class="container" style="max-width:380px;margin-top:20px"><div class="card" style="background:white;color:black;border:2px dashed black"><div class="text-center"><img src="/static/logo.png?v=ruve3" style="width:110px"><h5 style="font-weight:bold">LECHÓN AL HORNO RUVE</h5></div><hr><p><b>Ticket #{v.id}</b><br>Cliente: {v.cliente}<br>Vendedor: {v.vendedor}<br>Fecha: {v.fecha.strftime("%d/%m/%Y %H:%M")}<br>Producto: {v.producto_nombre}<br>Cant: {v.cantidad}<br><b>Total: ${v.total}</b></p><div class="text-center no-print"><button onclick="window.print()" class="btn-rosa">🖨️ IMPRIMIR</button><a href="/dashboard" class="btn btn-dark ms-2">Volver</a></div></div></div>')

@app.route('/productos', methods=['GET','POST'])
def productos_route():
    if 'user' not in session: return redirect('/')
    if not session.get('is_admin'): return redirect('/dashboard')
    if request.method=='POST':
        db.session.add(Producto(nombre=request.form['nombre'], precio=float(request.form['precio']), stock=int(request.form['stock']), costo=float(request.form.get('costo',0)))); db.session.commit(); return redirect('/productos')
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4"><div class="card"><h5>Productos</h5><form method="POST" class="row g-2 mt-2"><div class="col-md-3"><input name="nombre" class="form-control" placeholder="Nombre" required></div><div class="col-md-2"><input name="precio" type="number" step="0.01" class="form-control" placeholder="Precio" required></div><div class="col-md-2"><input name="costo" type="number" step="0.01" class="form-control" placeholder="Costo" required></div><div class="col-md-2"><input name="stock" type="number" class="form-control" placeholder="Stock" required></div><div class="col-md-3"><button class="btn-rosa w-100">Agregar</button></div></form><table class="table table-dark table-bordered mt-4"><tr><th>Nombre</th><th>Venta</th><th>Costo</th><th>Ganancia</th><th>Stock</th><th></th></tr>{% for p in productos %}<tr><td>{{p.nombre}}</td><td>${{p.precio}}</td><td>${{p.costo}}</td><td style="color:#25D366">${{p.precio-p.costo}}</td><td>{{p.stock}}</td><td><a href="/eliminar_producto/{{p.id}}" style="color:red">X</a></td></tr>{% endfor %}</table></div></div>""", productos=Producto.query.all())

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
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4"><div class="card"><h5>{% if is_admin %}Historial Completo - Admin puede borrar 🗑️{% else %}Mi Historial{% endif %} - Total: ${{total}}</h5><table class="table table-dark table-bordered mt-3"><tr><th>Cliente</th><th>Producto</th><th>Total</th>{% if is_admin %}<th>Vendedor</th>{% endif %}<th>Acciones</th></tr>{% for v in ventas %}<tr><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td>{% if is_admin %}<td>{{v.vendedor}}</td>{% endif %}<td>{% if cfg.tickets %}<a href="/ticket/{{v.id}}" class="btn-rosa" style="font-size:11px">TICKET</a>{% endif %}{% if is_admin %}<a href="/eliminar_venta/{{v.id}}" class="btn ms-1" style="background:#ff3b3b;color:white;font-size:11px" onclick="return confirm('¿Borrar ticket #{{v.id}}?')">🗑️</a>{% endif %}</td></tr>{% endfor %}</table></div></div>""", ventas=ventas, total=sum([v.total for v in ventas]), cfg=cfg, is_admin=session.get('is_admin'))

@app.route('/reporte')
def reporte():
    if 'user' not in session: return redirect('/')
    cfg=get_config(); hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    if session.get('is_admin'): ventas_hoy=Venta.query.filter(Venta.fecha>=hoy).order_by(Venta.fecha.desc()).all()
    else: ventas_hoy=Venta.query.filter(Venta.fecha>=hoy, Venta.vendedor==session.get('user')).order_by(Venta.fecha.desc()).all()
    total_hoy=sum([v.total for v in ventas_hoy])
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4"><div class="card"><h4>Total Hoy: ${{total_hoy}} ({{ventas_hoy|length}})</h4><a href="/ventas" class="btn-rosa mt-2">Ver Historial</a> {% if is_admin %}<a href="/dueno" class="btn-rosa ms-2">💰 Dueño</a>{% endif %}</div><div class="card mt-4"><h5>Detalle Hoy</h5><table class="table table-dark mt-3"><tr><th>Hora</th><th>Cliente</th><th>Producto</th><th>Total</th><th></th></tr>{% for v in ventas_hoy %}<tr><td>{{v.fecha.strftime('%H:%M')}}</td><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td><td>{% if is_admin %}<a href="/eliminar_venta/{{v.id}}" style="color:#ff3b3b" onclick="return confirm('¿Borrar?')">🗑️</a>{% endif %}</td></tr>{% endfor %}</table></div></div>""", ventas_hoy=ventas_hoy, total_hoy=total_hoy, cfg=cfg, is_admin=session.get('is_admin'))

@app.route('/reporte_pdf')
def reporte_pdf():
    if 'user' not in session: return redirect('/')
    hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    if session.get('is_admin'): ventas=Venta.query.filter(Venta.fecha>=hoy).all()
    else: ventas=Venta.query.filter(Venta.fecha>=hoy, Venta.vendedor==session.get('user')).all()
    total=sum([v.total for v in ventas])
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    buffer=io.BytesIO(); c=canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 16); c.drawString(50,750,f"RUVE - {session.get('user')}")
    c.setFont("Helvetica", 12); c.drawString(50,730,f"Fecha: {datetime.now().strftime('%d/%m/%Y')} - Total: ${total}"); y=700
    for v in ventas:
        c.drawString(50,y,f"{v.fecha.strftime('%H:%M')} - {v.cliente} - {v.cantidad}x {v.producto_nombre} - ${v.total}"); y-=20
        if y<50: c.showPage(); y=750
    c.save(); buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"reporte_{session.get('user')}.pdf", mimetype='application/pdf')

@app.route('/admin/config', methods=['GET','POST'])
def admin_config():
    chk=admin_required()
    if chk: return chk
    cfg=get_config()
    if request.method=='POST':
        cfg.whatsapp_btn = 'whatsapp_btn' in request.form; cfg.tickets = 'tickets' in request.form; cfg.reporte_pdf = 'reporte_pdf' in request.form; cfg.total_whatsapp = 'total_whatsapp' in request.form
        cfg.mod_mesas = 'mod_mesas' in request.form; cfg.mod_cocina = 'mod_cocina' in request.form; cfg.mod_clientes = 'mod_clientes' in request.form; cfg.mod_reservas = 'mod_reservas' in request.form; cfg.mod_llevar = 'mod_llevar' in request.form; cfg.mod_dueno = 'mod_dueno' in request.form
        cfg.numero_whatsapp = request.form.get('numero_whatsapp','').strip() or cfg.numero_whatsapp; db.session.commit(); return redirect('/admin/config')
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4" style="max-width:700px"><div class="card"><h4>⚙️ Config Admin</h4><form method="POST" class="mt-2"><label><input type="checkbox" name="whatsapp_btn" {{'checked' if cfg.whatsapp_btn}}> WhatsApp</label><br><label><input type="checkbox" name="tickets" {{'checked' if cfg.tickets}}> Tickets</label><br><label><input type="checkbox" name="reporte_pdf" {{'checked' if cfg.reporte_pdf}}> PDF</label><br><label><input type="checkbox" name="total_whatsapp" {{'checked' if cfg.total_whatsapp}}> Total WA</label><br><hr><label><input type="checkbox" name="mod_mesas" {{'checked' if cfg.mod_mesas}}> Mesas</label><br><label><input type="checkbox" name="mod_cocina" {{'checked' if cfg.mod_cocina}}> Cocina</label><br><label><input type="checkbox" name="mod_clientes" {{'checked' if cfg.mod_clientes}}> Clientes</label><br><label><input type="checkbox" name="mod_reservas" {{'checked' if cfg.mod_reservas}}> Reservas</label><br><label><input type="checkbox" name="mod_llevar" {{'checked' if cfg.mod_llevar}}> Llevar</label><br><label><input type="checkbox" name="mod_dueno" {{'checked' if cfg.mod_dueno}}> Dueño</label><br><br><input name="numero_whatsapp" class="form-control" value="{{cfg.numero_whatsapp}}"><br><button class="btn-rosa w-100">GUARDAR</button></form></div></div>""", cfg=cfg)

@app.route('/admin/usuarios', methods=['GET','POST'])
def admin_usuarios():
    chk=admin_required()
    if chk: return chk
    if request.method=='POST':
        if User.query.filter_by(username=request.form['username']).first():
            return render_template_string(STYLE_BASE+nav()+'<div class="container mt-4"><div class="card"><h5 style="color:red">Ya existe</h5><a href="/admin/usuarios" class="btn-rosa">Volver</a></div></div>')
        es_admin = 'is_admin' in request.form; rol = request.form.get('rol','cajero')
        if es_admin: rol='admin'
        db.session.add(User(username=request.form['username'].strip(), password=generate_password_hash(request.form['password']), is_admin=es_admin, rol=rol)); db.session.commit(); return redirect('/admin/usuarios')
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4"><div class="row"><div class="col-md-4"><div class="card"><h5>Crear Usuario</h5><form method="POST" class="mt-3"><input name="username" class="form-control mb-3" placeholder="Usuario" required><input name="password" class="form-control mb-3" type="text" placeholder="Contraseña" required><select name="rol" class="form-control mb-3"><option value="cajero">Cajero</option><option value="mesero">Mesero</option><option value="cocina">Cocina</option></select><label><input type="checkbox" name="is_admin"> Es admin</label><br><button class="btn-rosa w-100">Crear</button></form></div></div><div class="col-md-8"><div class="card"><h5>Usuarios</h5><table class="table table-dark mt-3"><tr><th>Usuario</th><th>Rol</th><th></th></tr>{% for u in usuarios %}<tr><td>{{u.username}}</td><td>{% if u.is_admin %}ADMIN{% else %}{{u.rol}}{% endif %}</td><td>{% if u.username!='admin' %}<a href="/admin/usuarios/eliminar/{{u.id}}" style="color:red">Eliminar</a>{% endif %}</td></tr>{% endfor %}</table></div></div></div></div>""", usuarios=User.query.all())

@app.route('/admin/usuarios/eliminar/<int:id>')
def eliminar_usuario(id):
    chk=admin_required()
    if chk: return chk
    u=User.query.get(id)
    if u and u.username!='admin': db.session.delete(u); db.session.commit()
    return redirect('/admin/usuarios')

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

def logout(): session.clear(); return redirect('/')

@app.route("/ping")
def ping():
    return "Ruve vivo", 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

