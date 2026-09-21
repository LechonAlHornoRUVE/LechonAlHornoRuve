from flask import Flask, request, redirect, session, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os, traceback

app = Flask(__name__)
app.secret_key = 'ruve-diseno-original-restaurado-fix-mesa4'

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXT = {'png','jpg','jpeg','webp'}

db_url = os.environ.get('DATABASE_URL', 'sqlite:///lechon.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

CLOUDINARY_ENABLED = False
try:
    import cloudinary, cloudinary.uploader
    cloudinary.config(cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'), api_key=os.environ.get('CLOUDINARY_API_KEY'), api_secret=os.environ.get('CLOUDINARY_API_SECRET'), secure=True)
    if os.environ.get('CLOUDINARY_CLOUD_NAME'):
        CLOUDINARY_ENABLED = True
except: pass

class User(db.Model):
    __tablename__='usuarios'
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True)
    nombre_completo=db.Column(db.String(100), default="")
    password=db.Column(db.String(200))
    is_admin=db.Column(db.Boolean, default=False)
    rol=db.Column(db.String(20), default="cajero")
class Categoria(db.Model):
    __tablename__='categorias'
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(50), unique=True)
class Producto(db.Model):
    __tablename__='productos'
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(100))
    precio=db.Column(db.Float, default=0)
    stock=db.Column(db.Integer, default=0)
    costo=db.Column(db.Float, default=0)
    imagen=db.Column(db.Text, default="")
    descripcion=db.Column(db.Text, default="")
    categoria=db.Column(db.String(50), default="Sin categoria")
    disponible=db.Column(db.Boolean, default=True)
    vendido_por=db.Column(db.String(20), default="Unidad")
    ref=db.Column(db.String(50), default="")
    codigo_barras=db.Column(db.String(100), default="")
class Venta(db.Model):
    __tablename__='ventas'
    id=db.Column(db.Integer, primary_key=True)
    cliente=db.Column(db.String(100))
    producto_nombre=db.Column(db.String(100))
    cantidad=db.Column(db.Integer)
    total=db.Column(db.Float)
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    vendedor=db.Column(db.String(80), default="admin")
    vendedor_nombre=db.Column(db.String(100), default="")
    metodo_pago=db.Column(db.String(20), default="efectivo")
class Gasto(db.Model):
    __tablename__='gastos'
    id=db.Column(db.Integer, primary_key=True)
    concepto=db.Column(db.String(100))
    monto=db.Column(db.Float)
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
class Config(db.Model):
    __tablename__='config'
    id=db.Column(db.Integer, primary_key=True)
    logo_path=db.Column(db.Text, default="logo.png")
    mod_pos_mesero=db.Column(db.Boolean, default=False)
    mod_mesero_cobrar=db.Column(db.Boolean, default=False)
class Mesa(db.Model):
    __tablename__='mesas'
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(50))
    estado=db.Column(db.String(20), default="libre")
    total=db.Column(db.Float, default=0)
class Comanda(db.Model):
    __tablename__='comandas'
    id=db.Column(db.Integer, primary_key=True)
    mesa_id=db.Column(db.Integer, db.ForeignKey('mesas.id'))
    producto_nombre=db.Column(db.String(100))
    cantidad=db.Column(db.Integer)
    estado=db.Column(db.String(20), default="cocina")
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    mesero=db.Column(db.String(80))
    mesero_nombre=db.Column(db.String(100), default="")
    comentario=db.Column(db.String(200), default="")
    mesa=db.relationship('Mesa', backref='comandas', foreign_keys=[mesa_id])

def get_config():
    c=Config.query.first()
    if not c:
        c=Config()
        db.session.add(c)
        db.session.commit()
    return c

def save_upload(file):
    if not file or not file.filename or '.' not in file.filename: return ""
    ext=file.filename.rsplit('.',1)[1].lower()
    if ext not in ALLOWED_EXT: return ""
    try:
        try: file.stream.seek(0)
        except: pass
        if CLOUDINARY_ENABLED:
            res=cloudinary.uploader.upload(file, folder="ruve_productos", overwrite=True, resource_type="image")
            return res.get('secure_url','')
    except: pass
    try:
        try: file.stream.seek(0)
        except: pass
        fn=datetime.now().strftime('%Y%m%d%H%M%S%f')+"_"+secure_filename(file.filename)
        path=os.path.join(UPLOAD_FOLDER, fn)
        file.save(path)
        return "uploads/"+fn
    except: return ""

def get_producto_imagen(p):
    try:
        if p and getattr(p,'imagen',None) and p.imagen.startswith('http'):
            return p.imagen
    except: pass
    try:
        if p and getattr(p,'imagen',None) and 'uploads' in p.imagen:
            full=os.path.join(app.root_path, 'static', p.imagen)
            if os.path.exists(full):
                return "/static/"+p.imagen
    except: pass
    cfg=get_config()
    if getattr(cfg,'logo_path',None) and cfg.logo_path.startswith('http'):
        return cfg.logo_path
    return "/static/"+cfg.logo_path

def format_mxn(n):
    try: return "${:,.2f} MXN".format(float(n))
    except: return "$0.00 MXN"

with app.app_context():
    db.create_all()
    from sqlalchemy import text
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE config ADD COLUMN IF NOT EXISTS mod_mesero_cobrar BOOLEAN DEFAULT FALSE"))
            conn.execute(text("ALTER TABLE config ADD COLUMN IF NOT EXISTS mod_pos_mesero BOOLEAN DEFAULT FALSE"))
            conn.commit()
    except: pass
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin',nombre_completo='Administrador General',password=generate_password_hash('admin123'),is_admin=True,rol='admin'))
    if Categoria.query.count()==0:
        for cat in ["Sin categoría","Lechón","Tortas","Órdenes","Bebidas","Extras","Comida"]:
            if not Categoria.query.filter_by(nombre=cat).first():
                db.session.add(Categoria(nombre=cat))
    if Mesa.query.count()==0:
        for i in range(1,13):
            db.session.add(Mesa(nombre="Mesa "+str(i)))
    db.session.commit()

