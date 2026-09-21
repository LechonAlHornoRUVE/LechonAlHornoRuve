from flask import Flask, request, redirect, session, render_template_string, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'ruve-login-centrado-reset-pass'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXT = {'png','jpg','jpeg','webp'}

db_url = os.environ.get('DATABASE_URL', 'sqlite:///lechon.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'usuarios'
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True)
    nombre_completo=db.Column(db.String(100), default="")
    password=db.Column(db.String(200))
    is_admin=db.Column(db.Boolean, default=False)
    rol=db.Column(db.String(20), default="cajero")
class Categoria(db.Model):
    __tablename__ = 'categorias'
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(50), unique=True)
class Producto(db.Model):
    __tablename__ = 'productos'
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(100))
    precio=db.Column(db.Float, default=0)
    stock=db.Column(db.Integer, default=0)
    imagen=db.Column(db.String(200), default="")
    descripcion=db.Column(db.Text, default="")
    categoria=db.Column(db.String(50), default="Sin categoria")
    disponible=db.Column(db.Boolean, default=True)
class Venta(db.Model):
    __tablename__ = 'ventas'
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
    __tablename__ = 'gastos'
    id=db.Column(db.Integer, primary_key=True)
    concepto=db.Column(db.String(100))
    monto=db.Column(db.Float)
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
class Config(db.Model):
    __tablename__ = 'config'
    id=db.Column(db.Integer, primary_key=True)
    logo_path=db.Column(db.String(200), default="logo.png")
    mod_pos_mesero=db.Column(db.Boolean, default=False)
class Mesa(db.Model):
    __tablename__ = 'mesas'
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(50))
    estado=db.Column(db.String(20), default="libre")
    total=db.Column(db.Float, default=0)
class Comanda(db.Model):
    __tablename__ = 'comandas'
    id=db.Column(db.Integer, primary_key=True)
    mesa_id=db.Column(db.Integer, db.ForeignKey('mesas.id'))
    producto_nombre=db.Column(db.String(100))
    cantidad=db.Column(db.Integer)
    estado=db.Column(db.String(20), default="cocina")
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    mesero=db.Column(db.String(80))
    mesero_nombre=db.Column(db.String(100), default="")
    comentario=db.Column(db.String(200), default="")
    mesa = db.relationship('Mesa', backref='comandas', foreign_keys=[mesa_id])

def get_config():
    c=Config.query.first()
    if not c: c=Config(); db.session.add(c); db.session.commit()
    return c
def save_upload(file):
    if file and file.filename and '.' in file.filename and file.filename.rsplit('.',1)[1].lower() in ALLOWED_EXT:
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        return f"uploads/{filename}"
    return ""
def get_producto_imagen(p):
    if p and p.imagen: return f"/static/{p.imagen}"
    cfg=get_config(); return f"/static/{cfg.logo_path}"
def format_mxn(n):
    try: return f"${float(n):,.2f} MXN"
    except: return "$0.00 MXN"

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin',nombre_completo='Administrador General',password=generate_password_hash('admin123'),is_admin=True,rol='admin'))
        db.session.commit()
    if Categoria.query.count()==0:
        for cat in ["Sin categoría","Lechón","Tortas","Órdenes","Bebidas","Extras"]:
            if not Categoria.query.filter_by(nombre=cat).first():
                db.session.add(Categoria(nombre=cat))
        db.session.commit()
    if Mesa.query.count()==0:
        for i in range(1,13): db.session.add(Mesa(nombre=f"Mesa {i}"))
        db.session.commit()

