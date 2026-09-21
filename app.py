from flask import Flask, request, redirect, session, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'ruve-pos-anterior-dropdown-click-fix'

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
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True)
    password=db.Column(db.String(200))
    is_admin=db.Column(db.Boolean, default=False)
    rol=db.Column(db.String(20), default="cajero")
class Producto(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(100))
    precio=db.Column(db.Float, default=0)
    stock=db.Column(db.Integer, default=0)
    costo=db.Column(db.Float, default=0)
    imagen=db.Column(db.String(200), default="")
    descripcion=db.Column(db.Text, default="")
    categoria=db.Column(db.String(50), default="Sin categoria")
    disponible=db.Column(db.Boolean, default=True)
    vendido_por=db.Column(db.String(20), default="Unidad")
    ref=db.Column(db.String(50), default="")
    codigo_barras=db.Column(db.String(100), default="")
class Venta(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    cliente=db.Column(db.String(100))
    producto_nombre=db.Column(db.String(100))
    cantidad=db.Column(db.Integer)
    total=db.Column(db.Float)
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    vendedor=db.Column(db.String(80), default="admin")
    metodo_pago=db.Column(db.String(20), default="efectivo")
class Config(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    logo_path=db.Column(db.String(200), default="logo.png")
    mod_mesas=db.Column(db.Boolean, default=True)
    mod_cocina=db.Column(db.Boolean, default=True)
    mod_pos_mesero=db.Column(db.Boolean, default=False)
class Mesa(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(50))
    estado=db.Column(db.String(20), default="libre")
    total=db.Column(db.Float, default=0)
    unida_a_id=db.Column(db.Integer, db.ForeignKey('mesa.id'), nullable=True)
    unida_a = db.relationship('Mesa', remote_side=[id], backref='mesas_unidas')
class Comanda(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    mesa_id=db.Column(db.Integer, db.ForeignKey('mesa.id'))
    producto_nombre=db.Column(db.String(100))
    cantidad=db.Column(db.Integer)
    estado=db.Column(db.String(20), default="cocina")
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    mesero=db.Column(db.String(80))
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
def get_mesa_principal(mesa):
    if mesa and mesa.unida_a_id:
        principal = Mesa.query.get(mesa.unida_a_id)
        while principal and principal.unida_a_id:
            principal = Mesa.query.get(principal.unida_a_id)
        return principal or mesa
    return mesa
def get_categoria(nombre):
    n=nombre.lower()
    if 'lech' in n: return 'lechon'
    if 'torta' in n: return 'tortas'
    if 'orden' in n: return 'ordenes'
    if 'refresco' in n or 'bebida' in n or 'agua' in n: return 'bebidas'
    return 'extras'

with app.app_context():
    from sqlalchemy import text
    db.create_all()
    for q in [
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS imagen VARCHAR(200) DEFAULT \'\'',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS descripcion TEXT DEFAULT \'\'',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS categoria VARCHAR(50) DEFAULT \'Sin categoria\'',
        'ALTER TABLE config ADD COLUMN IF NOT EXISTS logo_path VARCHAR(200) DEFAULT \'logo.png\'',
        'ALTER TABLE config ADD COLUMN IF NOT EXISTS mod_pos_mesero BOOLEAN DEFAULT FALSE',
    ]:
        try: db.session.execute(text(q)); db.session.commit()
        except: db.session.rollback()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin',password=generate_password_hash('admin123'),is_admin=True,rol='admin')); db.session.commit()
    if Producto.query.count()==0:
        db.session.add_all([Producto(nombre='Lechón por Kilo',precio=350,stock=50),Producto(nombre='Torta de Lechón',precio=70,stock=30),Producto(nombre='Refresco',precio=25,stock=100)]); db.session.commit()
    if Mesa.query.count()==0:
        for i in range(1,13): db.session.add(Mesa(nombre=f"Mesa {i}"))
        db.session.commit()

STYLE_BASE = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#000;color:white;font-family:Arial;margin:0}
.card{background:#111;border:2px solid #ff4d8a;border-radius:15px;padding:20px}
.btn-rosa{background:#ff4d8a;color:white;border:none;padding:10px 18px;border-radius:10px;font-weight:bold}
.navbar{background:#000!important;border-bottom:2px solid #ff4d8a;display:flex;justify-content:space-between;align-items:center;padding:10px 15px}
.pos-container{display:flex;height:calc(100vh - 60px);gap:10px;padding:10px}
.pos-left{width:38%;background:#0f0f0f;border:2px solid #ff4d8a;border-radius:15px;display:flex;flex-direction:column}
.pos-center{width:12%;display:flex;flex-direction:column;gap:8px}
.pos-right{width:50%;background:#0f0f0f;border:2px solid #333;border-radius:15px;padding:10px;overflow-y:auto}
.cat-btn{background:#222;color:white;font-weight:bold;padding:14px;border:2px solid #333;border-radius:8px;cursor:pointer;text-align:center}
.cat-btn.active{background:#ff4d8a;border-color:#ff4d8a}
.prod-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.prod-card{background:#1a1a1a;border:2px solid #333;border-radius:12px;padding:10px;text-align:center;cursor:pointer}
.prod-card:hover{border-color:#ff4d8a}
.prod-card img{width:70px;height:70px;object-fit:cover;border-radius:10px;background:white;padding:5px}
.prod-card h6{color:#ff4d8a;margin:8px 0 2px 0;font-size:13px}
.ticket-header{background:#111;padding:12px;border-bottom:2px solid #ff4d8a}
.ticket-body{flex:1;overflow-y:auto;padding:10px;background:white;color:black}
.ticket-footer{background:#111;padding:12px;border-top:2px solid #ff4d8a}
.ticket-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed #ccc;font-size:13px}
.btn-cash{background:#25D366;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:32%}
.btn-pay{background:#3f51b5;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:32%}
.btn-trans{background:#0097a7;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:32%}
.qty-btn{border:none;background:#ff4d8a;color:white;border-radius:5px;padding:2px 8px;font-weight:bold}
.qty-btn.minus{background:#555}
/* DROPDOWN CORREGIDO - CLICK */
.dropdown{position:relative;display:inline-block}
.dropbtn{background:#111;color:#ff4d8a;border:2px solid #ff4d8a;padding:6px 14px;border-radius:8px;font-weight:bold;cursor:pointer}
.dropdown-content{display:none;position:absolute;right:0;background:#111;border:2px solid #ff4d8a;border-radius:10px;min-width:230px;z-index:9999;box-shadow:0 8px 16px rgba(0,0,0,0.8)}
.dropdown-content a{display:block;padding:12px 16px;color:white;text-decoration:none;font-size:13px;border-bottom:1px solid #222}
.dropdown-content a:hover{background:#222;color:#ff4d8a}
.dropdown-content.show{display:block}
.header-verde{background:#4caf50;color:white;padding:12px 20px;display:flex;align-items:center;font-weight:bold;font-size:18px}
.card-blanca{background:white;color:#333;border-radius:4px;padding:20px;margin:15px;box-shadow:0 1px 3px rgba(0,0,0,0.2)}
.input-line{border:none!important;border-bottom:1px solid #ccc!important;background:white!important;color:#333!important;border-radius:0!important;padding:8px 0!important;width:100%}
.label-small{font-size:11px;color:#888;margin-top:15px;display:block}
.switch{position:relative;display:inline-block;width:36px;height:20px}
.switch input{opacity:0;width:0;height:0}
.slider{position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background:#ccc;transition:.4s;border-radius:20px}
.slider:before{position:absolute;content:"";height:16px;width:16px;left:2px;bottom:2px;background:white;transition:.4s;border-radius:50%}
input:checked +.slider{background:#4caf50}
input:checked +.slider:before{transform:translateX(16px)}
</style>
"""

def nav():
    cfg=get_config(); rol=session.get('rol','cajero'); is_admin=session.get('is_admin', False); user=session.get('user','')
    logo_url=f"/static/{cfg.logo_path}"
    if not is_admin and rol=='cocina':
        return f'<nav class="navbar"><div class="d-flex align-items-center"><img src="{logo_url}" style="width:40px;height:40px;border-radius:50%;background:white;padding:3px;object-fit:cover"><h6 class="m-0 ms-2" style="color:#ffcc00">Cocina {user}</h6></div><div><a href="/cocina" class="me-3" style="color:#ffcc00">🔥 Cocina</a><a href="/logout">Salir</a></div></nav>'
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
            <a href="/productos/nuevo">➕ Crear artículo (con foto)</a>
            <a href="/ventas">🧾 Ventas</a>
            <a href="/reporte">📊 Reporte</a>
            <a href="/dueno" style="color:#ff4d8a">💰 Dueño</a>
            <a href="/admin/config">⚙️ Config + Logo</a>
            <a href="/admin/usuarios">👥 Usuarios</a>
          </div>
        </div>
        <script>
        function toggleDropdown(){{ document.getElementById("adminDropdown").classList.toggle("show"); }}
        window.onclick = function(e){{ if (!e.target.matches('.dropbtn')) {{ var d=document.getElementById("adminDropdown"); if(d && d.classList.contains('show')) d.classList.remove('show'); }} }}
        </script>
        '''
    else:
        if rol=='cajero': links+='<a href="/ventas" class="me-3">Ventas</a>'
    return f'<nav class="navbar"><div class="d-flex align-items-center"><img src="{logo_url}" style="width:40px;height:40px;border-radius:50%;background:white;padding:3px;object-fit:cover"><h6 class="m-0 ms-2" style="color:#ff4d8a">Ruve {user}</h6></div><div>{links}{admin_drop}<a href="/logout" class="ms-3">Salir</a></div></nav>'

@app.route('/', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user']=u.username; session['is_admin']=u.is_admin; session['rol']=u.rol; session['carrito']=[]
            if u.rol=='cocina' and not u.is_admin: return redirect('/cocina')
            if u.rol=='mesero' and not u.is_admin: return redirect('/mesas')
            return redirect('/dashboard')
    cfg=get_config()
    return render_template_string(STYLE_BASE+f'<div class="container" style="max-width:400px;margin-top:40px"><div class="card text-center"><img src="/static/{cfg.logo_path}" style="width:150px;height:150px;object-fit:cover;border-radius:50%;background:white;padding:5px"><h3 class="mt-3" style="color:#ff4d8a">Ruve</h3><form method="POST" class="mt-3"><input name="username" class="form-control mb-2" placeholder="Usuario" required><input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required><button class="btn-rosa w-100">Entrar</button></form></div></div>')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    productos=Producto.query.filter_by(disponible=True).all()
    for p in productos:
        p.img_url=get_producto_imagen(p)
        p.cat=get_categoria(p.nombre)
    carrito=session.get('carrito',[]); total=sum([x['precio']*x['cant'] for x in carrito])
    hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    ventas=Venta.query.filter(Venta.fecha>=hoy).order_by(Venta.id.desc()).limit(6).all()
    mesas_ocupadas=[m for m in Mesa.query.filter_by(estado='ocupada').all() if not m.unida_a_id]
    return render_template_string(STYLE_BASE+nav()+"""
<div class="pos-container">
    <div class="pos-left">
        <div class="ticket-header">
            <div style="display:flex;justify-content:space-between"><small style="color:#aaa">Mostrador</small><small style="color:#aaa">{{fecha}}</small></div>
        </div>
        <div class="ticket-body">
            <div style="display:flex;justify-content:space-between;font-weight:bold;border-bottom:2px solid black;padding-bottom:5px;font-size:11px"><span style="width:5%">#</span><span style="width:40%">Artículo</span><span style="width:15%">Precio</span><span style="width:20%">Cant</span><span style="width:20%">Total</span></div>
            {% for item in carrito %}
            <div class="ticket-row"><span style="width:5%;color:green">{{loop.index}}</span><span style="width:40%">{{item.nombre}}</span><span style="width:15%">${{item.precio}}</span><span style="width:20%"><a href="/pos/cant/{{loop.index0}}/-1" class="qty-btn minus">-</a> {{item.cant}} <a href="/pos/cant/{{loop.index0}}/1" class="qty-btn">+</a></span><span style="width:20%">${{item.precio*item.cant}}</span></div>
            {% endfor %}
            {% if mesas_ocupadas %}<hr><div style="background:#fff3cd;color:black;padding:6px;border-radius:6px;font-size:11px"><b>🪑 Mesas por cobrar:</b>{% for m in mesas_ocupadas %}<div style="display:flex;justify-content:space-between;padding:3px 0"><span>{{m.nombre}} ${{m.total}}</span><a href="/mesa/{{m.id}}/cobrar" style="background:#25D366;color:white;padding:2px 6px;border-radius:4px">Cobrar</a></div>{% endfor %}</div>{% endif %}
        </div>
        <div class="ticket-footer">
            <div style="display:flex;justify-content:space-between;color:white;font-weight:bold;font-size:18px"><span>Total</span><span>${{total}}</span></div>
            <div style="display:flex;gap:6px;margin-top:10px">
                <button onclick="pagar('efectivo')" class="btn-cash">💵 Efectivo</button>
                <button onclick="pagar('tarjeta')" class="btn-pay">💳 Tarjeta</button>
                <button onclick="pagar('transferencia')" class="btn-trans">🏦 Transfer</button>
            </div>
            <a href="/pos/clear" style="display:block;text-align:center;background:#555;color:white;padding:8px;border-radius:8px;margin-top:8px">🗑️ Limpiar</a>
            <div style="margin-top:8px;font-size:10px;color:#aaa">{% for v in ventas %}{{v.cliente}} ${{v.total}} ({{v.metodo_pago}})<br>{% endfor %}</div>
        </div>
    </div>
    <div class="pos-center">
        <button class="cat-btn active" onclick="filtrar('todos')" id="btn-todos">Todos</button>
        <button class="cat-btn" onclick="filtrar('lechon')" id="btn-lechon">Lechón</button>
        <button class="cat-btn" onclick="filtrar('tortas')" id="btn-tortas">Tortas</button>
        <button class="cat-btn" onclick="filtrar('ordenes')" id="btn-ordenes">Órdenes</button>
        <button class="cat-btn" onclick="filtrar('bebidas')" id="btn-bebidas">Bebidas</button>
        <button class="cat-btn" onclick="filtrar('extras')" id="btn-extras">Extras</button>
    </div>
    <div class="pos-right">
        <div class="prod-grid">
            {% for p in productos %}
            <div class="prod-card" data-cat="{{p.cat}}" onclick="location='/pos/add/{{p.id}}'">
                <img src="{{p.img_url}}"><h6>{{p.nombre}}</h6><small>${{p.precio}} | {{p.stock}}</small><br><small style="color:#888">{{p.categoria}}</small>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
<script>
function filtrar(cat){document.querySelectorAll('.cat-btn').forEach(b=>b.classList.remove('active'));document.getElementById('btn-'+cat).classList.add('active');document.querySelectorAll('.prod-card').forEach(c=>{if(cat=='todos'||c.dataset.cat==cat)c.style.display='block';else c.style.display='none';})}
function pagar(tipo){fetch('/pos/pagar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tipo:tipo})}).then(r=>r.json()).then(d=>{if(d.ok)location='/ticket/'+d.ticket_id; else alert(d.error)})}
</script>
""", productos=productos, carrito=carrito, total=total, ventas=ventas, fecha=datetime.now().strftime("%d/%m/%Y %H:%M"), mesas_ocupadas=mesas_ocupadas)

@app.route('/pos/add/<int:id>')
def pos_add(id):
    prod=Producto.query.get(id); carrito=session.get('carrito',[]);
    for it in carrito:
        if it['id']==prod.id: it['cant']+=1; session['carrito']=carrito; return redirect('/dashboard')
    carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':prod.precio,'cant':1}); session['carrito']=carrito; return redirect('/dashboard')
@app.route('/pos/cant/<int:index>/<int:delta>')
def pos_cant(index,delta):
    carrito=session.get('carrito',[]);
    if 0 <= index < len(carrito):
        carrito[index]['cant']+=delta
        if carrito[index]['cant']<=0: carrito.pop(index)
        session['carrito']=carrito
    return redirect('/dashboard')
@app.route('/pos/clear')
def pos_clear(): session['carrito']=[]; return redirect('/dashboard')
@app.route('/pos/pagar', methods=['POST'])
def pos_pagar():
    data=request.get_json(); metodo=data.get('tipo','efectivo'); carrito=session.get('carrito',[]); last=None
    for it in carrito:
        v=Venta(cliente='Mostrador',producto_nombre=it['nombre'],cantidad=it['cant'],total=it['precio']*it['cant'],vendedor=session.get('user'),metodo_pago=metodo); db.session.add(v); db.session.flush(); last=v.id
    db.session.commit(); session['carrito']=[]; return jsonify({'ok':True,'ticket_id':last})

@app.route('/mesas')
def mesas_view():
    mesas=Mesa.query.all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px">{% for m in mesas %}<div style="background:{% if m.estado=='ocupada' %}#fde8e8{% else %}#e8f5e9{% endif %};color:black;padding:15px;border-radius:10px;text-align:center;cursor:pointer" onclick="location='/mesa/{{m.id}}'"><b>{{m.nombre}}</b><br>{{m.estado}}<br>${{m.total}}</div>{% endfor %}</div></div>""", mesas=mesas)

@app.route('/mesa/<int:id>')
def mesa_detalle(id):
    mesa=Mesa.query.get(id)
    if mesa.unida_a_id: mesa=get_mesa_principal(mesa); return redirect(f'/mesa/{mesa.id}')
    productos=Producto.query.filter_by(disponible=True).all()
    for p in productos: p.img_url=get_producto_imagen(p)
    carrito=session.get(f'mesa_carrito_{id}',[]); total_nuevo=sum([x['precio']*x['cant'] for x in carrito]); comandas=[c for c in mesa.comandas if c.estado!='entregado']
    return render_template_string(STYLE_BASE+nav()+"""
<div style="display:flex;height:calc(100vh - 60px);gap:10px;padding:10px">
<div style="width:45%;background:#111;border:2px solid #00e5ff;border-radius:12px;padding:10px;overflow:auto">
<h6 style="color:#00e5ff">{{mesa.nombre}} - ${{mesa.total or 0}}</h6>
{% for c in comandas %}<div style="background:white;color:black;padding:6px;border-radius:6px;margin-bottom:5px;font-size:12px"><b>{{c.cantidad}}x {{c.producto_nombre}}</b> {% if c.comentario %}<span style="background:#c62828;color:white;padding:2px 4px;border-radius:4px">💬 {{c.comentario}}</span>{% endif %}<form action="/mesa/{{mesa.id}}/comanda/coment/{{c.id}}" method="POST" style="display:flex;gap:3px;margin-top:3px"><input name="comentario" value="{{c.comentario}}" class="form-control" style="font-size:11px" placeholder="Editar comentario"><button>Guardar</button></form></div>{% endfor %}
<hr><b style="color:#ffcc00;font-size:12px">Nuevo ticket - comentario ANTES</b>
{% for it in carrito %}<div style="background:#fffde7;color:black;padding:5px;border-radius:4px;margin-top:5px;font-size:12px">{{it.nombre}} x{{it.cant}}<form action="/mesa/{{mesa.id}}/carrito/coment/{{loop.index0}}" method="POST" style="display:flex;gap:3px"><input name="comentario" value="{{it.comentario}}" class="form-control" style="font-size:11px" placeholder="💬 Comentario"><button>💾</button></form></div>{% endfor %}
<div style="margin-top:10px"><b>Total Final ${{(mesa.total or 0)+total_nuevo}}</b><br><a href="/mesa/{{mesa.id}}/enviar" style="background:#00e5ff;color:black;padding:8px;display:block;text-align:center;border-radius:6px;margin-top:5px">MANDAR A COCINA</a><a href="/mesa/{{mesa.id}}/cobrar" style="background:#25D366;color:white;padding:8px;display:block;text-align:center;border-radius:6px;margin-top:5px">💰 COBRAR MESA</a></div>
</div>
<div style="width:55%;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;overflow:auto">
{% for p in productos %}<div style="background:white;color:#333;border-radius:8px;padding:6px;text-align:center;cursor:pointer" onclick="location='/mesa/{{mesa.id}}/add/{{p.id}}'"><img src="{{p.img_url}}" style="width:60px;height:60px;object-fit:cover;border-radius:6px;background:#eee"><br><small>{{p.nombre}}</small><br><small>${{p.precio}}</small></div>{% endfor %}
</div>
</div>
""", mesa=mesa, productos=productos, carrito=carrito, comandas=comandas, total_nuevo=total_nuevo)

@app.route('/mesa/<int:mesa_id>/add/<int:prod_id>')
def mesa_add(mesa_id, prod_id):
    prod=Producto.query.get(prod_id); carrito=session.get(f'mesa_carrito_{mesa_id}',[])
    for it in carrito:
        if it['id']==prod.id and it.get('comentario','')=='': it['cant']+=1; session[f'mesa_carrito_{mesa_id}']=carrito; return redirect(f'/mesa/{mesa_id}')
    carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':prod.precio,'cant':1,'comentario':''}); session[f'mesa_carrito_{mesa_id}']=carrito; return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:mesa_id>/carrito/coment/<int:index>', methods=['POST'])
def mesa_carrito_coment(mesa_id,index):
    carrito=session.get(f'mesa_carrito_{mesa_id}',[]); carrito[index]['comentario']=request.form.get('comentario','')[:200]; session[f'mesa_carrito_{mesa_id}']=carrito; return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:mesa_id>/enviar')
def mesa_enviar(mesa_id):
    mesa=Mesa.query.get(mesa_id); carrito=session.get(f'mesa_carrito_{mesa_id}',[])
    for it in carrito:
        com=Comanda(mesa_id=mesa.id,producto_nombre=it['nombre'],cantidad=it['cant'],mesero=session.get('user'),estado='cocina',comentario=it.get('comentario','')); mesa.total=(mesa.total or 0)+it['precio']*it['cant']; db.session.add(com)
    db.session.commit(); session[f'mesa_carrito_{mesa_id}']=[]; return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:mesa_id>/comanda/coment/<int:com_id>', methods=['POST'])
def comanda_coment(mesa_id,com_id):
    c=Comanda.query.get(com_id); c.comentario=request.form.get('comentario','')[:200]; db.session.commit(); return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:id>/cobrar')
def mesa_cobrar_view(id):
    mesa=Mesa.query.get(id); total=mesa.total or 0
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4" style="max-width:500px"><div class="card" style="border-color:#25D366"><h4>💰 Cobrar {{mesa.nombre}} - ${{total}}</h4><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:15px"><a href="/mesa/{{mesa.id}}/cobrar_final/efectivo" style="background:#25D366;color:white;padding:20px;text-align:center;border-radius:8px">💵<br>Efectivo</a><a href="/mesa/{{mesa.id}}/cobrar_final/tarjeta" style="background:#3f51b5;color:white;padding:20px;text-align:center;border-radius:8px">💳<br>Tarjeta</a><a href="/mesa/{{mesa.id}}/cobrar_final/transferencia" style="background:#0097a7;color:white;padding:20px;text-align:center;border-radius:8px">🏦<br>Transfer</a></div></div></div>""", mesa=mesa, total=total)
@app.route('/mesa/<int:id>/cobrar_final/<metodo>')
def mesa_cobrar_final(id,metodo):
    mesa=Mesa.query.get(id)
    for c in list(mesa.comandas):
        if c.estado!='entregado':
            v=Venta(cliente=mesa.nombre,producto_nombre=c.producto_nombre+(f" ({c.comentario})" if c.comentario else ""),cantidad=c.cantidad,total=10*c.cantidad,vendedor=session.get('user'),metodo_pago=metodo); db.session.add(v); c.estado='entregado'
    mesa.estado='libre'; mesa.total=0; db.session.commit(); return redirect('/mesas')

@app.route('/cocina')
def cocina_view():
    if 'user' not in session: return redirect('/')
    comandas=Comanda.query.filter_by(estado='cocina').all()
    from collections import defaultdict
    grupos=defaultdict(list)
    for c in comandas:
        principal=get_mesa_principal(c.mesa) if c.mesa else None
        key=principal.id if principal else c.mesa_id
        grupos[key].append(c)
    grupos_list=[]
    for mesa_id, lista in grupos.items():
        mesa=Mesa.query.get(mesa_id)
        if mesa: grupos_list.append({'mesa':mesa,'comandas':lista})
    return render_template_string(STYLE_BASE+nav()+"""<div class="container-fluid mt-3"><h3 style="color:#ffcc00">🔥 Cocina - {{grupos_list|length}} mesas</h3><div class="row g-3 mt-2">{% for g in grupos_list %}<div class="col-md-4"><div class="card" style="border-color:#ff4d3a;background:#1a1a0a"><h5 style="color:#00e5ff">🪑 {{g.mesa.nombre}}</h5>{% for c in g.comandas %}<div style="background:white;color:black;padding:6px;border-radius:6px;margin-bottom:5px"><b>{{c.cantidad}}x {{c.producto_nombre}}</b><br>{% if c.comentario %}<span style="background:#c62828;color:white;padding:2px 6px;border-radius:4px;font-size:11px">💬 {{c.comentario}}</span>{% endif %}</div>{% endfor %}<a href="/cocina/mesa_listo/{{g.mesa.id}}" class="btn-rosa w-100 mt-2" style="background:#25D366">✅ MESA LISTA</a></div></div>{% endfor %}{% if not grupos_list %}<div class="col-12 text-center p-4"><h4 style="color:#25D366">Sin pedidos 🟢</h4></div>{% endif %}</div></div><script>setTimeout(()=>location.reload(),15000)</script>""", grupos_list=grupos_list)

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
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div style="background:white;color:#333;border-radius:4px;padding:15px"><div style="display:flex;justify-content:space-between"><h4>📦 Productos ({{productos|length}})</h4><a href="/productos/nuevo" style="background:#4caf50;color:white;padding:8px 16px;border-radius:4px;text-decoration:none">+ Crear artículo</a></div><table class="table mt-3"><tr><th>Foto</th><th>Nombre</th><th>Categoría</th><th>Precio</th><th>Stock</th><th></th></tr>{% for p in productos %}<tr><td><img src="{{p.img_url}}" style="width:45px;height:45px;object-fit:cover;border-radius:6px"></td><td>{{p.nombre}}<br><small style="color:#888">{{p.descripcion[:30]}}</small></td><td>{{p.categoria}}</td><td>${{p.precio}}</td><td>{{p.stock}}</td><td><a href="/productos/eliminar/{{p.id}}" style="color:red">Borrar</a></td></tr>{% endfor %}</table></div></div>""", productos=productos)

@app.route('/productos/nuevo', methods=['GET','POST'])
def productos_nuevo():
    if not session.get('is_admin'): return redirect('/dashboard')
    if request.method=='POST':
        imagen_path=""
        if 'imagen' in request.files:
            imagen_path=save_upload(request.files['imagen'])
        p=Producto(nombre=request.form.get('nombre','').strip() or 'Sin nombre',descripcion=request.form.get('descripcion',''),categoria=request.form.get('categoria','Sin categoria'),disponible='disponible' in request.form,vendido_por=request.form.get('vendido_por','Unidad'),precio=float(request.form.get('precio') or 0),costo=float(request.form.get('coste') or 0),ref=request.form.get('ref',''),codigo_barras=request.form.get('codigo_barras',''),stock=int(request.form.get('en_stock') or 0),imagen=imagen_path)
        db.session.add(p); db.session.commit(); return redirect('/productos')
    return render_template_string(STYLE_BASE+nav()+"""
<div style="background:#eee;min-height:100vh">
<div class="header-verde">☰ Crear artículo <a href="/productos" style="margin-left:auto;background:#388e3c;color:white;padding:6px 12px;border-radius:4px;text-decoration:none;font-size:13px">← Volver</a></div>
<form method="POST" enctype="multipart/form-data">
<div class="card-blanca">
<div class="row"><div class="col-md-8"><label class="label-small">Nombre</label><input name="nombre" class="input-line" placeholder="Ej: Agua, botella 0.5L" style="font-size:22px;font-weight:bold"></div><div class="col-md-4"><label class="label-small">Categoría</label><select name="categoria" class="input-line"><option>Sin categoría</option><option>Lechón</option><option>Tortas</option><option>Órdenes</option><option>Bebidas</option><option>Extras</option></select></div></div>
<label class="label-small">Descripción</label><textarea name="descripcion" class="input-line" rows="2" placeholder="Descripción"></textarea>
<div style="margin-top:15px"><input type="checkbox" name="disponible" checked> El artículo está disponible para la venta</div>
<div style="margin-top:10px"><label class="label-small">Vendido por</label><label><input type="radio" name="vendido_por" value="Unidad" checked> Unidad</label> <label style="margin-left:15px"><input type="radio" name="vendido_por" value="Peso/Volumen"> Peso/Volumen</label></div>
<div class="row" style="margin-top:15px"><div class="col-md-6"><label class="label-small">Precio</label><input name="precio" type="number" step="0.01" class="input-line" placeholder="10,00"></div><div class="col-md-6"><label class="label-small">Coste</label><input name="coste" type="number" step="0.01" class="input-line" placeholder="5,00"></div></div>
<div class="row" style="margin-top:10px"><div class="col-md-6"><label class="label-small">REF</label><input name="ref" class="input-line" placeholder="10028"></div><div class="col-md-6"><label class="label-small">Código de barras</label><input name="codigo_barras" class="input-line"></div></div>
<div style="margin-top:15px"><label class="label-small">Foto (visible para TODOS: cajero, mesero, cocina)</label><input name="imagen" type="file" class="form-control" accept="image/*"></div>
</div>
<div class="card-blanca"><h5>Inventario</h5><div class="row" style="margin-top:10px"><div class="col-md-6"><label class="label-small">En stock</label><input name="en_stock" type="number" class="input-line" placeholder="0"></div></div><button style="background:#4caf50;color:white;border:none;padding:12px 30px;border-radius:4px;margin-top:20px">💾 Guardar artículo</button></div>
</form>
</div>
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
        if 'logo' in request.files:
            new_logo=save_upload(request.files['logo'])
            if new_logo: cfg.logo_path=new_logo
        db.session.commit(); return redirect('/admin/config')
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4" style="max-width:600px"><div class="card"><h4>⚙️ Config + Logo</h4><div class="text-center"><img src="/static/{{cfg.logo_path}}" style="width:100px;height:100px;border-radius:50%;background:white;padding:5px;object-fit:cover"></div><form method="POST" enctype="multipart/form-data" class="mt-3"><input name="logo" type="file" class="form-control mb-3" accept="image/*"><button class="btn-rosa w-100">Guardar Logo</button></form></div></div>""", cfg=cfg)

@app.route('/ticket/<int:id>')
def ticket(id):
    v=Venta.query.get(id); return render_template_string(STYLE_BASE+f'<div class="container mt-5" style="max-width:350px"><div class="card" style="background:white;color:black"><h5>Ticket #{v.id}</h5><p>{v.producto_nombre}<br>Total ${v.total}<br>Pago {v.metodo_pago}</p></div></div>')

@app.route('/ventas')
def ventas():
    vs=Venta.query.order_by(Venta.id.desc()).all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card"><h5>Ventas</h5><table class="table table-dark"><tr><th>Producto</th><th>Total</th><th>Pago</th></tr>{% for v in vs %}<tr><td>{{v.producto_nombre}}</td><td>${{v.total}}</td><td>{{v.metodo_pago}}</td></tr>{% endfor %}</table></div></div>""", vs=vs)

@app.route('/reporte')
def reporte():
    vs=Venta.query.all(); total=sum([v.total for v in vs])
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card"><h4>Total ${{total}}</h4></div></div>""", total=total)

@app.route('/dueno')
def dueno():
    if not session.get('is_admin'): return redirect('/dashboard')
    vs=Venta.query.all(); total=sum([v.total for v in vs])
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card"><h4>💰 Dueño ${{total}}</h4></div></div>""", total=total)

@app.route('/admin/usuarios', methods=['GET','POST'])
def admin_usuarios():
    if not session.get('is_admin'): return redirect('/dashboard')
    if request.method=='POST':
        if not User.query.filter_by(username=request.form['username']).first():
            es_admin='is_admin' in request.form; rol=request.form.get('rol','cajero')
            if es_admin: rol='admin'
            db.session.add(User(username=request.form['username'],password=generate_password_hash(request.form['password']),is_admin=es_admin,rol=rol)); db.session.commit()
        return redirect('/admin/usuarios')
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card"><h5>Usuarios</h5><form method="POST" class="row g-2"><div class="col-md-3"><input name="username" class="form-control" placeholder="Usuario" required></div><div class="col-md-3"><input name="password" class="form-control" placeholder="Contraseña" required></div><div class="col-md-2"><select name="rol" class="form-control"><option value="cajero">Cajero</option><option value="mesero">Mesero</option><option value="cocina">Cocina</option></select></div><div class="col-md-2"><label><input type="checkbox" name="is_admin"> Admin</label></div><div class="col-md-2"><button class="btn-rosa">Crear</button></div></form><table class="table table-dark mt-3"><tr><th>Usuario</th><th>Rol</th></tr>{% for u in usuarios %}<tr><td>{{u.username}}</td><td>{{u.rol}}</td></tr>{% endfor %}</table></div></div>""", usuarios=User.query.all())

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))