STYLE_BASE = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{--rosa:#ff4d8a}
body{background:#000;color:white;font-family:Arial;margin:0}
.card{background:#111;border:2px solid var(--rosa);border-radius:15px;padding:20px}
.btn-rosa{background:var(--rosa);color:white;border:none;padding:10px 18px;border-radius:10px;font-weight:bold}
.navbar{background:#000!important;border-bottom:2px solid var(--rosa);display:flex;justify-content:space-between;align-items:center;padding:10px 15px;flex-wrap:wrap}
.pos-container{display:flex;height:calc(100vh - 60px);gap:10px;padding:10px}
.pos-left{width:38%;background:#0f0f0f;border:2px solid var(--rosa);border-radius:15px;display:flex;flex-direction:column}
.pos-center{width:12%;display:flex;flex-direction:column;gap:8px;overflow-y:auto}
.pos-right{width:50%;background:#0f0f0f;border:2px solid #333;border-radius:15px;padding:10px;overflow-y:auto}
.cat-btn{background:#222;color:white;font-weight:bold;padding:14px;border:2px solid #333;border-radius:8px;cursor:pointer;text-align:center;font-size:12px}
.cat-btn.active{background:var(--rosa);border-color:var(--rosa)}
.prod-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.prod-card{background:#1a1a1a;border:2px solid #333;border-radius:12px;padding:10px;text-align:center;cursor:pointer}
.prod-card:hover{border-color:var(--rosa)}
.prod-card img{width:70px;height:70px;object-fit:cover;border-radius:10px;background:white;padding:5px}
.prod-card h6{color:var(--rosa);margin:8px 0 2px 0;font-size:12px}
.ticket-header{background:#111;padding:12px;border-bottom:2px solid var(--rosa);border-radius:15px 15px 0 0}
.ticket-body{flex:1;overflow-y:auto;padding:10px;background:white;color:black}
.ticket-footer{background:#111;padding:12px;border-top:2px solid var(--rosa);border-radius:0 0 15px 15px}
.btn-cash{background:#25D366;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:100%}
.btn-pay{background:#3f51b5;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:100%}
.btn-trans{background:#0097a7;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:100%}
.btn-clear{background:#333;color:white;border:1px solid #555;width:100%;padding:10px;border-radius:8px;margin-top:8px;font-weight:bold}
.dropdown{position:relative;display:inline-block}
.dropbtn{background:#111;color:var(--rosa);border:2px solid var(--rosa);padding:6px 14px;border-radius:8px;font-weight:bold;cursor:pointer}
.dropdown-content{display:none;position:absolute;right:0;background:#111;border:2px solid var(--rosa);border-radius:10px;min-width:230px;z-index:9999}
.dropdown-content a{display:block;padding:12px 16px;color:white;text-decoration:none;font-size:13px;border-bottom:1px solid #222}
.dropdown-content a:hover{background:#222;color:var(--rosa)}
.dropdown-content.show{display:block}
.crear-wrapper{background:#000;min-height:100vh}
.crear-header{background:var(--rosa);color:white;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;font-weight:bold}
.crear-card{background:#0e0e0e;border:1px solid #222;border-radius:8px;padding:20px;margin:15px}
.crear-input{border:none!important;border-bottom:1px solid #444!important;background:transparent!important;color:white!important;border-radius:0!important;padding:12px 0!important;width:100%;font-size:15px}
.crear-input:focus{border-bottom-color:var(--rosa)!important;box-shadow:none!important}
.crear-label{font-size:11px;color:#888;display:block;margin-top:5px}
.crear-label-rosa{font-size:11px;color:var(--rosa);display:block;margin-top:15px;font-weight:bold}
.label-rosa{font-size:11px;color:var(--rosa);margin-top:18px;display:block;font-weight:bold}
.modal-efectivo{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);display:none;justify-content:center;align-items:center;z-index:99999}
.modal-efectivo.show{display:flex}
.modal-caja{background:#111;border:2px solid var(--rosa);border-radius:15px;padding:25px;width:90%;max-width:380px;text-align:center}
</style>
"""

def nav():
    cfg=get_config()
    logo_url=get_producto_imagen(cfg)
    rol=session.get('rol','cajero')
    is_admin=session.get('is_admin', False)
    nombre=session.get('nombre_completo') or session.get('user','')
    if not is_admin and rol=='cocina':
        return '<nav class="navbar"><div class="d-flex align-items-center"><img src="'+logo_url+'" style="width:40px;height:40px;border-radius:50%;background:white;padding:3px;object-fit:cover"><h6 class="m-0 ms-2" style="color:#ffcc00">Cocina '+nombre+'</h6></div><div><a href="/cocina" class="me-3">Cocina</a><a href="/logout">Salir</a></div></nav>'
    links=""
    if is_admin or rol=='cajero':
        links+='<a href="/dashboard" class="me-3">POS</a>'
    if rol=='mesero' and cfg.mod_pos_mesero:
        links+='<a href="/dashboard" class="me-3">POS</a>'
    if is_admin or rol in ['cajero','mesero']:
        links+='<a href="/mesas" class="me-3" style="color:#00e5ff">Mesas</a>'
    if is_admin or rol=='cajero':
        links+='<a href="/cocina" class="me-3" style="color:#ffcc00">Cocina</a>'
    admin_drop=""
    if is_admin:
        admin_drop='<div class="dropdown"><button onclick="toggleDropdown()" class="dropbtn">⚙️ Herramientas admin ▾</button><div id="adminDropdown" class="dropdown-content"><a href="/productos">📦 Productos</a><a href="/productos/nuevo">➕ Crear artículo</a><a href="/admin/categorias">🏷️ Categorías</a><a href="/admin/mesas">🪑 Mesas</a><a href="/ventas">🧾 Ventas</a><a href="/dueno">💰 Dueño + Gráfica</a><a href="/admin/config">⚙️ Config + Logo</a><a href="/admin/usuarios">👥 Usuarios</a></div></div><script>function toggleDropdown(){var d=document.getElementById("adminDropdown"); if(d) d.classList.toggle("show");}</script>'
    html='<nav class="navbar"><div class="d-flex align-items-center"><img src="'+logo_url+'" style="width:40px;height:40px;border-radius:50%;background:white;padding:3px;object-fit:cover"><h6 class="m-0 ms-2" style="color:var(--rosa)">Ruve '+nombre+'</h6><span id="relojPC" style="margin-left:12px;color:var(--rosa);font-size:10px;font-weight:700"></span></div><div>'+links+admin_drop+'<a href="/logout" class="ms-3">Salir</a></div></nav><script>function actualizarReloj(){var el=document.getElementById("relojPC"); if(el){var a=new Date(); el.textContent=a.toLocaleString("es-MX",{timeZone:"America/Cancun"});}} setInterval(actualizarReloj,1000); actualizarReloj();</script>'
    return html

@app.route('/', methods=['GET','POST'])
def login():
    cfg=get_config()
    error=None
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user']=u.username; session['nombre_completo']=u.nombre_completo or u.username; session['is_admin']=u.is_admin; session['rol']=u.rol; session['carrito']=[]
            if u.rol=='cocina' and not u.is_admin: return redirect('/cocina')
            if u.rol=='mesero' and not u.is_admin: return redirect('/mesas')
            return redirect('/dashboard')
        else:
            error="Usuario o contraseña incorrectos"
    logo_url=get_producto_imagen(cfg)
    err_html=""
    if error:
        err_html='<div style="background:#2a1018;border:1px solid var(--rosa);color:var(--rosa);padding:8px;border-radius:8px;font-size:12px;margin-bottom:10px">'+error+'</div>'
    return render_template_string(STYLE_BASE+'<div style="min-height:100vh;display:flex;justify-content:center;align-items:center;background:#000;padding:20px"><div class="card" style="width:100%;max-width:380px;text-align:center;padding:30px 25px"><div style="display:flex;justify-content:center;margin-bottom:15px"><img src="'+logo_url+'" style="width:130px;height:130px;object-fit:cover;border-radius:50%;background:white;padding:5px;border:3px solid var(--rosa)"></div><h3 style="color:var(--rosa);font-weight:bold;margin:10px 0 20px 0">Ruve</h3>'+err_html+'<form method="POST" style="text-align:left"><input name="username" class="form-control mb-3" placeholder="Usuario" required style="background:white!important;color:#333!important;padding:12px;border-radius:8px"><input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required style="background:white!important;color:#333!important;padding:12px;border-radius:8px"><button class="btn-rosa w-100" style="padding:12px;font-size:15px;border-radius:10px">Entrar</button></form><div style="margin-top:15px;text-align:center"><a href="/restablecer" style="color:var(--rosa);font-size:12px;text-decoration:none">¿Olvidaste tu contraseña? Restablecer</a></div></div></div>')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    cfg=get_config()
    if not session.get('is_admin') and session.get('rol')=='mesero' and not cfg.mod_pos_mesero:
        return redirect('/mesas')
    if not session.get('is_admin') and session.get('rol')=='cocina':
        return redirect('/cocina')
    all_prods=Producto.query.all()
    productos=[p for p in all_prods if getattr(p,'disponible',True)==True]
    prod_list=[]
    for p in productos:
        prod_list.append({'id':p.id,'nombre':p.nombre,'categoria':getattr(p,'categoria','Sin categoria'),'stock':getattr(p,'stock',0),'img_url':get_producto_imagen(p),'precio_mxn':format_mxn(p.precio or 0)})
    carrito=session.get('carrito',[])
    total=sum([float(x.get('precio',0))*int(x.get('cant',0)) for x in carrito])
    mesas_ocupadas=Mesa.query.filter_by(estado='ocupada').all()
    mesas_por_cobrar=Mesa.query.filter_by(estado='por_cobrar').all()
    cats=Categoria.query.all()
    try:
        today=datetime.now().date(); start=datetime(today.year,today.month,today.day)
        total_hoy=sum([v.total or 0 for v in Venta.query.filter(Venta.fecha>=start).all()])
    except: total_hoy=0
    return render_template_string(STYLE_BASE+nav()+"""
<div class="pos-container">
    <div class="pos-left">
        <div class="ticket-header"><div style="display:flex;justify-content:space-between"><small style="color:var(--rosa);font-weight:bold">TICKET - MOSTRADOR</small><small id="fechaPOS" style="color:#888;font-size:9px"></small></div><div style="background:#0a1a0f;border:1px solid #25D366;border-radius:8px;padding:6px 8px;margin-top:8px;display:flex;justify-content:space-between"><small style="color:#25D366;font-weight:bold;font-size:10px">VENTA HOY</small><b id="totalHoy" style="color:#25D366;font-size:13px">{{total_hoy_mxn}}</b></div></div>
        <div class="ticket-body">
            {% for item in carrito %}<div style="display:flex;justify-content:space-between;border-bottom:1px dashed #ccc;padding:6px 0;font-size:12px"><span>{{item.nombre}} x{{item.cant}}</span><span>{{item.total_mxn}}</span></div>{% endfor %}
            {% if not carrito %}<p style="color:#888;text-align:center;margin-top:20px;font-size:12px">Toca un producto →</p>{% endif %}
            {% if mesas_por_cobrar %}
            <div style="background:#ffeb3b;color:black;padding:8px;border-radius:8px;margin-top:10px;border:3px solid #ff9800"><b style="font-size:11px">🔔 SOLICITUDES MESERO A CAJA:</b>
            {% for m in mesas_por_cobrar %}<div style="display:flex;justify-content:space-between;align-items:center;background:white;padding:6px;border-radius:4px;margin-top:5px"><span style="font-weight:bold">{{m.nombre}} {{m.total_mxn}}</span><a href="/mesa/{{m.id}}/cobrar" style="background:#25D366;color:white;padding:4px 10px;border-radius:4px;font-size:12px;text-decoration:none">COBRAR AHORA</a></div>{% endfor %}</div>
            {% endif %}
        </div>
        <div class="ticket-footer"><div style="display:flex;justify-content:space-between;color:white;font-weight:bold;font-size:18px"><span>TOTAL</span><span id="totalTicket" data-total="{{total_num}}">${{total}} MXN</span></div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-top:10px"><button onclick="abrirEfectivo()" class="btn-cash">💵 Efectivo</button><a href="/pos/pagar/tarjeta" style="text-decoration:none"><button class="btn-pay">💳 Tarjeta</button></a><a href="/pos/pagar/transferencia" style="text-decoration:none"><button class="btn-trans">🏦 Transfer</button></a></div>
            <form method="POST" action="/pos/clear"><button class="btn-clear">🗑️ LIMPIAR TICKET</button></form></div>
    </div>
    <div class="pos-center"><button class="cat-btn active" onclick="filtrar('todos')" id="btn-todos">Todos</button>{% for cat in cats %}<button class="cat-btn" onclick="filtrar('{{cat.nombre}}')" id="btn-{{cat.nombre}}">{{cat.nombre}}</button>{% endfor %}</div>
    <div class="pos-right"><div class="prod-grid">{% for p in productos %}<div class="prod-card" data-cat="{{p.categoria}}" onclick="location='/pos/add/{{p.id}}'"><img src="{{p.img_url}}"><h6>{{p.nombre}}</h6><small style="color:var(--rosa);font-weight:bold">{{p.precio_mxn}}</small></div>{% endfor %}</div></div>
</div>
<div id="modalEfectivo" class="modal-efectivo"><div class="modal-caja"><h5 style="color:var(--rosa)">Efectivo</h5><div style="background:#0a0a0a;border:1px solid #333;border-radius:10px;padding:12px;margin:15px 0"><div style="display:flex;justify-content:space-between"><span>Total:</span><b id="modalTotal" style="color:var(--rosa)">$0 MXN</b></div></div><input id="cantidadEntregada" type="number" step="0.01" class="form-control" style="background:#000!important;border:2px solid var(--rosa)!important;color:white!important;font-size:22px;text-align:center" oninput="calcularCambio()"><div style="background:#0a1a0f;border:2px solid #25D366;border-radius:10px;padding:12px;margin-top:15px"><b id="modalCambio" style="color:#25D366;font-size:22px">$0.00 MXN</b></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:15px"><button onclick="cerrarEfectivo()" style="background:#333;color:white;border:none;padding:12px;border-radius:8px">Cancelar</button><button onclick="confirmarEfectivo()" style="background:#25D366;color:white;border:none;padding:12px;border-radius:8px">Cobrar</button></div></div></div>
<script>
let totalNum=parseFloat(document.getElementById('totalTicket').dataset.total||0);
function filtrar(cat){document.querySelectorAll('.cat-btn').forEach(function(b){b.classList.remove('active');}); var btn=document.getElementById('btn-'+cat); if(btn) btn.classList.add('active'); document.querySelectorAll('.prod-card').forEach(function(c){if(cat=='todos'||c.dataset.cat==cat) c.style.display='block'; else c.style.display='none';});}
function actualizarTotalHoy(){fetch('/api/total_hoy').then(function(r){return r.json();}).then(function(d){document.getElementById('totalHoy').textContent=d.total_mxn;});}setInterval(actualizarTotalHoy,5000);
function abrirEfectivo(){if(totalNum<=0){alert('Ticket vacio');return;}document.getElementById('modalTotal').textContent='$'+totalNum.toFixed(2)+' MXN';document.getElementById('cantidadEntregada').value=totalNum.toFixed(2);calcularCambio();document.getElementById('modalEfectivo').classList.add('show');}
function cerrarEfectivo(){document.getElementById('modalEfectivo').classList.remove('show');}
function calcularCambio(){var e=parseFloat(document.getElementById('cantidadEntregada').value)||0;document.getElementById('modalCambio').textContent='$'+(e-totalNum).toFixed(2)+' MXN';}
function confirmarEfectivo(){var e=parseFloat(document.getElementById('cantidadEntregada').value)||0;if(e<totalNum){alert('Menor');return;}location.href='/pos/pagar/efectivo?entregado='+e;}
</script>
""", productos=prod_list, carrito=[{'nombre':x.get('nombre',''),'cant':x.get('cant',0),'total_mxn':format_mxn(float(x.get('precio',0))*int(x.get('cant',0)))} for x in carrito], total="{:,.2f}".format(total), total_num=total, total_hoy_mxn=format_mxn(total_hoy), mesas_por_cobrar=[{'id':m.id,'nombre':m.nombre,'total_mxn':format_mxn(m.total or 0)} for m in mesas_por_cobrar], cats=cats)

@app.route('/api/total_hoy')
def api_total_hoy():
    try:
        today=datetime.now().date(); start=datetime(today.year,today.month,today.day)
        total=sum([v.total or 0 for v in Venta.query.filter(Venta.fecha>=start).all()])
    except: total=0
    return jsonify({'total_mxn':format_mxn(total)})

@app.route('/pos/add/<int:id>')
def pos_add(id):
    prod=Producto.query.get(id)
    carrito=session.get('carrito',[])
    for it in carrito:
        if it['id']==prod.id:
            it['cant']+=1
            session['carrito']=carrito
            session.modified=True
            return redirect('/dashboard')
    carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':float(prod.precio or 0),'cant':1})
    session['carrito']=carrito
    session.modified=True
    return redirect('/dashboard')

@app.route('/pos/clear', methods=['POST'])
def pos_clear():
    session['carrito']=[]; session.modified=True; return redirect('/dashboard')

@app.route('/pos/pagar/<metodo>')
def pos_pagar(metodo):
    carrito=session.get('carrito',[])
    if not carrito: return redirect('/dashboard')
    vendedor=session.get('user'); vendedor_nombre=session.get('nombre_completo','')
    last_id=None
    for it in carrito:
        v=Venta(cliente='Mostrador',producto_nombre=it['nombre'],cantidad=it['cant'],total=float(it['precio'])*int(it['cant']),vendedor=vendedor,vendedor_nombre=vendedor_nombre,metodo_pago=metodo)
        db.session.add(v); db.session.flush(); last_id=v.id
    db.session.commit(); session['carrito']=[]; session.modified=True
    return redirect('/ticket/'+str(last_id))

@app.route('/mesas')
def mesas_view():
    mesas=Mesa.query.all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><h5 style="color:var(--rosa)">Mesas - Amarillo = Por cobrar en caja</h5><div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:10px">{% for m in mesas %}<div style="background:{% if m.estado=='por_cobrar' %}#ffeb3b{% elif m.estado=='ocupada' %}#fde8e8{% else %}#e8f5e9{% endif %};color:black;padding:15px;border-radius:10px;text-align:center;cursor:pointer;border:{% if m.estado=='por_cobrar' %}3px solid #ff9800{% else %}none{% endif %}" onclick="location='/mesa/{{m.id}}'"><b>{{m.nombre}}</b><br>{% if m.estado=='por_cobrar' %}POR COBRAR{% else %}{{m.estado}}{% endif %}<br>{{m.total_mxn}}</div>{% endfor %}</div></div>""", mesas=[{'id':m.id,'nombre':m.nombre,'estado':m.estado,'total_mxn':format_mxn(m.total or 0)} for m in mesas])

@app.route('/mesa/<int:id>')
def mesa_detalle(id):
    try:
        cfg=get_config()
        puede_cobrar=session.get('is_admin') or session.get('rol')=='cajero' or getattr(cfg,'mod_mesero_cobrar',False)
        mesa=Mesa.query.get(id)
        if not mesa: return redirect('/mesas')
        all_prods=Producto.query.all()
        productos=[p for p in all_prods if getattr(p,'disponible',True)==True]
        prod_list=[{'id':p.id,'nombre':p.nombre,'precio_mxn':format_mxn(p.precio or 0),'img_url':get_producto_imagen(p)} for p in productos]
        carrito=session.get('mesa_carrito_'+str(id),[])
        if not isinstance(carrito, list): carrito=[]
        total_nuevo=sum([float(x.get('precio',0))*int(x.get('cant',0)) for x in carrito])
        comandas=[c for c in mesa.comandas if c.estado!='entregado']
        return render_template_string(STYLE_BASE+nav()+"""
<div style="display:flex;height:calc(100vh - 60px);gap:10px;padding:10px">
<div style="width:45%;background:#111;border:2px solid #00e5ff;border-radius:12px;padding:10px;overflow:auto;display:flex;flex-direction:column">
<h6 style="color:#00e5ff">{{mesa.nombre}} - {{mesa.total_mxn}} {% if mesa.estado=='por_cobrar' %}<span style="background:#ffeb3b;color:black;padding:2px 6px;border-radius:4px">POR COBRAR</span>{% endif %}</h6>
<div style="flex:1;overflow:auto">
{% for c in comandas %}<div style="background:white;color:black;padding:8px;border-radius:8px;margin-bottom:6px;font-size:12px;display:flex;justify-content:space-between"><div><b>{{c.cantidad}}x {{c.producto_nombre}}</b> {% if c.comentario %}<span style="background:red;color:white;padding:2px 4px;border-radius:4px">{{c.comentario}}</span>{% endif %}<br><small>{{c.estado}} - {{c.mesero_nombre}}</small></div><a href="/mesa/{{mesa.id}}/comanda/eliminar/{{c.id}}" style="background:var(--rosa);color:white;padding:6px 10px;border-radius:6px;text-decoration:none">Quitar</a></div>{% endfor %}
<hr><b style="color:#ffcc00">Nuevo</b>
{% for it in carrito %}<div style="background:#fffde7;color:black;padding:5px;border-radius:4px;margin-top:5px;font-size:12px;display:flex;justify-content:space-between"><span>{{it.nombre}} x{{it.cant}} - {{it.total_mxn}}</span><a href="/mesa/{{mesa.id}}/carrito/eliminar/{{loop.index0}}" style="color:var(--rosa)">X</a></div><form action="/mesa/{{mesa.id}}/carrito/coment/{{loop.index0}}" method="POST" style="display:flex;gap:3px;margin-top:3px"><input name="comentario" value="{{it.comentario}}" class="form-control" style="font-size:11px" placeholder="Comentario"><button style="background:var(--rosa);color:white;border:none;border-radius:4px;padding:4px 8px">OK</button></form>{% endfor %}
</div>
<div style="border-top:2px solid var(--rosa);padding-top:10px"><b>Total Final {{total_final_mxn}}</b><br><a href="/mesa/{{mesa.id}}/enviar" style="background:#00e5ff;color:black;padding:8px;display:block;text-align:center;border-radius:6px;margin-top:5px;text-decoration:none">MANDAR A COCINA</a>
{% if puede_cobrar %}<a href="/mesa/{{mesa.id}}/cobrar" style="background:#25D366;color:white;padding:10px;display:block;text-align:center;border-radius:6px;margin-top:5px;font-weight:bold;text-decoration:none">COBRAR MESA (CAJA)</a>
{% else %}<a href="/mesa/{{mesa.id}}/solicitar_cuenta" style="background:#ffeb3b;color:black;padding:10px;display:block;text-align:center;border-radius:6px;margin-top:5px;font-weight:bold;border:2px solid #ff9800;text-decoration:none">SOLICITAR CUENTA A CAJA</a>{% endif %}
</div></div>
<div style="width:55%;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;overflow:auto">{% for p in productos %}<div style="background:white;color:#333;border-radius:8px;padding:6px;text-align:center;cursor:pointer" onclick="location='/mesa/{{mesa.id}}/add/{{p.id}}'"><img src="{{p.img_url}}" style="width:60px;height:60px;object-fit:cover;border-radius:6px"><br><small>{{p.nombre}}</small><br><small style="color:var(--rosa);font-weight:bold">{{p.precio_mxn}}</small></div>{% endfor %}</div>
</div>
""", mesa={'id':mesa.id,'nombre':mesa.nombre,'total_mxn':format_mxn(mesa.total or 0),'estado':mesa.estado}, productos=prod_list, carrito=[{'nombre':x.get('nombre',''),'cant':x.get('cant',0),'comentario':x.get('comentario',''),'total_mxn':format_mxn(float(x.get('precio',0))*int(x.get('cant',0)))} for x in carrito], comandas=comandas, total_final_mxn=format_mxn((mesa.total or 0)+total_nuevo), puede_cobrar=puede_cobrar)
    except Exception as e:
        return "<h3>Error mesa "+str(id)+"</h3><pre>"+traceback.format_exc()+"</pre><a href='/mesas'>Volver</a>"

@app.route('/mesa/<int:mesa_id>/add/<int:prod_id>')
def mesa_add(mesa_id, prod_id):
    prod=Producto.query.get(prod_id)
    if not prod: return redirect('/mesa/'+str(mesa_id))
    key='mesa_carrito_'+str(mesa_id)
    carrito=session.get(key,[])
    if not isinstance(carrito, list): carrito=[]
    carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':float(prod.precio or 0),'cant':1,'comentario':''})
    session[key]=carrito; session.modified=True
    return redirect('/mesa/'+str(mesa_id))

@app.route('/mesa/<int:mesa_id>/carrito/coment/<int:index>', methods=['POST'])
def mesa_carrito_coment(mesa_id,index):
    key='mesa_carrito_'+str(mesa_id); carrito=session.get(key,[])
    if 0 <= index < len(carrito):
        carrito[index]['comentario']=request.form.get('comentario','')[:200]
        session[key]=carrito; session.modified=True
    return redirect('/mesa/'+str(mesa_id))

@app.route('/mesa/<int:mesa_id>/carrito/eliminar/<int:index>')
def mesa_carrito_eliminar(mesa_id,index):
    key='mesa_carrito_'+str(mesa_id); carrito=session.get(key,[])
    if 0 <= index < len(carrito):
        carrito.pop(index); session[key]=carrito; session.modified=True
    return redirect('/mesa/'+str(mesa_id))

@app.route('/mesa/<int:mesa_id>/comanda/eliminar/<int:comanda_id>')
def mesa_comanda_eliminar(mesa_id, comanda_id):
    mesa=Mesa.query.get(mesa_id); com=Comanda.query.get(comanda_id)
    if not mesa or not com: return redirect('/mesa/'+str(mesa_id))
    try:
        prod=Producto.query.filter_by(nombre=com.producto_nombre).first()
        mesa.total=max(0,(mesa.total or 0)-(prod.precio if prod else 0)*(com.cantidad or 1))
    except: pass
    db.session.delete(com); db.session.commit()
    if len([c for c in mesa.comandas if c.estado!='entregado'])==0 and (mesa.total or 0)<=0:
        mesa.estado='libre'; mesa.total=0; db.session.commit()
        return redirect('/mesas')
    return redirect('/mesa/'+str(mesa_id))

@app.route('/mesa/<int:mesa_id>/enviar')
def mesa_enviar(mesa_id):
    mesa=Mesa.query.get(mesa_id); key='mesa_carrito_'+str(mesa_id); carrito=session.get(key,[])
    mesero=session.get('user'); mesero_nombre=session.get('nombre_completo','')
    for it in carrito:
        com=Comanda(mesa_id=mesa.id,producto_nombre=it['nombre'],cantidad=it['cant'],mesero=mesero,mesero_nombre=mesero_nombre,estado='cocina',comentario=it.get('comentario',''))
        mesa.total=(mesa.total or 0)+float(it.get('precio',0))*int(it.get('cant',0)); mesa.estado='ocupada'; db.session.add(com)
    db.session.commit(); session[key]=[]; session.modified=True
    return redirect('/mesa/'+str(mesa_id))

@app.route('/mesa/<int:id>/solicitar_cuenta')
def mesa_solicitar_cuenta(id):
    mesa=Mesa.query.get(id)
    if mesa and mesa.estado!='libre':
        mesa.estado='por_cobrar'; db.session.commit()
    return redirect('/mesas')

@app.route('/mesa/<int:id>/cobrar')
def mesa_cobrar_view(id):
    cfg=get_config(); mesa=Mesa.query.get(id)
    if not mesa: return redirect('/mesas')
    if not session.get('is_admin') and session.get('rol')=='mesero' and not getattr(cfg,'mod_mesero_cobrar',False):
        mesa.estado='por_cobrar'; db.session.commit()
        return redirect('/mesas')
    comandas=[c for c in mesa.comandas if c.estado!='entregado']
    return render_template_string(STYLE_BASE+nav()+"""
<div class="container mt-3" style="max-width:700px"><div class="card" style="border-color:#ffeb3b"><h4 style="color:#ffeb3b">Cobro de {{mesa.nombre}} - {{total_mxn}}</h4>
<div style="background:white;color:black;border-radius:8px;padding:12px;margin-top:10px">
<table class="table table-sm"><tr><th>Cant</th><th>Producto</th></tr>{% for c in comandas %}<tr><td>{{c.cantidad}}</td><td>{{c.producto_nombre}} {% if c.comentario %}<small style="color:red">({{c.comentario}})</small>{% endif %}</td></tr>{% endfor %}</table><b>TOTAL {{total_mxn}}</b></div>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:15px">
<a href="/mesa/{{mesa.id}}/cobrar_final/efectivo" style="background:#25D366;color:white;padding:18px;text-align:center;border-radius:10px;text-decoration:none">Efectivo</a>
<a href="/mesa/{{mesa.id}}/cobrar_final/tarjeta" style="background:#3f51b5;color:white;padding:18px;text-align:center;border-radius:10px;text-decoration:none">Tarjeta</a>
<a href="/mesa/{{mesa.id}}/cobrar_final/transferencia" style="background:#0097a7;color:white;padding:18px;text-align:center;border-radius:10px;text-decoration:none">Transfer</a>
</div></div></div>
""", mesa={'id':mesa.id,'nombre':mesa.nombre}, total_mxn=format_mxn(mesa.total or 0), comandas=comandas)

@app.route('/mesa/<int:id>/cobrar_final/<metodo>')
def mesa_cobrar_final(id,metodo):
    mesa=Mesa.query.get(id); vendedor=session.get('user'); vendedor_nombre=session.get('nombre_completo','')
    for c in list(mesa.comandas):
        if c.estado!='entregado':
            prod=Producto.query.filter_by(nombre=c.producto_nombre).first(); precio=prod.precio if prod else 0
            v=Venta(cliente=mesa.nombre,producto_nombre=c.producto_nombre+( " ("+c.comentario+")" if c.comentario else ""),cantidad=c.cantidad,total=precio*c.cantidad,vendedor=vendedor,vendedor_nombre=vendedor_nombre,metodo_pago=metodo); db.session.add(v); c.estado='entregado'
    mesa.estado='libre'; mesa.total=0; db.session.commit()
    return redirect('/mesas')

@app.route('/cocina')
def cocina_view():
    comandas=Comanda.query.filter_by(estado='cocina').all()
    from collections import defaultdict
    grupos=defaultdict(list)
    for c in comandas: grupos[c.mesa_id].append(c)
    grupos_list=[]
    for mid,lista in grupos.items():
        m=Mesa.query.get(mid)
        if m: grupos_list.append({'mesa':m,'comandas':lista})
    return render_template_string(STYLE_BASE+nav()+"""<div class="container-fluid mt-3"><h3 style="color:#ffcc00">Cocina - {{grupos_list|length}} mesas</h3><div class="row g-3">{% for g in grupos_list %}<div class="col-md-4"><div class="card"><h5 style="color:#00e5ff">{{g.mesa.nombre}}</h5>{% for c in g.comandas %}<div style="background:white;color:black;padding:6px;border-radius:6px;margin-bottom:5px"><b>{{c.cantidad}}x {{c.producto_nombre}}</b>{% if c.comentario %}<span style="background:red;color:white;padding:2px 6px;border-radius:4px">{{c.comentario}}</span>{% endif %}</div>{% endfor %}<a href="/cocina/mesa_listo/{{g.mesa.id}}" style="background:#25D366;color:white;padding:8px;display:block;text-align:center;border-radius:6px;text-decoration:none">MESA LISTA</a></div></div>{% endfor %}</div></div>""", grupos_list=[{'mesa':{'id':g['mesa'].id,'nombre':g['mesa'].nombre},'comandas':g['comandas']} for g in grupos_list])

@app.route('/cocina/mesa_listo/<int:mesa_id>')
def cocina_mesa_listo(mesa_id):
    mesa=Mesa.query.get(mesa_id)
    for c in mesa.comandas:
        if c.estado=='cocina': c.estado='listo'
    db.session.commit()
    return redirect('/cocina')

@app.route('/productos')
def productos_list():
    if not session.get('is_admin'): return redirect('/dashboard')
    productos=Producto.query.all()
    lista=[{'id':p.id,'nombre':p.nombre,'categoria':getattr(p,'categoria',''),'img_url':get_producto_imagen(p),'precio_mxn':format_mxn(p.precio or 0),'stock':getattr(p,'stock',0)} for p in productos]
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div style="background:white;color:#333;border-radius:8px;padding:15px"><h4 style="color:black">Productos ({{productos|length}}) {% if cloudinary_enabled %}<small style="background:#25D366;color:white;padding:3px 8px;border-radius:10px;font-size:10px">Cloudinary Activo</small>{% endif %}</h4><a href="/productos/nuevo" style="background:var(--rosa);color:white;padding:8px 16px;border-radius:4px;text-decoration:none">+ Crear</a><table class="table mt-3"><tr><th>Foto</th><th>Nombre</th><th>Precio</th><th>Acciones</th></tr>{% for p in productos %}<tr><td><img src="{{p.img_url}}" style="width:45px;height:45px;object-fit:cover"></td><td>{{p.nombre}}</td><td>{{p.precio_mxn}}</td><td><a href="/productos/editar/{{p.id}}">Editar</a> <a href="/productos/eliminar/{{p.id}}">Borrar</a></td></tr>{% endfor %}</table></div></div>""", productos=lista, cloudinary_enabled=CLOUDINARY_ENABLED)

@app.route('/productos/nuevo', methods=['GET','POST'])
def productos_nuevo():
    if not session.get('is_admin'): return redirect('/dashboard')
    if request.method=='POST':
        img=save_upload(request.files['imagen']) if 'imagen' in request.files else ""
        p=Producto(nombre=request.form.get('nombre','').strip() or 'Sin nombre',categoria=request.form.get('categoria','Sin categoria'),precio=float(request.form.get('precio') or 0),stock=int(request.form.get('stock') or 0),imagen=img)
        db.session.add(p); db.session.commit(); return redirect('/productos')
    cats=Categoria.query.all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card"><h5>Crear articulo</h5><form method="POST" enctype="multipart/form-data"><input name="nombre" class="form-control mb-2" placeholder="Nombre" required><select name="categoria" class="form-control mb-2">{% for c in cats %}<option>{{c.nombre}}</option>{% endfor %}</select><input name="precio" type="number" step="0.01" class="form-control mb-2" placeholder="Precio" required><input name="stock" type="number" class="form-control mb-2" value="0"><input name="imagen" type="file" class="form-control mb-2" accept="image/*"><button class="btn-rosa">Guardar</button></form></div></div>""", cats=cats)

@app.route('/productos/editar/<int:id>', methods=['GET','POST'])
def productos_editar(id):
    if not session.get('is_admin'): return redirect('/dashboard')
    p=Producto.query.get(id)
    if not p: return redirect('/productos')
    if request.method=='POST':
        if 'imagen' in request.files and request.files['imagen'].filename:
            nueva=save_upload(request.files['imagen'])
            if nueva: p.imagen=nueva
        p.nombre=request.form.get('nombre','').strip() or p.nombre
        p.precio=float(request.form.get('precio') or 0)
        p.stock=int(request.form.get('stock') or 0)
        db.session.commit()
        return redirect('/productos')
    return render_template_string(STYLE_BASE+nav()+"""
<div class="container mt-3"><div class="card"><h5>Editar """+p.nombre+"""</h5><form method="POST" enctype="multipart/form-data"><input name="nombre" class="form-control mb-2" value=\""""+p.nombre+"""\" required><input name="precio" type="number" step="0.01" class="form-control mb-2" value=\""""+str(p.precio or 0)+"""\"><input name="stock" type="number" class="form-control mb-2" value=\""""+str(p.stock or 0)+"""\"><p>Actual: <img src=\""""+get_producto_imagen(p)+"""\" style="width:60px;height:60px"></p><input name="imagen" type="file" class="form-control mb-2" accept="image/*"><button class="btn-rosa">Guardar cambios</button></form></div></div>
""")

@app.route('/productos/eliminar/<int:id>')
def eliminar_producto(id):
    p=Producto.query.get(id)
    if p: db.session.delete(p); db.session.commit()
    return redirect('/productos')

@app.route('/admin/config', methods=['GET','POST'])
def admin_config():
    if not session.get('is_admin'): return redirect('/dashboard')
    cfg=get_config()
    if request.method=='POST':
        if 'logo' in request.files and request.files['logo'].filename:
            nl=save_upload(request.files['logo'])
            if nl: cfg.logo_path=nl
        cfg.mod_pos_mesero='mod_pos_mesero' in request.form
        cfg.mod_mesero_cobrar='mod_mesero_cobrar' in request.form
        db.session.commit()
        return redirect('/admin/config')
    logo=get_producto_imagen(cfg)
    c1="checked" if getattr(cfg,'mod_pos_mesero',False) else ""
    c2="checked" if getattr(cfg,'mod_mesero_cobrar',False) else ""
    return render_template_string(STYLE_BASE+nav()+'<div class="container mt-3"><div class="card"><h5>Config + Logo</h5><img src="'+logo+'" style="width:80px;height:80px;border-radius:50%;background:white;padding:5px"><form method="POST" enctype="multipart/form-data" class="mt-3"><input name="logo" type="file" class="form-control mb-2"><label><input type="checkbox" name="mod_pos_mesero" '+c1+'> POS mesero</label><br><label><input type="checkbox" name="mod_mesero_cobrar" '+c2+'> <b>Permitir mesero cobrar directo (si no, solo solicita a caja)</b></label><br><button class="btn-rosa mt-2">Guardar</button></form></div></div>')

@app.route('/ticket/<int:id>')
def ticket(id):
    v=Venta.query.get(id)
    if not v: return redirect('/dashboard')
    return render_template_string(STYLE_BASE+nav()+'<div class="container mt-3"><div class="card" style="background:white;color:black"><h5>Ticket #'+str(v.id)+'</h5><p>'+v.producto_nombre+' - '+format_mxn(v.total)+'<br>'+v.metodo_pago+'</p><a href="/dashboard" class="btn-rosa">Volver</a></div></div>')

@app.route('/ventas')
def ventas():
    vs=Venta.query.order_by(Venta.id.desc()).limit(200).all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card"><h5>Ventas</h5><table class="table table-dark table-sm"><tr><th>ID</th><th>Producto</th><th>Total</th><th>Accion</th></tr>{% for v in vs %}<tr><td>{{v.id}}</td><td>{{v.producto_nombre}} x{{v.cantidad}}</td><td>{{v.total_mxn}}</td><td><a href="/ventas/eliminar/{{v.id}}" style="color:var(--rosa)">Eliminar</a></td></tr>{% endfor %}</table></div></div>""", vs=[{'id':v.id,'producto_nombre':v.producto_nombre,'cantidad':v.cantidad,'total_mxn':format_mxn(v.total)} for v in vs])

@app.route('/ventas/eliminar/<int:id>')
def ventas_eliminar(id):
    v=Venta.query.get(id)
    if v: db.session.delete(v); db.session.commit()
    return redirect('/ventas')

@app.route('/admin/usuarios')
def admin_usuarios():
    if not session.get('is_admin'): return redirect('/dashboard')
    usuarios=User.query.all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card"><h5>Usuarios</h5><table class="table table-dark"><tr><th>Nombre</th><th>Usuario</th><th>Rol</th></tr>{% for u in usuarios %}<tr><td>{{u.nombre_completo}}</td><td>{{u.username}}</td><td>{{u.rol}}</td></tr>{% endfor %}</table></div></div>""", usuarios=usuarios)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/total_hoy')
def api_total_hoy():
    try:
        today=datetime.now().date(); start=datetime(today.year,today.month,today.day)
        total=sum([v.total or 0 for v in Venta.query.filter(Venta.fecha>=start).all()])
    except: total=0
    return jsonify({'total_mxn':format_mxn(total)})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))