STYLE_BASE = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#000;color:white;font-family:Arial;margin:0}
.card{background:#111;border:2px solid #ff4d8a;border-radius:15px;padding:20px}
.btn-rosa{background:#ff4d8a;color:white;border:none;padding:10px 18px;border-radius:10px;font-weight:bold}
.navbar{background:#000!important;border-bottom:2px solid #ff4d8a;display:flex;justify-content:space-between;align-items:center;padding:10px 15px;flex-wrap:wrap}
.pos-container{display:flex;height:calc(100vh - 60px);gap:10px;padding:10px}
.pos-left{width:38%;background:#0f0f0f;border:2px solid #ff4d8a;border-radius:15px;display:flex;flex-direction:column}
.pos-center{width:12%;display:flex;flex-direction:column;gap:8px;overflow-y:auto}
.pos-right{width:50%;background:#0f0f0f;border:2px solid #333;border-radius:15px;padding:10px;overflow-y:auto}
.cat-btn{background:#222;color:white;font-weight:bold;padding:14px;border:2px solid #333;border-radius:8px;cursor:pointer;text-align:center;font-size:12px}
.cat-btn.active{background:#ff4d8a;border-color:#ff4d8a}
.prod-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.prod-card{background:#1a1a1a;border:2px solid #333;border-radius:12px;padding:10px;text-align:center;cursor:pointer}
.prod-card:hover{border-color:#ff4d8a}
.prod-card img{width:70px;height:70px;object-fit:cover;border-radius:10px;background:white;padding:5px}
.prod-card h6{color:#ff4d8a;margin:8px 0 2px 0;font-size:12px}
.ticket-header{background:#111;padding:12px;border-bottom:2px solid #ff4d8a;border-radius:15px 15px 0 0}
.ticket-body{flex:1;overflow-y:auto;padding:10px;background:white;color:black}
.ticket-footer{background:#111;padding:12px;border-top:2px solid #ff4d8a;border-radius:0 0 15px 15px}
.btn-cash{background:#25D366;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:32%}
.btn-pay{background:#3f51b5;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:32%}
.btn-trans{background:#0097a7;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:32%}
.btn-clear{background:#333;color:white;border:1px solid #555;width:100%;padding:10px;border-radius:8px;margin-top:8px;font-weight:bold}
.dropdown{position:relative;display:inline-block}
.dropbtn{background:#111;color:#ff4d8a;border:2px solid #ff4d8a;padding:6px 14px;border-radius:8px;font-weight:bold;cursor:pointer}
.dropdown-content{display:none;position:absolute;right:0;background:#111;border:2px solid #ff4d8a;border-radius:10px;min-width:230px;z-index:9999}
.dropdown-content a{display:block;padding:12px 16px;color:white;text-decoration:none;font-size:13px;border-bottom:1px solid #222}
.dropdown-content a:hover{background:#222;color:#ff4d8a}
.dropdown-content.show{display:block}
.input-rosa{border:none!important;border-bottom:2px solid #ff4d8a!important;background:#111!important;color:white!important;border-radius:0!important;padding:10px 0!important;width:100%}
.label-rosa{font-size:11px;color:#ff4d8a;margin-top:18px;display:block;font-weight:bold;letter-spacing:0.5px}
.select-rosa{background:#111!important;color:white!important;border:2px solid #ff4d8a!important;border-radius:8px!important;padding:8px!important}
.card-negra{background:#111;border:2px solid #ff4d8a;border-radius:12px;padding:20px;margin:15px;box-shadow:0 0 15px rgba(255,77,138,0.25)}
.header-rosa-negro{background:#000;border-bottom:3px solid #ff4d8a;color:#ff4d8a;padding:14px 20px;display:flex;align-items:center;font-weight:bold;font-size:18px;letter-spacing:1px}
</style>
"""

def nav():
    cfg=get_config(); rol=session.get('rol','cajero'); is_admin=session.get('is_admin', False); nombre=session.get('nombre_completo') or session.get('user','')
    logo_url=f"/static/{cfg.logo_path}"
    if not is_admin and rol=='cocina':
        return f'<nav class="navbar"><div class="d-flex align-items-center"><img src="{logo_url}" style="width:40px;height:40px;border-radius:50%;background:white;padding:3px;object-fit:cover"><h6 class="m-0 ms-2" style="color:#ffcc00">Cocina {nombre}</h6></div><div><a href="/cocina" class="me-3" style="color:#ffcc00">🔥 Cocina</a><a href="/logout">Salir</a></div></nav>'
    links=""
    if is_admin or rol=='cajero': links+='<a href="/dashboard" class="me-3">POS</a>'
    if rol=='mesero' and cfg.mod_pos_mesero: links+='<a href="/dashboard" class="me-3">POS</a>'
    if is_admin or rol in ['cajero','mesero']: links+='<a href="/mesas" class="me-3" style="color:#00e5ff">🪑 Mesas</a>'
    if is_admin or rol=='cajero': links+='<a href="/cocina" class="me-3" style="color:#ffcc00">🔥 Cocina</a>'
    admin_drop=""
    if is_admin:
        admin_drop=f'''
        <div class="dropdown">
          <button onclick="toggleDropdown()" class="dropbtn">⚙️ Herramientas admin ▾</button>
          <div id="adminDropdown" class="dropdown-content">
            <a href="/productos">📦 Productos</a>
            <a href="/productos/nuevo">➕ Crear artículo</a>
            <a href="/admin/mesas">🪑 Mesas</a>
            <a href="/ventas">🧾 Ventas</a>
            <a href="/dueno">💰 Dueño + Gráfica</a>
            <a href="/admin/config">⚙️ Config + Logo</a>
            <a href="/admin/usuarios">👥 Usuarios</a>
          </div>
        </div>
        <script>function toggleDropdown(){{document.getElementById("adminDropdown").classList.toggle("show");}} window.onclick=function(e){{if(!e.target.matches('.dropbtn')){{var d=document.getElementById("adminDropdown"); if(d && d.classList.contains('show')) d.classList.remove('show');}}}}</script>
        '''
    return f'<nav class="navbar"><div class="d-flex align-items-center"><img src="{logo_url}" style="width:40px;height:40px;border-radius:50%;background:white;padding:3px;object-fit:cover"><h6 class="m-0 ms-2" style="color:#ff4d8a">Ruve {nombre}</h6><span id="relojPC" style="margin-left:12px;color:#ff4d8a;font-size:10px;font-weight:700"></span></div><div>{links}{admin_drop}<a href="/logout" class="ms-3">Salir</a></div></nav><script>function actualizarReloj(){{let a=new Date(); let el=document.getElementById("relojPC"); if(el) el.textContent=a.toLocaleString("es-MX",{{hour12:false,timeZone:"America/Cancun"}})}};setInterval(actualizarReloj,1000);actualizarReloj();</script>'

# --- LOGIN CENTRADO PERFECTO + RESTABLECER ---
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
    return render_template_string(STYLE_BASE+f"""
<div style="min-height:100vh;display:flex;justify-content:center;align-items:center;background:#000;padding:20px">
    <div class="card" style="width:100%;max-width:380px;text-align:center;padding:30px 25px">
        <div style="display:flex;justify-content:center;align-items:center;margin-bottom:15px">
            <img src="/static/{cfg.logo_path}" style="width:130px;height:130px;object-fit:cover;border-radius:50%;background:white;padding:5px;border:3px solid #ff4d8a;display:block;margin:0 auto">
        </div>
        <h3 style="color:#ff4d8a;font-weight:bold;margin:10px 0 20px 0;text-align:center">Ruve</h3>
        {"<div style='background:#2a1018;border:1px solid #ff4d8a;color:#ff4d8a;padding:8px;border-radius:8px;font-size:12px;margin-bottom:10px'>"+error+"</div>" if error else ""}
        <form method="POST" style="text-align:left">
            <input name="username" class="form-control mb-3" placeholder="Usuario" required style="background:white!important;color:#333!important;border:none!important;padding:12px;border-radius:8px">
            <input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required style="background:white!important;color:#333!important;border:none!important;padding:12px;border-radius:8px">
            <button class="btn-rosa w-100" style="padding:12px;font-size:15px;border-radius:10px">Entrar</button>
        </form>
        <div style="margin-top:15px;text-align:center">
            <a href="/restablecer" style="color:#ff4d8a;font-size:12px;text-decoration:none">¿Olvidaste tu contraseña? Restablecer</a>
        </div>
    </div>
</div>
""")

@app.route('/restablecer', methods=['GET','POST'])
def restablecer():
    cfg=get_config()
    msg=None; error=None
    if request.method=='POST':
        username=request.form.get('username','').strip()
        nueva=request.form.get('nueva','').strip()
        confirmar=request.form.get('confirmar','').strip()
        u=User.query.filter_by(username=username).first()
        if not u:
            error="Usuario no encontrado"
        elif nueva!=confirmar:
            error="Las contraseñas no coinciden"
        elif len(nueva)<4:
            error="La contraseña debe tener mínimo 4 caracteres"
        else:
            u.password=generate_password_hash(nueva)
            db.session.commit()
            msg=f"Contraseña de {u.nombre_completo} ({u.username}) restablecida correctamente. Ya puedes ingresar."
    return render_template_string(STYLE_BASE+f"""
<div style="min-height:100vh;display:flex;justify-content:center;align-items:center;background:#000;padding:20px">
    <div class="card" style="width:100%;max-width:400px;text-align:center;padding:25px">
        <div style="display:flex;justify-content:center;margin-bottom:10px">
            <img src="/static/{cfg.logo_path}" style="width:90px;height:90px;border-radius:50%;background:white;padding:4px;border:2px solid #ff4d8a">
        </div>
        <h5 style="color:#ff4d8a;font-weight:bold">Restablecer Contraseña</h5>
        {"<div style='background:#101a14;border:1px solid #25D366;color:#25D366;padding:8px;border-radius:8px;font-size:12px;margin:10px 0'>"+msg+"</div>" if msg else ""}
        {"<div style='background:#2a1018;border:1px solid #ff4d8a;color:#ff4d8a;padding:8px;border-radius:8px;font-size:12px;margin:10px 0'>"+error+"</div>" if error else ""}
        <form method="POST" class="text-start mt-3">
            <label class="label-rosa">Usuario</label>
            <input name="username" class="form-control mb-2" placeholder="Ej: admin" required style="background:#000!important;border:1.5px solid #ff4d8a!important">
            <label class="label-rosa">Nueva Contraseña</label>
            <input name="nueva" type="password" class="form-control mb-2" placeholder="Nueva contraseña" required style="background:#000!important;border:1.5px solid #ff4d8a!important">
            <label class="label-rosa">Confirmar Contraseña</label>
            <input name="confirmar" type="password" class="form-control mb-3" placeholder="Confirmar" required style="background:#000!important;border:1.5px solid #ff4d8a!important">
            <button class="btn-rosa w-100">Restablecer</button>
        </form>
        <div style="margin-top:12px"><a href="/" style="color:#888;font-size:12px">← Volver al login</a></div>
        <p style="font-size:10px;color:#555;margin-top:10px">Si no recuerdas tu usuario, pide al admin que lo verifique en Usuarios</p>
    </div>
</div>
""")

# --- POS, MESAS, COCINA, PRODUCTOS (MISMO DISEÑO ORIGINAL) ---
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    cfg=get_config(); rol=session.get('rol'); is_admin=session.get('is_admin')
    if not is_admin and rol=='mesero' and not cfg.mod_pos_mesero: return redirect('/mesas')
    if not is_admin and rol=='cocina': return redirect('/cocina')
    productos=Producto.query.filter_by(disponible=True).all()
    for p in productos: p.img_url=get_producto_imagen(p)
    carrito=session.get('carrito',[]); total=sum([x['precio']*x['cant'] for x in carrito])
    mesas_ocupadas=Mesa.query.filter_by(estado='ocupada').all()
    cats=Categoria.query.all()
    return render_template_string(STYLE_BASE+nav()+"""
<div class="pos-container">
    <div class="pos-left">
        <div class="ticket-header"><small style="color:#ff4d8a;font-weight:bold">TICKET - MOSTRADOR</small><small id="fechaPOS" style="color:#888;font-size:10px"></small></div>
        <div class="ticket-body">
            {% for item in carrito %}<div style="display:flex;justify-content:space-between;border-bottom:1px dashed #ccc;padding:6px 0;font-size:12px"><span>{{item.nombre}} x{{item.cant}}</span><span>{{item.total_mxn}}</span></div>{% endfor %}
            {% if not carrito %}<p style="color:#888;text-align:center;margin-top:20px;font-size:12px">Toca un producto →</p>{% endif %}
            {% if mesas_ocupadas %}<hr><div style="background:#fff3cd;color:black;padding:6px;border-radius:6px;font-size:10px"><b>MESAS POR COBRAR:</b>{% for m in mesas_ocupadas %}<div style="display:flex;justify-content:space-between"><span>{{m.nombre}} {{m.total_mxn}}</span><a href="/mesa/{{m.id}}/cobrar" style="background:#25D366;color:white;padding:2px 6px;border-radius:4px">Cobrar</a></div>{% endfor %}</div>{% endif %}
        </div>
        <div class="ticket-footer">
            <div style="display:flex;justify-content:space-between;color:white;font-weight:bold;font-size:18px"><span>TOTAL</span><span>${{total}} MXN</span></div>
            <div style="display:flex;gap:6px;margin-top:10px">
                <button onclick="pagar('efectivo')" class="btn-cash">💵 Efectivo</button>
                <button onclick="pagar('tarjeta')" class="btn-pay">💳 Tarjeta</button>
                <button onclick="pagar('transferencia')" class="btn-trans">🏦 Transfer</button>
            </div>
            <form method="POST" action="/pos/clear"><button type="submit" class="btn-clear">🗑️ LIMPIAR TICKET</button></form>
        </div>
    </div>
    <div class="pos-center">
        <button class="cat-btn active" onclick="filtrar('todos')" id="btn-todos">Todos</button>
        {% for cat in cats %}<button class="cat-btn" onclick="filtrar('{{cat.nombre}}')" id="btn-{{cat.nombre}}">{{cat.nombre}}</button>{% endfor %}
    </div>
    <div class="pos-right">
        <div class="prod-grid">
            {% for p in productos %}
            <div class="prod-card" data-cat="{{p.categoria}}" onclick="location='/pos/add/{{p.id}}'">
                <img src="{{p.img_url}}"><h6>{{p.nombre}}</h6><small style="color:#ff4d8a;font-weight:bold">{{p.precio_mxn}}</small><br><small style="color:#888;font-size:10px">{{p.categoria}} | {{p.stock}}</small>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
<script>
function filtrar(cat){document.querySelectorAll('.cat-btn').forEach(b=>b.classList.remove('active'));let btn=document.getElementById('btn-'+cat); if(btn) btn.classList.add('active');document.querySelectorAll('.prod-card').forEach(c=>{if(cat=='todos'||c.dataset.cat==cat)c.style.display='block';else c.style.display='none';})}
function pagar(tipo){fetch('/pos/pagar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tipo:tipo})}).then(r=>r.json()).then(d=>{if(d.ok)location='/ticket/'+d.ticket_id})}
document.getElementById('fechaPOS').textContent=new Date().toLocaleString('es-MX',{timeZone:'America/Cancun'});
</script>
""", productos=[{'id':p.id,'nombre':p.nombre,'categoria':p.categoria,'stock':p.stock,'img_url':p.img_url,'precio_mxn':format_mxn(p.precio)} for p in productos], carrito=[{'nombre':x['nombre'],'cant':x['cant'],'total_mxn':format_mxn(x['precio']*x['cant'])} for x in carrito], total=f"{total:,.2f}", mesas_ocupadas=[{'id':m.id,'nombre':m.nombre,'total_mxn':format_mxn(m.total or 0)} for m in mesas_ocupadas], cats=cats)

@app.route('/pos/add/<int:id>')
def pos_add(id):
    prod=Producto.query.get(id); carrito=session.get('carrito',[])
    for it in carrito:
        if it['id']==prod.id: it['cant']+=1; session['carrito']=carrito; session.modified=True; return redirect('/dashboard')
    carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':prod.precio,'cant':1}); session['carrito']=carrito; session.modified=True; return redirect('/dashboard')
@app.route('/pos/clear', methods=['POST'])
def pos_clear():
    session['carrito']=[]; session.modified=True; return redirect('/dashboard')
@app.route('/pos/pagar', methods=['POST'])
def pos_pagar():
    data=request.get_json(); metodo=data.get('tipo','efectivo'); carrito=session.get('carrito',[]); last=None
    vendedor=session.get('user'); vendedor_nombre=session.get('nombre_completo','')
    for it in carrito:
        prod=Producto.query.get(it['id'])
        if prod: prod.stock-=it['cant']
        v=Venta(cliente='Mostrador',producto_nombre=it['nombre'],cantidad=it['cant'],total=it['precio']*it['cant'],vendedor=vendedor,vendedor_nombre=vendedor_nombre,metodo_pago=metodo); db.session.add(v); db.session.flush(); last=v.id
    db.session.commit(); session['carrito']=[]; session.modified=True; return jsonify({'ok':True,'ticket_id':last})

@app.route('/admin/mesas', methods=['GET','POST'])
def admin_mesas():
    if not session.get('is_admin'): return redirect('/dashboard')
    if request.method=='POST':
        nombre=request.form.get('nombre','').strip()
        if nombre and not Mesa.query.filter_by(nombre=nombre).first():
            db.session.add(Mesa(nombre=nombre,estado='libre',total=0)); db.session.commit()
        return redirect('/admin/mesas')
    mesas=Mesa.query.all()
    return render_template_string(STYLE_BASE+nav()+"""
<div class="container mt-3"><div class="card"><h5 style="color:#ff4d8a">🪑 Administrar Mesas</h5>
<form method="POST" class="d-flex gap-2 mt-3"><input name="nombre" class="form-control" placeholder="Ej: Mesa 13" required><button class="btn-rosa">Agregar Mesa</button></form>
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px;margin-top:15px">
{% for m in mesas %}<div style="background:#111;border:2px solid {% if m.estado=='ocupada' %}#ff4d8a{% else %}#333{% endif %};border-radius:10px;padding:12px;text-align:center"><b>{{m.nombre}}</b><br><small>{{m.estado}} - {{m.total_mxn}}</small><br>{% if m.estado=='libre' %}<a href="/admin/mesas/eliminar/{{m.id}}" onclick="return confirm('¿Eliminar {{m.nombre}}?')" style="color:#ff4d8a;font-size:12px">Eliminar</a>{% else %}<small style="color:#888">Ocupada</small>{% endif %}</div>{% endfor %}
</div></div></div>
""", mesas=[{'id':m.id,'nombre':m.nombre,'estado':m.estado,'total_mxn':format_mxn(m.total or 0)} for m in mesas])

@app.route('/admin/mesas/eliminar/<int:id>')
def admin_mesas_eliminar(id):
    if not session.get('is_admin'): return redirect('/dashboard')
    m=Mesa.query.get(id)
    if m and m.estado=='libre': db.session.delete(m); db.session.commit()
    return redirect('/admin/mesas')

@app.route('/mesas')
def mesas_view():
    mesas=Mesa.query.all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px">{% for m in mesas %}<div style="background:{% if m.estado=='ocupada' %}#fde8e8{% else %}#e8f5e9{% endif %};color:black;padding:15px;border-radius:10px;text-align:center;cursor:pointer" onclick="location='/mesa/{{m.id}}'"><b>{{m.nombre}}</b><br>{{m.estado}}<br>{{m.total_mxn}}</div>{% endfor %}</div></div>""", mesas=[{'id':m.id,'nombre':m.nombre,'estado':m.estado,'total_mxn':format_mxn(m.total or 0)} for m in mesas])

@app.route('/mesa/<int:id>')
def mesa_detalle(id):
    mesa=Mesa.query.get(id)
    productos=Producto.query.filter_by(disponible=True).all()
    for p in productos: p.img_url=get_producto_imagen(p)
    carrito=session.get(f'mesa_carrito_{id}',[]); total_nuevo=sum([x['precio']*x['cant'] for x in carrito]); comandas=[c for c in mesa.comandas if c.estado!='entregado']
    return render_template_string(STYLE_BASE+nav()+"""
<div style="display:flex;height:calc(100vh - 60px);gap:10px;padding:10px">
<div style="width:45%;background:#111;border:2px solid #00e5ff;border-radius:12px;padding:10px;overflow:auto;display:flex;flex-direction:column">
<h6 style="color:#00e5ff">{{mesa.nombre}} - {{mesa.total_mxn}}</h6>
<div style="flex:1;overflow:auto">
{% for c in comandas %}<div style="background:white;color:black;padding:6px;border-radius:6px;margin-bottom:5px;font-size:12px"><b>{{c.cantidad}}x {{c.producto_nombre}}</b> {% if c.comentario %}<span style="background:#c62828;color:white;padding:2px 4px;border-radius:4px">💬 {{c.comentario}}</span>{% endif %}</div>{% endfor %}
<hr><b style="color:#ffcc00;font-size:12px">Nuevo - Comentario ANTES</b>
{% for it in carrito %}<div style="background:#fffde7;color:black;padding:5px;border-radius:4px;margin-top:5px;font-size:12px">{{it.nombre}} x{{it.cant}} - {{it.total_mxn}}<form action="/mesa/{{mesa.id}}/carrito/coment/{{loop.index0}}" method="POST" style="display:flex;gap:3px"><input name="comentario" value="{{it.comentario}}" class="form-control" style="font-size:11px" placeholder="💬 Comentario"><button>💾</button></form></div>{% endfor %}
</div>
<div style="border-top:2px solid #ff4d8a;padding-top:10px"><b>Total Final {{total_final_mxn}}</b><br><a href="/mesa/{{mesa.id}}/enviar" style="background:#00e5ff;color:black;padding:8px;display:block;text-align:center;border-radius:6px;margin-top:5px">MANDAR A COCINA</a><a href="/mesa/{{mesa.id}}/cobrar" style="background:#25D366;color:white;padding:8px;display:block;text-align:center;border-radius:6px;margin-top:5px">💰 COBRAR MESA</a></div>
</div>
<div style="width:55%;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;overflow:auto">
{% for p in productos %}<div style="background:white;color:#333;border-radius:8px;padding:6px;text-align:center;cursor:pointer" onclick="location='/mesa/{{mesa.id}}/add/{{p.id}}'"><img src="{{p.img_url}}" style="width:60px;height:60px;object-fit:cover;border-radius:6px"><br><small>{{p.nombre}}</small><br><small style="color:#ff4d8a;font-weight:bold">{{p.precio_mxn}}</small></div>{% endfor %}
</div>
</div>
""", mesa={'id':mesa.id,'nombre':mesa.nombre,'total_mxn':format_mxn(mesa.total or 0)}, productos=[{'id':p.id,'nombre':p.nombre,'precio_mxn':format_mxn(p.precio),'img_url':p.img_url} for p in productos], carrito=[{'nombre':x['nombre'],'cant':x['cant'],'comentario':x.get('comentario',''),'total_mxn':format_mxn(x['precio']*x['cant'])} for x in carrito], comandas=comandas, total_final_mxn=format_mxn((mesa.total or 0)+total_nuevo))

@app.route('/mesa/<int:mesa_id>/add/<int:prod_id>')
def mesa_add(mesa_id, prod_id):
    prod=Producto.query.get(prod_id); carrito=session.get(f'mesa_carrito_{mesa_id}',[])
    carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':prod.precio,'cant':1,'comentario':''}); session[f'mesa_carrito_{mesa_id}']=carrito; session.modified=True; return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:mesa_id>/carrito/coment/<int:index>', methods=['POST'])
def mesa_carrito_coment(mesa_id,index):
    carrito=session.get(f'mesa_carrito_{mesa_id}',[]);
    if 0 <= index < len(carrito): carrito[index]['comentario']=request.form.get('comentario','')[:200]; session[f'mesa_carrito_{mesa_id}']=carrito; session.modified=True
    return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:mesa_id>/enviar')
def mesa_enviar(mesa_id):
    mesa=Mesa.query.get(mesa_id); carrito=session.get(f'mesa_carrito_{mesa_id}',[])
    mesero=session.get('user'); mesero_nombre=session.get('nombre_completo','')
    for it in carrito:
        com=Comanda(mesa_id=mesa.id,producto_nombre=it['nombre'],cantidad=it['cant'],mesero=mesero,mesero_nombre=mesero_nombre,estado='cocina',comentario=it.get('comentario','')); mesa.total=(mesa.total or 0)+it['precio']*it['cant']; mesa.estado='ocupada'; db.session.add(com)
    db.session.commit(); session[f'mesa_carrito_{mesa_id}']=[]; session.modified=True; return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:id>/cobrar')
def mesa_cobrar_view(id):
    mesa=Mesa.query.get(id); total=mesa.total or 0
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4" style="max-width:500px"><div class="card" style="border-color:#25D366"><h4>💰 Cobrar {{mesa.nombre}} - {{total_mxn}}</h4><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:15px"><a href="/mesa/{{mesa.id}}/cobrar_final/efectivo" style="background:#25D366;color:white;padding:20px;text-align:center;border-radius:8px">💵<br>Efectivo</a><a href="/mesa/{{mesa.id}}/cobrar_final/tarjeta" style="background:#3f51b5;color:white;padding:20px;text-align:center;border-radius:8px">💳<br>Tarjeta</a><a href="/mesa/{{mesa.id}}/cobrar_final/transferencia" style="background:#0097a7;color:white;padding:20px;text-align:center;border-radius:8px">🏦<br>Transfer</a></div></div></div>""", mesa=mesa, total_mxn=format_mxn(total))
@app.route('/mesa/<int:id>/cobrar_final/<metodo>')
def mesa_cobrar_final(id,metodo):
    mesa=Mesa.query.get(id); vendedor=session.get('user'); vendedor_nombre=session.get('nombre_completo','')
    for c in list(mesa.comandas):
        if c.estado!='entregado':
            prod=Producto.query.filter_by(nombre=c.producto_nombre).first()
            precio=prod.precio if prod else 0
            v=Venta(cliente=mesa.nombre,producto_nombre=c.producto_nombre+(f" ({c.comentario})" if c.comentario else ""),cantidad=c.cantidad,total=precio*c.cantidad,vendedor=vendedor,vendedor_nombre=vendedor_nombre,metodo_pago=metodo); db.session.add(v); c.estado='entregado'
    mesa.estado='libre'; mesa.total=0; db.session.commit()
    v=Venta.query.filter_by(vendedor=vendedor).order_by(Venta.id.desc()).first()
    if v: return redirect(f'/ticket/{v.id}')
    return redirect('/mesas')

@app.route('/cocina')
def cocina_view():
    if 'user' not in session: return redirect('/')
    comandas=Comanda.query.filter_by(estado='cocina').all()
    from collections import defaultdict
    grupos=defaultdict(list)
    for c in comandas: grupos[c.mesa_id].append(c)
    grupos_list=[{'mesa':Mesa.query.get(mid),'comandas':lista} for mid,lista in grupos.items() if Mesa.query.get(mid)]
    return render_template_string(STYLE_BASE+nav()+"""<div class="container-fluid mt-3"><h3 style="color:#ffcc00">🔥 Cocina - {{grupos_list|length}} mesas</h3><div class="row g-3 mt-2">{% for g in grupos_list %}<div class="col-md-4"><div class="card" style="border-color:#ff4d3a;background:#1a1a0a"><h5 style="color:#00e5ff">🪑 {{g.mesa.nombre}}</h5>{% for c in g.comandas %}<div style="background:white;color:black;padding:6px;border-radius:6px;margin-bottom:5px"><b>{{c.cantidad}}x {{c.producto_nombre}}</b><br>{% if c.comentario %}<span style="background:#c62828;color:white;padding:2px 6px;border-radius:4px;font-size:11px">💬 {{c.comentario}}</span>{% endif %}</div>{% endfor %}<a href="/cocina/mesa_listo/{{g.mesa.id}}" class="btn-rosa w-100 mt-2" style="background:#25D366">✅ MESA LISTA</a></div></div>{% endfor %}{% if not grupos_list %}<div class="col-12 text-center p-4"><h4 style="color:#25D366">Sin pedidos 🟢</h4></div>{% endif %}</div></div><script>setTimeout(()=>location.reload(),15000)</script>""", grupos_list=[{'mesa':{'id':g['mesa'].id,'nombre':g['mesa'].nombre},'comandas':g['comandas']} for g in grupos_list])

@app.route('/cocina/mesa_listo/<int:mesa_id>')
def cocina_mesa_listo(mesa_id):
    mesa=Mesa.query.get(mesa_id)
    for c in mesa.comandas:
        if c.estado=='cocina': c.estado='listo'
    db.session.commit(); return redirect('/cocina')

@app.route('/productos')
def productos_list():
    if not session.get('is_admin'): return redirect('/dashboard')
    productos=Producto.query.all()
    for p in productos: p.img_url=get_producto_imagen(p)
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div style="background:white;color:#333;border-radius:4px;padding:15px"><div style="display:flex;justify-content:space-between"><h4>📦 Productos ({{productos|length}})</h4><a href="/productos/nuevo" style="background:#4caf50;color:white;padding:8px 16px;border-radius:4px;text-decoration:none">+ Crear artículo</a></div><table class="table mt-3"><tr><th>Foto</th><th>Nombre</th><th>Categoría</th><th>Precio</th><th>Stock</th><th></th></tr>{% for p in productos %}<tr><td><img src="{{p.img_url}}" style="width:45px;height:45px;object-fit:cover;border-radius:6px"></td><td>{{p.nombre}}</td><td>{{p.categoria}}</td><td>{{p.precio_mxn}}</td><td>{{p.stock}}</td><td><a href="/productos/eliminar/{{p.id}}" style="color:red">Borrar</a></td></tr>{% endfor %}</table></div></div>""", productos=[{'id':p.id,'nombre':p.nombre,'categoria':p.categoria,'stock':p.stock,'img_url':p.img_url,'precio_mxn':format_mxn(p.precio)} for p in productos])

@app.route('/productos/nuevo', methods=['GET','POST'])
def productos_nuevo():
    if not session.get('is_admin'): return redirect('/dashboard')
    categorias=Categoria.query.all()
    if request.method=='POST':
        imagen_path=save_upload(request.files['imagen']) if 'imagen' in request.files else ""
        p=Producto(nombre=request.form.get('nombre','').strip() or 'Sin nombre',descripcion=request.form.get('descripcion',''),categoria=request.form.get('categoria','Sin categoria'),disponible='disponible' in request.form,precio=float(request.form.get('precio') or 0),stock=int(request.form.get('en_stock') or 0),imagen=imagen_path)
        db.session.add(p); db.session.commit(); return redirect('/productos')
    return render_template_string(STYLE_BASE+nav()+"""
<div style="background:#000;min-height:100vh">
<div class="header-rosa-negro">☰ Crear artículo <a href="/productos" style="margin-left:auto;background:#111;color:#ff4d8a;border:2px solid #ff4d8a;padding:6px 12px;border-radius:8px;text-decoration:none;font-size:13px">← Volver</a></div>
<form method="POST" enctype="multipart/form-data">
<div class="card-negra">
<div class="row"><div class="col-md-6"><label class="label-rosa">NOMBRE *</label><input name="nombre" class="input-rosa" placeholder="Ej: Agua, botella 0.5L" style="font-size:20px;font-weight:bold" required></div>
<div class="col-md-6"><label class="label-rosa">CATEGORÍA</label><div style="display:flex;gap:6px"><select name="categoria" id="catSelect" class="select-rosa" style="flex:1">{% for cat in categorias %}<option value="{{cat.nombre}}">{{cat.nombre}}</option>{% endfor %}</select><button type="button" onclick="nuevaCategoria()" style="background:#ff4d8a;color:white;border:none;padding:6px 10px;border-radius:8px;font-size:11px;font-weight:bold">+ NUEVA</button></div></div></div>
<label class="label-rosa">DESCRIPCIÓN</label><textarea name="descripcion" class="input-rosa" rows="2" placeholder="Descripción opcional"></textarea>
<div style="margin-top:15px"><input type="checkbox" name="disponible" checked style="accent-color:#ff4d8a"> El artículo está disponible para la venta</div>
<div class="row" style="margin-top:15px"><div class="col-md-4"><label class="label-rosa">PRECIO MXN *</label><input name="precio" type="number" step="0.01" class="input-rosa" placeholder="0.00" required></div><div class="col-md-4"><label class="label-rosa">EN STOCK</label><input name="en_stock" type="number" class="input-rosa" placeholder="0"></div><div class="col-md-4"><label class="label-rosa">FOTO</label><input name="imagen" type="file" class="form-control" accept="image/*" style="background:#111!important;color:white!important;border:2px solid #ff4d8a!important"></div></div>
<button style="background:#ff4d8a;color:white;border:none;padding:12px 30px;border-radius:10px;font-weight:bold;margin-top:20px">💾 GUARDAR ARTÍCULO</button>
</div>
</form>
</div>
<script>
function nuevaCategoria(){
  let nombre=prompt("Nombre nueva categoría:");
  if(!nombre) return;
  fetch('/api/categorias/crear',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nombre:nombre})}).then(r=>r.json()).then(d=>{
    if(d.ok){ let sel=document.getElementById('catSelect'); let opt=document.createElement('option'); opt.value=d.nombre; opt.text=d.nombre; opt.selected=true; sel.add(opt); }
    else alert("Ya existe");
  })
}
</script>
""", categorias=categorias)

@app.route('/api/categorias/crear', methods=['POST'])
def api_categorias_crear():
    if not session.get('is_admin'): return jsonify({'ok':False})
    nombre=request.get_json().get('nombre','').strip()
    if nombre and not Categoria.query.filter_by(nombre=nombre).first():
        db.session.add(Categoria(nombre=nombre)); db.session.commit(); return jsonify({'ok':True,'nombre':nombre})
    return jsonify({'ok':False})

@app.route('/productos/eliminar/<int:id>')
def eliminar_producto(id):
    p=Producto.query.get(id)
    if p: db.session.delete(p); db.session.commit()
    return redirect('/productos')

@app.route('/dueno')
def dueno_view():
    if not session.get('is_admin'): return redirect('/dashboard')
    return render_template_string(STYLE_BASE+nav()+"""
<div class="container mt-3"><div class="card" style="border-color:#ff4d8a"><h4 style="color:#ff4d8a">💰 Dueño - Ventas vs Gastos</h4>
<div style="display:flex;gap:10px;margin-top:15px"><select id="periodo" class="form-control" style="width:150px;background:#111!important;color:white!important;border:2px solid #ff4d8a!important" onchange="cargarGrafica()"><option value="dia">Día</option><option value="mes" selected>Mes</option><option value="ano">Año</option></select><button onclick="cargarGrafica()" style="background:#ff4d8a;color:white;border:none;padding:6px 12px;border-radius:6px">Actualizar</button></div>
<div style="background:#111;border:2px solid #ff4d8a;border-radius:12px;padding:15px;margin-top:15px"><canvas id="graficaVentasGastos" height="100"></canvas></div>
<div class="row mt-3"><div class="col-md-4"><div class="card"><h6>Ventas</h6><h3 id="totalVentas" style="color:#25D366">$0 MXN</h3></div></div><div class="col-md-4"><div class="card"><h6>Gastos</h6><h3 id="totalGastos" style="color:#ff4d8a">$0 MXN</h3></div></div><div class="col-md-4"><div class="card"><h6>Ganancia</h6><h3 id="totalGanancia" style="color:#ff4d8a">$0 MXN</h3></div></div></div>
<div class="card mt-3"><h6>Agregar gasto</h6><form id="formGasto" class="d-flex gap-2 mt-2"><input id="concepto" class="form-control" placeholder="Concepto" required><input id="monto" type="number" step="0.01" class="form-control" placeholder="Monto MXN" required><button style="background:#ff4d8a;color:white;border:none;padding:6px 12px;border-radius:6px">Agregar</button></form></div>
</div></div>
<script>
let chart;
function cargarGrafica(){
  let periodo=document.getElementById('periodo').value;
  fetch('/api/ventas_gastos?periodo='+periodo).then(r=>r.json()).then(data=>{
    document.getElementById('totalVentas').innerText='$'+data.total_ventas.toFixed(2)+' MXN';
    document.getElementById('totalGastos').innerText='$'+data.total_gastos.toFixed(2)+' MXN';
    document.getElementById('totalGanancia').innerText='$'+(data.total_ventas-data.total_gastos).toFixed(2)+' MXN';
    let ctx=document.getElementById('graficaVentasGastos').getContext('2d');
    if(chart) chart.destroy();
    chart=new Chart(ctx,{type:'line',data:{labels:data.labels,[STRIPPED]
  });
}
document.getElementById('formGasto').addEventListener('submit',function(e){e.preventDefault();fetch('/api/gasto',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({concepto:document.getElementById('concepto').value,monto:document.getElementById('monto').value})}).then(()=>{document.getElementById('concepto').value='';document.getElementById('monto').value='';cargarGrafica();});});
cargarGrafica();
</script>
""")

@app.route('/api/ventas_gastos')
def api_ventas_gastos():
    periodo=request.args.get('periodo','mes'); labels=[]; ventas_data=[]; gastos_data=[]; now=datetime.now()
    if periodo=='dia':
        for i in range(6,-1,-1):
            day=now - timedelta(days=i); start=day.replace(hour=0,minute=0,second=0,microsecond=0); end=start+timedelta(days=1)
            v=sum([x.total or 0 for x in Venta.query.filter(Venta.fecha>=start,Venta.fecha<end).all()])
            g=sum([x.monto or 0 for x in Gasto.query.filter(Gasto.fecha>=start,Gasto.fecha<end).all()])
            labels.append(start.strftime("%d/%m")); ventas_data.append(v); gastos_data.append(g)
    elif periodo=='ano':
        for y in range(now.year-4, now.year+1):
            start=datetime(y,1,1); end=datetime(y+1,1,1)
            v=sum([x.total or 0 for x in Venta.query.filter(Venta.fecha>=start,Venta.fecha<end).all()])
            g=sum([x.monto or 0 for x in Gasto.query.filter(Gasto.fecha>=start,Gasto.fecha<end).all()])
            labels.append(str(y)); ventas_data.append(v); gastos_data.append(g)
    else:
        for i in range(11,-1,-1):
            m=now.month - i; y=now.year
            while m<=0: m+=12; y-=1
            start=datetime(y,m,1); end=datetime(y+1,1,1) if m==12 else datetime(y,m+1,1)
            v=sum([x.total or 0 for x in Venta.query.filter(Venta.fecha>=start,Venta.fecha<end).all()])
            g=sum([x.monto or 0 for x in Gasto.query.filter(Gasto.fecha>=start,Gasto.fecha<end).all()])
            labels.append(start.strftime("%b %Y")); ventas_data.append(v); gastos_data.append(g)
    return jsonify({'labels':labels,'ventas':ventas_data,'gastos':gastos_data,'total_ventas':sum(ventas_data),'total_gastos':sum(gastos_data)})

@app.route('/api/gasto', methods=['POST'])
def api_gasto():
    data=request.get_json()
    g=Gasto(concepto=data.get('concepto','Gasto'),monto=float(data.get('monto',0))); db.session.add(g); db.session.commit()
    return jsonify({'ok':True})

@app.route('/admin/config', methods=['GET','POST'])
def admin_config():
    if not session.get('is_admin'): return redirect('/dashboard')
    cfg=get_config()
    if request.method=='POST':
        if 'logo' in request.files:
            nl=save_upload(request.files['logo'])
            if nl: cfg.logo_path=nl
        cfg.mod_pos_mesero='mod_pos_mesero' in request.form
        db.session.commit(); return redirect('/admin/config')
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4" style="max-width:600px"><div class="card"><h4>⚙️ Config + Logo</h4><div class="text-center" style="display:flex;justify-content:center"><img src="/static/{{cfg.logo_path}}" style="width:100px;height:100px;border-radius:50%;background:white;padding:5px;object-fit:cover;border:2px solid #ff4d8a;display:block;margin:0 auto"></div><form method="POST" enctype="multipart/form-data" class="mt-3"><label>Cambiar logo</label><input name="logo" type="file" class="form-control mb-2" accept="image/*"><label><input type="checkbox" name="mod_pos_mesero" {{'checked' if cfg.mod_pos_mesero}}> POS para mesero habilitado</label><br><button class="btn-rosa w-100 mt-2">Guardar</button></form></div></div>""", cfg=cfg)

@app.route('/ticket/<int:id>')
def ticket(id):
    v=Venta.query.get(id)
    if not v: return redirect('/dashboard')
    cfg=get_config()
    return render_template_string(STYLE_BASE+f'<div class="container mt-5" style="max-width:350px"><div class="card" style="background:white;color:black"><h5>Ticket #{v.id}</h5><p><b>{v.producto_nombre}</b><br>Total: {format_mxn(v.total)}<br>Pago: {v.metodo_pago}<br>Atendió: {v.vendedor_nombre}<br><small style="color:#888">Usuario: {v.vendedor}</small><br><small id="fechaPC" style="color:#888"></small></p><button onclick="window.print()" class="btn-rosa w-100">Imprimir</button><a href="/dashboard" class="btn btn-dark w-100 mt-2">Volver</a></div></div><script>document.getElementById("fechaPC").textContent=new Date().toLocaleString("es-MX",{{timeZone:"America/Cancun"}})</script>')

@app.route('/ventas')
def ventas():
    vs=Venta.query.order_by(Venta.id.desc()).limit(100).all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card"><h5>Ventas MXN</h5><table class="table table-dark table-sm"><tr><th>Fecha</th><th>Producto</th><th>Total MXN</th><th>Pago</th><th>Vendedor</th></tr>{% for v in vs %}<tr><td>{{v.fecha.strftime('%d/%m %H:%M')}}</td><td>{{v.producto_nombre}} x{{v.cantidad}}</td><td>{{v.total_mxn}}</td><td>{{v.metodo_pago}}</td><td>{{v.vendedor_nombre}}</td></tr>{% endfor %}</table></div></div>""", vs=[{'fecha':v.fecha,'producto_nombre':v.producto_nombre,'cantidad':v.cantidad,'total_mxn':format_mxn(v.total),'metodo_pago':v.metodo_pago,'vendedor_nombre':v.vendedor_nombre} for v in vs])

# --- USUARIOS CON EDITAR + RESETEAR ---
@app.route('/admin/usuarios', methods=['GET','POST'])
def admin_usuarios():
    if not session.get('is_admin'): return redirect('/dashboard')
    if request.method=='POST':
        username=request.form.get('username','').strip()
        nombre_completo=request.form.get('nombre_completo','').strip()
        password=request.form.get('password','').strip()
        rol=request.form.get('rol','cajero')
        is_admin='is_admin' in request.form
        if username and nombre_completo and password and not User.query.filter_by(username=username).first():
            if is_admin: rol='admin'
            db.session.add(User(username=username,nombre_completo=nombre_completo,password=generate_password_hash(password),is_admin=is_admin,rol=rol)); db.session.commit()
        return redirect('/admin/usuarios')
    usuarios=User.query.all()
    return render_template_string(STYLE_BASE+nav()+"""
<div class="container mt-3"><div class="card"><h5>👥 Usuarios - Editar y Restablecer</h5><p style="font-size:11px;color:#888">El nombre completo solo aparece en ticket. El admin puede editar todo.</p>
<form method="POST" class="row g-2">
<div class="col-md-3"><input name="nombre_completo" class="form-control" placeholder="Nombre completo *" required></div>
<div class="col-md-2"><input name="username" class="form-control" placeholder="Usuario *" required></div>
<div class="col-md-2"><input name="password" type="password" class="form-control" placeholder="Contraseña *" required></div>
<div class="col-md-2"><select name="rol" class="form-control"><option value="cajero">Cajero</option><option value="mesero">Mesero</option><option value="cocina">Cocina</option></select></div>
<div class="col-md-1"><label><input type="checkbox" name="is_admin"> Admin</label></div>
<div class="col-md-2"><button class="btn-rosa w-100">Crear</button></div>
</form>
<table class="table table-dark mt-3"><tr><th>Nombre Completo</th><th>Usuario</th><th>Rol</th><th>Acciones</th></tr>
{% for u in usuarios %}<tr><td>{{u.nombre_completo}}</td><td>{{u.username}}</td><td>{% if u.is_admin %}ADMIN{% else %}{{u.rol}}{% endif %}</td><td><a href="/admin/usuarios/editar/{{u.id}}" style="color:#00e5ff;font-size:12px;margin-right:8px">Editar</a><a href="/admin/usuarios/reset/{{u.id}}" style="color:#ffcc00;font-size:12px;margin-right:8px">Reset Pass</a><a href="/admin/usuarios/eliminar/{{u.id}}" onclick="return confirm('Eliminar {{u.username}}?')" style="color:#ff4d8a;font-size:12px">Eliminar</a></td></tr>{% endfor %}
</table>
</div></div>
""", usuarios=usuarios)

@app.route('/admin/usuarios/editar/<int:id>', methods=['GET','POST'])
def admin_usuarios_editar(id):
    if not session.get('is_admin'): return redirect('/dashboard')
    u=User.query.get(id)
    if not u: return redirect('/admin/usuarios')
    if request.method=='POST':
        u.nombre_completo=request.form.get('nombre_completo','').strip() or u.nombre_completo
        u.username=request.form.get('username','').strip() or u.username
        u.rol=request.form.get('rol',u.rol)
        u.is_admin='is_admin' in request.form
        nueva_pass=request.form.get('password','').strip()
        if nueva_pass:
            u.password=generate_password_hash(nueva_pass)
        db.session.commit()
        return redirect('/admin/usuarios')
    return render_template_string(STYLE_BASE+nav()+f"""
<div class="container mt-3"><div class="card" style="max-width:500px;margin:0 auto"><h5 style="color:#ff4d8a">Editar Usuario - {u.username}</h5>
<form method="POST" class="mt-3">
<label class="label-rosa">Nombre completo</label><input name="nombre_completo" class="form-control mb-2" value="{u.nombre_completo}" required>
<label class="label-rosa">Usuario</label><input name="username" class="form-control mb-2" value="{u.username}" required>
<label class="label-rosa">Rol</label><select name="rol" class="form-control mb-2"><option value="cajero" {"selected" if u.rol=="cajero" else ""}>Cajero</option><option value="mesero" {"selected" if u.rol=="mesero" else ""}>Mesero</option><option value="cocina" {"selected" if u.rol=="cocina" else ""}>Cocina</option><option value="admin" {"selected" if u.is_admin else ""}>Admin</option></select>
<label><input type="checkbox" name="is_admin" {"checked" if u.is_admin else ""}> Es Administrador</label>
<label class="label-rosa">Nueva Contraseña (dejar en blanco para no cambiar)</label><input name="password" type="password" class="form-control mb-3" placeholder="Nueva contraseña">
<button class="btn-rosa w-100">Guardar Cambios</button>
</form>
<a href="/admin/usuarios" style="display:block;text-align:center;margin-top:10px;color:#888">← Volver</a>
</div></div>
""")

@app.route('/admin/usuarios/reset/<int:id>', methods=['GET','POST'])
def admin_usuarios_reset(id):
    if not session.get('is_admin'): return redirect('/dashboard')
    u=User.query.get(id)
    if request.method=='POST':
        nueva=request.form.get('nueva','').strip()
        confirmar=request.form.get('confirmar','').strip()
        if nueva==confirmar and len(nueva)>=4:
            u.password=generate_password_hash(nueva)
            db.session.commit()
            return redirect('/admin/usuarios')
    return render_template_string(STYLE_BASE+nav()+f"""
<div class="container mt-3"><div class="card" style="max-width:400px;margin:0 auto"><h5 style="color:#ffcc00">Restablecer Contraseña - {u.nombre_completo}</h5><p style="font-size:12px;color:#888">Usuario: {u.username}</p>
<form method="POST">
<label class="label-rosa">Nueva Contraseña</label><input name="nueva" type="password" class="form-control mb-2" required>
<label class="label-rosa">Confirmar</label><input name="confirmar" type="password" class="form-control mb-3" required>
<button class="btn-rosa w-100" style="background:#ffcc00;color:black">Restablecer</button>
</form>
<a href="/admin/usuarios" style="display:block;text-align:center;margin-top:10px;color:#888">← Volver</a>
</div></div>
""")

@app.route('/admin/usuarios/eliminar/<int:id>')
def admin_usuarios_eliminar(id):
    if not session.get('is_admin'): return redirect('/dashboard')
    u=User.query.get(id)
    if u and u.username!='admin': db.session.delete(u); db.session.commit()
    return redirect('/admin/usuarios')

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))