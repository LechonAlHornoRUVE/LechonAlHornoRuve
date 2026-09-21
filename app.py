from flask import Flask, request, redirect, session, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import func
import os

app = Flask(__name__)
app.secret_key = 'ruve-final-negro-rosado-completo'

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
class Categoria(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(50), unique=True)
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
    inventario_bajo=db.Column(db.Integer, default=0)
    proveedor=db.Column(db.String(100), default="")
    costo_compra=db.Column(db.Float, default=0)
class Venta(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    cliente=db.Column(db.String(100))
    producto_nombre=db.Column(db.String(100))
    cantidad=db.Column(db.Integer)
    total=db.Column(db.Float)
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    vendedor=db.Column(db.String(80), default="admin")
    costo_total=db.Column(db.Float, default=0)
    metodo_pago=db.Column(db.String(20), default="efectivo")
class Gasto(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    concepto=db.Column(db.String(100))
    monto=db.Column(db.Float)
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
class Config(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    logo_path=db.Column(db.String(200), default="logo.png")
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

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin',password=generate_password_hash('admin123'),is_admin=True,rol='admin'))
    if Categoria.query.count()==0:
        for cat in ["Sin categoría","Lechón","Tortas","Órdenes","Bebidas","Extras"]:
            db.session.add(Categoria(nombre=cat))
    if Producto.query.count()==0:
        db.session.add(Producto(nombre='Lechón por Kilo',precio=350,stock=50,categoria='Lechón'))
        db.session.add(Producto(nombre='Torta de Lechón',precio=70,stock=30,categoria='Tortas'))
        db.session.add(Producto(nombre='Refresco',precio=25,stock=100,categoria='Bebidas'))
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
.dropdown{position:relative;display:inline-block}
.dropbtn{background:#111;color:#ff4d8a;border:2px solid #ff4d8a;padding:6px 14px;border-radius:8px;font-weight:bold;cursor:pointer}
.dropdown-content{display:none;position:absolute;right:0;background:#111;border:2px solid #ff4d8a;border-radius:10px;min-width:230px;z-index:9999;box-shadow:0 8px 16px rgba(0,0,0,0.9)}
.dropdown-content a{display:block;padding:12px 16px;color:white;text-decoration:none;font-size:13px;border-bottom:1px solid #222}
.dropdown-content a:hover{background:#222;color:#ff4d8a}
.dropdown-content.show{display:block}
/* NEGRO Y ROSADO CREAR ARTICULO */
.crear-wrapper{background:#000;min-height:100vh;color:white}
.header-rosa{background:#000;border-bottom:3px solid #ff4d8a;color:#ff4d8a;padding:14px 20px;display:flex;align-items:center;font-weight:bold;font-size:18px;letter-spacing:1px}
.card-negra{background:#111;border:2px solid #ff4d8a;border-radius:12px;padding:20px;margin:15px;box-shadow:0 0 15px rgba(255,77,138,0.25)}
.input-rosa{border:none!important;border-bottom:2px solid #ff4d8a!important;background:#111!important;color:white!important;border-radius:0!important;padding:10px 0!important;width:100%}
.input-rosa::placeholder{color:#555}
.label-rosa{font-size:11px;color:#ff4d8a;margin-top:18px;display:block;font-weight:bold;letter-spacing:0.5px}
.select-rosa{background:#111!important;color:white!important;border:2px solid #ff4d8a!important;border-radius:8px!important;padding:8px!important}
.btn-rosa-neon{background:#ff4d8a;color:white;border:none;padding:12px 30px;border-radius:10px;font-weight:bold;box-shadow:0 0 10px rgba(255,77,138,0.5)}
</style>
"""

def nav():
    cfg=get_config(); rol=session.get('rol','cajero'); is_admin=session.get('is_admin', False); user=session.get('user','')
    logo_url=f"/static/{cfg.logo_path}"
    if not is_admin and rol=='cocina':
        return f'<nav class="navbar"><div class="d-flex align-items-center"><img src="{logo_url}" style="width:40px;height:40px;border-radius:50%;background:white;padding:3px;object-fit:cover"><h6 class="m-0 ms-2" style="color:#ffcc00">Cocina {user}</h6></div><div><a href="/cocina" class="me-3" style="color:#ffcc00;font-weight:bold">🔥 Cocina</a><a href="/logout">Salir</a></div></nav>'
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
            <a href="/productos/nuevo">➕ Crear artículo NEGRO/ROSADO</a>
            <a href="/categorias">🏷️ Categorías editables</a>
            <a href="/ventas">🧾 Ventas</a>
            <a href="/reporte">📊 Reporte</a>
            <a href="/dueno" style="color:#ff4d8a">💰 Dueño + Gráfica</a>
            <a href="/admin/config">⚙️ Config + Logo + POS mesero</a>
            <a href="/admin/usuarios">👥 Usuarios</a>
          </div>
        </div>
        <script>
        function toggleDropdown(){{ document.getElementById("adminDropdown").classList.toggle("show"); }}
        window.onclick = function(e){{ if (!e.target.matches('.dropbtn')) {{ var d=document.getElementById("adminDropdown"); if(d && d.classList.contains('show')) d.classList.remove('show'); }} }}
        </script>
        '''
    else:
        if rol=='cajero': links+='<a href="/ventas" class="me-3">Ventas</a><a href="/reporte" class="me-3">Reporte</a>'
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
    cfg=get_config(); rol=session.get('rol'); is_admin=session.get('is_admin')
    if not is_admin and rol=='mesero' and not cfg.mod_pos_mesero: return redirect('/mesas')
    if not is_admin and rol=='cocina': return redirect('/cocina')
    productos=Producto.query.filter_by(disponible=True).all()
    for p in productos: p.img_url=get_producto_imagen(p)
    carrito=session.get('carrito',[]); total=sum([x['precio']*x['cant'] for x in carrito])
    hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    ventas=Venta.query.filter(Venta.fecha>=hoy).order_by(Venta.id.desc()).limit(6).all()
    mesas_ocupadas=[m for m in Mesa.query.filter_by(estado='ocupada').all() if not m.unida_a_id]
    cats=Categoria.query.all()
    return render_template_string(STYLE_BASE+nav()+"""
<div class="pos-container">
    <div class="pos-left">
        <div class="ticket-header"><small style="color:#aaa">Mostrador - {{fecha}}</small></div>
        <div class="ticket-body">
            <div style="display:flex;justify-content:space-between;font-weight:bold;border-bottom:2px solid black;padding-bottom:5px;font-size:11px"><span>#</span><span>Artículo</span><span>Total</span></div>
            {% for item in carrito %}<div style="display:flex;justify-content:space-between;border-bottom:1px dashed #ccc;padding:6px 0;font-size:12px"><span>{{loop.index}} {{item.nombre}} x{{item.cant}}</span><span>${{item.precio*item.cant}}</span></div>{% endfor %}
            {% if not carrito %}<p style="color:#888;text-align:center;margin-top:20px">Toca un producto →</p>{% endif %}
            {% if mesas_ocupadas %}<hr><div style="background:#fff3cd;color:black;padding:6px;border-radius:6px;font-size:11px"><b>🪑 Mesas por cobrar (mesero → caja):</b>{% for m in mesas_ocupadas %}<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px dashed #ccc"><span>{{m.nombre}} ${{m.total}}</span><a href="/mesa/{{m.id}}/cobrar" style="background:#25D366;color:white;padding:2px 6px;border-radius:4px">Cobrar</a></div>{% endfor %}</div>{% endif %}
        </div>
        <div class="ticket-footer">
            <div style="display:flex;justify-content:space-between;color:white;font-weight:bold;font-size:18px"><span>Total</span><span>${{total}}</span></div>
            <div style="display:flex;gap:6px;margin-top:10px">
                <button onclick="pagar('efectivo')" class="btn-cash">💵 Efectivo</button>
                <button onclick="pagar('tarjeta')" class="btn-pay">💳 Tarjeta</button>
                <button onclick="pagar('transferencia')" class="btn-trans">🏦 Transfer</button>
            </div>
            <a href="/pos/clear" style="display:block;text-align:center;background:#555;color:white;padding:8px;border-radius:8px;margin-top:8px">🗑️ Limpiar ticket</a>
            <div style="font-size:9px;color:#888;margin-top:6px">{% for v in ventas %}{{v.cliente}} ${{v.total}} {{v.metodo_pago}}<br>{% endfor %}</div>
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
                <img src="{{p.img_url}}"><h6>{{p.nombre}}</h6><small>${{p.precio}} Stock {{p.stock}}</small><br><small style="color:#888">{{p.categoria}}</small>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
<script>
function filtrar(cat){
  document.querySelectorAll('.cat-btn').forEach(b=>b.classList.remove('active'));
  let btn=document.getElementById('btn-'+cat); if(btn) btn.classList.add('active');
  document.querySelectorAll('.prod-card').forEach(c=>{if(cat=='todos'||c.dataset.cat==cat)c.style.display='block';else c.style.display='none';})
}
function pagar(tipo){fetch('/pos/pagar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tipo:tipo})}).then(r=>r.json()).then(d=>{if(d.ok)location='/ticket/'+d.ticket_id; else alert(d.error)})}
</script>
""", productos=productos, carrito=carrito, total=total, ventas=ventas, fecha=datetime.now().strftime("%d/%m/%Y %H:%M"), mesas_ocupadas=mesas_ocupadas, cats=cats)

@app.route('/pos/add/<int:id>')
def pos_add(id):
    prod=Producto.query.get(id);
    if not prod or prod.stock<=0: return redirect('/dashboard')
    carrito=session.get('carrito',[]);
    for it in carrito:
        if it['id']==prod.id: it['cant']+=1; session['carrito']=carrito; return redirect('/dashboard')
    carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':prod.precio,'cant':1}); session['carrito']=carrito; return redirect('/dashboard')
@app.route('/pos/clear')
def pos_clear(): session['carrito']=[]; return redirect('/dashboard')
@app.route('/pos/pagar', methods=['POST'])
def pos_pagar():
    data=request.get_json(); metodo=data.get('tipo','efectivo'); carrito=session.get('carrito',[]); last=None
    for it in carrito:
        prod=Producto.query.get(it['id'])
        if prod: prod.stock-=it['cant']
        v=Venta(cliente='Mostrador',producto_nombre=it['nombre'],cantidad=it['cant'],total=it['precio']*it['cant'],vendedor=session.get('user'),metodo_pago=metodo); db.session.add(v); db.session.flush(); last=v.id
    db.session.commit(); session['carrito']=[]; return jsonify({'ok':True,'ticket_id':last})

@app.route('/mesas')
def mesas_view():
    mesas=Mesa.query.all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px">{% for m in mesas %}<div style="background:{% if m.estado=='ocupada' %}#fde8e8{% else %}#e8f5e9{% endif %};color:black;padding:15px;border-radius:10px;text-align:center;cursor:pointer;border:2px solid {% if m.estado=='ocupada' %}#c62828{% else %}#2e7d32{% endif %}" onclick="location='/mesa/{{m.id}}'"><b>{{m.nombre}}</b><br><small>{{m.estado}}</small><br><b>${{m.total}}</b></div>{% endfor %}</div></div>""", mesas=mesas)

@app.route('/mesa/<int:id>')
def mesa_detalle(id):
    mesa=Mesa.query.get(id)
    if mesa.unida_a_id: mesa=get_mesa_principal(mesa); return redirect(f'/mesa/{mesa.id}')
    productos=Producto.query.filter_by(disponible=True).all()
    for p in productos: p.img_url=get_producto_imagen(p)
    carrito=session.get(f'mesa_carrito_{id}',[]); total_nuevo=sum([x['precio']*x['cant'] for x in carrito]); comandas=[c for c in mesa.comandas if c.estado!='entregado']
    return render_template_string(STYLE_BASE+nav()+"""
<div style="display:flex;height:calc(100vh - 60px);gap:10px;padding:10px">
<div style="width:45%;background:#111;border:2px solid #00e5ff;border-radius:12px;padding:10px;overflow:auto;display:flex;flex-direction:column">
<h6 style="color:#00e5ff">{{mesa.nombre}} - ${{mesa.total or 0}}</h6>
<div style="flex:1;overflow:auto">
{% for c in comandas %}<div style="background:white;color:black;padding:6px;border-radius:6px;margin-bottom:5px;font-size:12px"><b>{{c.cantidad}}x {{c.producto_nombre}}</b> {% if c.comentario %}<span style="background:#c62828;color:white;padding:2px 4px;border-radius:4px">💬 {{c.comentario}}</span>{% endif %}<form action="/mesa/{{mesa.id}}/comanda/coment/{{c.id}}" method="POST" style="display:flex;gap:3px;margin-top:3px"><input name="comentario" value="{{c.comentario}}" class="form-control" style="font-size:11px" placeholder="Editar comentario"><button style="font-size:10px;background:#ffcc00;border:none;border-radius:4px;padding:2px 6px">Guardar</button></form></div>{% endfor %}
<hr><b style="color:#ffcc00;font-size:12px">NUEVO - COMENTARIO ANTES DE COCINA</b>
{% for it in carrito %}<div style="background:#fffde7;color:black;padding:5px;border-radius:4px;margin-top:5px;font-size:12px">{{it.nombre}} x{{it.cant}} - ${{it.precio*it.cant}}<form action="/mesa/{{mesa.id}}/carrito/coment/{{loop.index0}}" method="POST" style="display:flex;gap:3px;margin-top:2px"><input name="comentario" value="{{it.comentario}}" class="form-control" style="font-size:11px" placeholder="💬 Comentario antes de cocina"><button style="font-size:10px">💾</button></form></div>{% endfor %}
</div>
<div style="border-top:2px solid #ff4d8a;padding-top:8px;margin-top:8px"><b>Total Final ${{(mesa.total or 0)+total_nuevo}}</b><br><a href="/mesa/{{mesa.id}}/enviar" style="background:#00e5ff;color:black;padding:10px;display:block;text-align:center;border-radius:8px;margin-top:5px;font-weight:bold">🍽️ MANDAR A COCINA</a><a href="/mesa/{{mesa.id}}/cobrar" style="background:#25D366;color:white;padding:10px;display:block;text-align:center;border-radius:8px;margin-top:8px;font-weight:bold">💰 COBRAR MESA (Elige método)</a><a href="/mesas" style="background:#333;color:white;padding:6px;display:block;text-align:center;border-radius:6px;margin-top:6px">Volver</a></div>
</div>
<div style="width:55%;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;overflow:auto;align-content:start">
{% for p in productos %}<div style="background:white;color:#333;border-radius:8px;padding:6px;text-align:center;cursor:pointer;border:2px solid #222" onclick="location='/mesa/{{mesa.id}}/add/{{p.id}}'"><img src="{{p.img_url}}" style="width:60px;height:60px;object-fit:cover;border-radius:6px;background:#eee"><br><small style="font-weight:bold">{{p.nombre}}</small><br><small>${{p.precio}}</small></div>{% endfor %}
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
    carrito=session.get(f'mesa_carrito_{mesa_id}',[]);
    if 0 <= index < len(carrito):
        carrito[index]['comentario']=request.form.get('comentario','')[:200]; session[f'mesa_carrito_{mesa_id}']=carrito
    return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:mesa_id>/enviar')
def mesa_enviar(mesa_id):
    mesa=Mesa.query.get(mesa_id); carrito=session.get(f'mesa_carrito_{mesa_id}',[])
    if not carrito: return redirect(f'/mesa/{mesa_id}')
    for it in carrito:
        prod=Producto.query.get(it['id'])
        if prod: prod.stock-=it['cant']
        com=Comanda(mesa_id=mesa.id,producto_nombre=it['nombre'],cantidad=it['cant'],mesero=session.get('user'),estado='cocina',comentario=it.get('comentario','')); mesa.total=(mesa.total or 0)+it['precio']*it['cant']; db.session.add(com)
    db.session.commit(); session[f'mesa_carrito_{mesa_id}']=[]; return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:mesa_id>/comanda/coment/<int:com_id>', methods=['POST'])
def comanda_coment(mesa_id,com_id):
    c=Comanda.query.get(com_id); c.comentario=request.form.get('comentario','')[:200]; db.session.commit(); return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:id>/cobrar')
def mesa_cobrar_view(id):
    mesa=Mesa.query.get(id)
    if mesa.unida_a_id: mesa=get_mesa_principal(mesa)
    total=mesa.total or 0
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4" style="max-width:500px"><div class="card" style="border-color:#25D366"><h4 style="color:#25D366">💰 Cobrar {{mesa.nombre}} - ${{total}}</h4><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:15px"><a href="/mesa/{{mesa.id}}/cobrar_final/efectivo" style="background:#25D366;color:white;padding:20px;text-align:center;border-radius:10px;font-weight:bold;text-decoration:none">💵<br>Efectivo</a><a href="/mesa/{{mesa.id}}/cobrar_final/tarjeta" style="background:#3f51b5;color:white;padding:20px;text-align:center;border-radius:10px;font-weight:bold;text-decoration:none">💳<br>Tarjeta</a><a href="/mesa/{{mesa.id}}/cobrar_final/transferencia" style="background:#0097a7;color:white;padding:20px;text-align:center;border-radius:10px;font-weight:bold;text-decoration:none">🏦<br>Transfer</a></div><a href="/mesa/{{mesa.id}}" class="btn btn-dark w-100 mt-3">Volver</a></div></div>""", mesa=mesa, total=total)
@app.route('/mesa/<int:id>/cobrar_final/<metodo>')
def mesa_cobrar_final(id,metodo):
    mesa=Mesa.query.get(id)
    if mesa.unida_a_id: mesa=get_mesa_principal(mesa)
    for c in list(mesa.comandas):
        if c.estado!='entregado':
            prod=Producto.query.filter_by(nombre=c.producto_nombre).first()
            precio=prod.precio if prod else 10
            costo=(prod.costo if prod else 0)*c.cantidad
            v=Venta(cliente=mesa.nombre,producto_nombre=c.producto_nombre+(f" ({c.comentario})" if c.comentario else ""),cantidad=c.cantidad,total=precio*c.cantidad,costo_total=costo,vendedor=session.get('user'),metodo_pago=metodo); db.session.add(v); c.estado='entregado'
    for m in list(mesa.mesas_unidas): m.unida_a_id=None; m.estado='libre'; m.total=0
    mesa.estado='libre'; mesa.total=0; db.session.commit()
    v=Venta.query.filter_by(vendedor=session.get('user')).order_by(Venta.id.desc()).first()
    if v: return redirect(f'/ticket/{v.id}')
    return redirect('/mesas')

@app.route('/cocina')
def cocina_view():
    if 'user' not in session: return redirect('/')
    comandas=Comanda.query.filter_by(estado='cocina').order_by(Comanda.fecha.asc()).all()
    from collections import defaultdict
    grupos=defaultdict(list)
    for c in comandas:
        principal=get_mesa_principal(c.mesa) if c.mesa else None
        key=principal.id if principal else c.mesa_id
        grupos[key].append(c)
    grupos_list=[{'mesa':Mesa.query.get(mid),'comandas':lista} for mid,lista in grupos.items() if Mesa.query.get(mid)]
    return render_template_string(STYLE_BASE+nav()+"""<div class="container-fluid mt-3"><h3 style="color:#ffcc00">🔥 Cocina - {{grupos_list|length}} mesas</h3><div class="row g-3 mt-2">{% for g in grupos_list %}<div class="col-md-4"><div class="card" style="border-color:#ff4d3a;background:#1a1a0a"><h5 style="color:#00e5ff">🪑 {{g.mesa.nombre}} {% if g.mesa.mesas_unidas %}<small style="color:#ffcc00">+{{g.mesa.mesas_unidas|length}}</small>{% endif %}</h5>{% for c in g.comandas %}<div style="background:white;color:black;padding:6px;border-radius:6px;margin-bottom:5px"><b>{{c.cantidad}}x {{c.producto_nombre}}</b><br>{% if c.comentario %}<span style="background:#c62828;color:white;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:bold">💬 {{c.comentario}}</span>{% endif %}<br><small style="color:#666">{{c.mesero}}</small></div>{% endfor %}<a href="/cocina/mesa_listo/{{g.mesa.id}}" class="btn-rosa w-100 mt-2" style="background:#25D366">✅ MESA LISTA</a></div></div>{% endfor %}{% if not grupos_list %}<div class="col-12 text-center p-4"><h4 style="color:#25D366">Sin pedidos 🟢</h4></div>{% endif %}</div></div><script>setTimeout(()=>location.reload(),15000)</script>""", grupos_list=grupos_list)

@app.route('/cocina/mesa_listo/<int:mesa_id>')
def cocina_mesa_listo(mesa_id):
    mesa=Mesa.query.get(mesa_id)
    if mesa.unida_a_id: mesa=get_mesa_principal(mesa)
    for c in mesa.comandas:
        if c.estado=='cocina': c.estado='listo'
    db.session.commit(); return redirect('/cocina')

@app.route('/categorias', methods=['GET','POST'])
def categorias_view():
    if not session.get('is_admin'): return redirect('/dashboard')
    if request.method=='POST':
        nombre=request.form.get('nombre','').strip()
        if nombre and not Categoria.query.filter_by(nombre=nombre).first():
            db.session.add(Categoria(nombre=nombre)); db.session.commit()
        return redirect('/categorias')
    cats=Categoria.query.all()
    return render_template_string(STYLE_BASE+nav()+"""
<div class="container mt-4" style="max-width:600px"><div style="background:#111;border:2px solid #ff4d8a;border-radius:12px;padding:20px;color:white">
<h4 style="color:#ff4d8a">🏷️ CATEGORÍAS - NEGRO Y ROSADO</h4>
<form method="POST" class="d-flex gap-2 mt-3">
<input name="nombre" class="form-control" placeholder="Nueva categoría ej: Postres" required style="background:#000!important;color:white!important;border:2px solid #ff4d8a!important">
<button style="background:#ff4d8a;color:white;border:none;padding:8px 16px;border-radius:8px;font-weight:bold">Crear</button>
</form>
<table class="table mt-3" style="color:white"><tr><th style="color:#ff4d8a">Nombre</th><th></th></tr>
{% for c in cats %}<tr><td style="color:white">{{c.nombre}}</td><td><a href="/categorias/eliminar/{{c.id}}" style="color:#ff4d8a" onclick="return confirm('¿Borrar?')">Borrar</a> | <a href="/categorias/editar/{{c.id}}" style="color:#ff4d8a">Editar</a></td></tr>{% endfor %}
</table>
<a href="/productos/nuevo" style="background:#ff4d8a;color:white;padding:8px 12px;border-radius:8px;text-decoration:none">← Volver a Crear artículo</a>
</div></div>
""", cats=cats)

@app.route('/categorias/eliminar/<int:id>')
def categorias_eliminar(id):
    if not session.get('is_admin'): return redirect('/dashboard')
    c=Categoria.query.get(id); db.session.delete(c); db.session.commit(); return redirect('/categorias')
@app.route('/categorias/editar/<int:id>', methods=['GET','POST'])
def categorias_editar(id):
    c=Categoria.query.get(id)
    if request.method=='POST':
        nombre=request.form.get('nombre','').strip()
        if nombre: c.nombre=nombre; db.session.commit()
        return redirect('/categorias')
    return render_template_string(STYLE_BASE+nav()+f'<div class="container mt-4" style="max-width:400px"><div style="background:#111;border:2px solid #ff4d8a;border-radius:12px;padding:20px"><h5 style="color:#ff4d8a">Editar categoría</h5><form method="POST"><input name="nombre" class="form-control" value="{c.nombre}" required style="background:#000!important;color:white!important;border:2px solid #ff4d8a!important"><button style="background:#ff4d8a;color:white;border:none;padding:8px 16px;border-radius:8px;margin-top:10px">Guardar</button></form></div></div>')
@app.route('/api/categorias/crear', methods=['POST'])
def api_categorias_crear():
    if not session.get('is_admin'): return jsonify({'ok':False})
    data=request.get_json(); nombre=data.get('nombre','').strip()
    if nombre and not Categoria.query.filter_by(nombre=nombre).first():
        db.session.add(Categoria(nombre=nombre)); db.session.commit(); return jsonify({'ok':True,'nombre':nombre})
    return jsonify({'ok':False})

@app.route('/productos')
def productos_list():
    if not session.get('is_admin'): return redirect('/dashboard')
    productos=Producto.query.all()
    for p in productos: p.img_url=get_producto_imagen(p)
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div style="background:#111;border:2px solid #ff4d8a;border-radius:12px;padding:15px;color:white"><div style="display:flex;justify-content:space-between;align-items:center"><h4 style="color:#ff4d8a">📦 Productos ({{productos|length}})</h4><a href="/productos/nuevo" style="background:#ff4d8a;color:white;padding:8px 16px;border-radius:8px;text-decoration:none;font-weight:bold">+ Crear artículo NEGRO/ROSADO</a></div><table class="table mt-3" style="color:white"><tr><th>Foto</th><th>Nombre</th><th>Categoría</th><th>Precio</th><th>Stock</th><th></th></tr>{% for p in productos %}<tr><td><img src="{{p.img_url}}" style="width:45px;height:45px;object-fit:cover;border-radius:6px;background:white"></td><td><b>{{p.nombre}}</b><br><small style="color:#888">{{p.descripcion[:30]}}</small></td><td>{{p.categoria}}</td><td>${{p.precio}}</td><td>{{p.stock}}</td><td><a href="/productos/eliminar/{{p.id}}" style="color:#ff4d8a">Borrar</a></td></tr>{% endfor %}</table></div></div>""", productos=productos)

@app.route('/productos/nuevo', methods=['GET','POST'])
def productos_nuevo():
    if not session.get('is_admin'): return redirect('/dashboard')
    categorias=Categoria.query.all()
    if request.method=='POST':
        imagen_path=""
        if 'imagen' in request.files:
            imagen_path=save_upload(request.files['imagen'])
        p=Producto(
            nombre=request.form.get('nombre','').strip() or 'Sin nombre',
            descripcion=request.form.get('descripcion',''),
            categoria=request.form.get('categoria','Sin categoria'),
            disponible='disponible' in request.form,
            vendido_por=request.form.get('vendido_por','Unidad'),
            precio=float(request.form.get('precio') or 0),
            costo=float(request.form.get('coste') or 0),
            costo_compra=float(request.form.get('costo_compra') or 0),
            ref=request.form.get('ref',''),
            codigo_barras=request.form.get('codigo_barras',''),
            stock=int(request.form.get('en_stock') or 0),
            inventario_bajo=int(request.form.get('inventario_bajo') or 0),
            proveedor=request.form.get('proveedor',''),
            imagen=imagen_path
        )
        db.session.add(p); db.session.commit(); return redirect('/productos')
    return render_template_string(STYLE_BASE+nav()+"""
<style>
.crear-wrapper{background:#000;min-height:100vh;color:white}
.header-rosa{background:#000;border-bottom:3px solid #ff4d8a;color:#ff4d8a;padding:14px 20px;display:flex;align-items:center;font-weight:bold;font-size:18px;letter-spacing:1px}
.card-negra{background:#111;border:2px solid #ff4d8a;border-radius:12px;padding:20px;margin:15px;box-shadow:0 0 15px rgba(255,77,138,0.25)}
.input-rosa{border:none!important;border-bottom:2px solid #ff4d8a!important;background:#111!important;color:white!important;border-radius:0!important;padding:10px 0!important;width:100%}
.input-rosa::placeholder{color:#555}
.label-rosa{font-size:11px;color:#ff4d8a;margin-top:18px;display:block;font-weight:bold;letter-spacing:0.5px}
.select-rosa{background:#111!important;color:white!important;border:2px solid #ff4d8a!important;border-radius:8px!important;padding:8px!important}
.btn-rosa-neon{background:#ff4d8a;color:white;border:none;padding:12px 30px;border-radius:10px;font-weight:bold;box-shadow:0 0 10px rgba(255,77,138,0.5)}
</style>
<div class="crear-wrapper">
<div class="header-rosa">☰ CREAR ARTÍCULO <a href="/productos" style="margin-left:auto;background:#111;color:#ff4d8a;border:2px solid #ff4d8a;padding:6px 14px;border-radius:8px;text-decoration:none;font-size:13px">← Volver</a></div>
<form method="POST" enctype="multipart/form-data">
<div class="card-negra">
<div class="row"><div class="col-md-6"><label class="label-rosa">NOMBRE *</label><input name="nombre" class="input-rosa" placeholder="Ej: Agua, botella 0.5L" style="font-size:20px;font-weight:bold" required></div>
<div class="col-md-4"><label class="label-rosa">CATEGORÍA (EDITABLE)</label>
<div style="display:flex;gap:5px"><select name="categoria" id="catSelect" class="select-rosa">
{% for cat in categorias %}<option value="{{cat.nombre}}">{{cat.nombre}}</option>{% endfor %}
</select><button type="button" onclick="nuevaCategoria()" style="background:#ff4d8a;color:white;border:none;padding:6px 10px;border-radius:8px;font-size:11px;font-weight:bold">+ Nueva</button></div>
</div>
<div class="col-md-2"><a href="/categorias" style="font-size:11px;color:#ff4d8a">Editar categorías</a></div>
</div>
<label class="label-rosa">DESCRIPCIÓN</label><textarea name="descripcion" class="input-rosa" rows="2" placeholder="Descripción opcional..."></textarea>
<div style="margin-top:18px"><input type="checkbox" name="disponible" checked style="accent-color:#ff4d8a;width:18px;height:18px"> <span style="color:white">El artículo está disponible para la venta</span></div>
<div style="margin-top:12px"><label class="label-rosa">VENDIDO POR</label><label style="color:white"><input type="radio" name="vendido_por" value="Unidad" checked style="accent-color:#ff4d8a"> Unidad</label> <label style="margin-left:20px;color:white"><input type="radio" name="vendido_por" value="Peso/Volumen" style="accent-color:#ff4d8a"> Peso/Volumen</label></div>
<div class="row" style="margin-top:15px"><div class="col-md-6"><label class="label-rosa">PRECIO</label><input name="precio" type="number" step="0.01" class="input-rosa" placeholder="€10,00"></div><div class="col-md-6"><label class="label-rosa">COSTE</label><input name="coste" type="number" step="0.01" class="input-rosa" placeholder="€5,00"></div></div>
<div class="row" style="margin-top:10px"><div class="col-md-6"><label class="label-rosa">REF</label><input name="ref" class="input-rosa" placeholder="10028"></div><div class="col-md-6"><label class="label-rosa">CÓDIGO DE BARRAS</label><input name="codigo_barras" class="input-rosa" placeholder="750123456789"></div></div>
<div style="margin-top:20px"><label class="label-rosa">FOTO DEL PRODUCTO (VISIBLE PARA TODOS: CAJERO, MESERO, COCINA)</label><input name="imagen" type="file" class="form-control" accept="image/*" style="background:#111!important;color:white!important;border:2px solid #ff4d8a!important"></div>
</div>
<div class="card-negra"><h5 style="color:#ff4d8a">📦 INVENTARIO</h5>
<div class="row" style="margin-top:10px"><div class="col-md-4"><label class="label-rosa">EN STOCK</label><input name="en_stock" type="number" class="input-rosa" placeholder="0"></div><div class="col-md-4"><label class="label-rosa">INVENTARIO BAJO</label><input name="inventario_bajo" type="number" class="input-rosa" placeholder="5"></div><div class="col-md-4"><label class="label-rosa">PROVEEDOR</label><input name="proveedor" class="input-rosa" placeholder="Proveedor"></div></div>
<button class="btn-rosa-neon" style="margin-top:25px">💾 GUARDAR ARTÍCULO NEGRO/ROSADO</button>
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

@app.route('/productos/eliminar/<int:id>')
def eliminar_producto(id):
    p=Producto.query.get(id)
    if p: db.session.delete(p); db.session.commit()
    return redirect('/productos')

@app.route('/dueno')
def dueno_view():
    if not session.get('is_admin'): return redirect('/dashboard')
    return render_template_string(STYLE_BASE+nav()+"""
<div class="container mt-3">
<div class="card" style="border-color:#ff4d8a">
<h4 style="color:#ff4d8a">💰 Dueño - Ventas vs Gastos (NEGRO Y ROSADO)</h4>
<div style="display:flex;gap:10px;margin-top:15px;align-items:center;flex-wrap:wrap">
<label style="color:#ff4d8a">Ver por:</label>
<select id="periodo" class="form-control" style="width:160px;background:#111!important;color:white!important;border:2px solid #ff4d8a!important" onchange="cargarGrafica()">
<option value="dia">Día (últimos 7 días)</option>
<option value="mes" selected>Mes (últimos 12 meses)</option>
<option value="ano">Año</option>
</select>
<button onclick="cargarGrafica()" style="background:#ff4d8a;color:white;border:none;padding:6px 14px;border-radius:8px;font-weight:bold">Actualizar</button>
</div>
<div style="background:#111;border:2px solid #ff4d8a;border-radius:12px;padding:15px;margin-top:15px">
<canvas id="graficaVentasGastos" height="100"></canvas>
</div>
<div class="row mt-3">
<div class="col-md-4"><div class="card" style="border-color:#25D366"><h6 style="color:#25D366">Ventas Totales</h6><h3 id="totalVentas" style="color:#25D366">$0</h3></div></div>
<div class="col-md-4"><div class="card" style="border-color:#ff4d8a"><h6 style="color:#ff4d8a">Gastos Totales</h6><h3 id="totalGastos" style="color:#ff4d8a">$0</h3></div></div>
<div class="col-md-4"><div class="card" style="border-color:#ff4d8a;background:#1a0a10"><h6 style="color:#ff4d8a">Ganancia</h6><h3 id="totalGanancia" style="color:#ff4d8a">$0</h3></div></div>
</div>
<div class="card mt-3" style="border-color:#ff4d8a">
<h6 style="color:#ff4d8a">Agregar gasto</h6>
<form id="formGasto" class="d-flex gap-2 mt-2 flex-wrap">
<input id="concepto" class="form-control" placeholder="Concepto" required style="background:#000!important;color:white!important;border:2px solid #ff4d8a!important">
<input id="monto" type="number" step="0.01" class="form-control" placeholder="Monto" required style="background:#000!important;color:white!important;border:2px solid #ff4d8a!important">
<button style="background:#ff4d8a;color:white;border:none;padding:6px 16px;border-radius:8px;font-weight:bold">Agregar gasto</button>
</form>
</div>
</div>
</div>
<script>
let chart;
function cargarGrafica(){
  let periodo=document.getElementById('periodo').value;
  fetch('/api/ventas_gastos?periodo='+periodo).then(r=>r.json()).then(data=>{
    document.getElementById('totalVentas').innerText='$'+data.total_ventas.toFixed(2);
    document.getElementById('totalGastos').innerText='$'+data.total_gastos.toFixed(2);
    document.getElementById('totalGanancia').innerText='$'+(data.total_ventas-data.total_gastos).toFixed(2);
    let ctx=document.getElementById('graficaVentasGastos').getContext('2d');
    if(chart) chart.destroy();
    chart=new Chart(ctx,{
      type:'line',
      data:{
        labels:data.labels,
        datasets:[
          {label:'Ventas',data:data.ventas,borderColor:'#ff4d8a',backgroundColor:'rgba(255,77,138,0.2)',tension:0.4,fill:true},
          {label:'Gastos',data:data.gastos,borderColor:'#ff1a6a',backgroundColor:'rgba(255,26,106,0.2)',tension:0.4,fill:true}
        ]
      },
      options:{responsive:true,plugins:{legend:{labels:{color:'white'}}},scales:{x:{ticks:{color:'white'},grid:{color:'#333'}},y:{ticks:{color:'white'},grid:{color:'#333'},beginAtZero:true}}}
    });
  });
}
document.getElementById('formGasto').addEventListener('submit',function(e){
  e.preventDefault();
  fetch('/api/gasto',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({concepto:document.getElementById('concepto').value,monto:document.getElementById('monto').value})}).then(()=>{document.getElementById('concepto').value='';document.getElementById('monto').value='';cargarGrafica();});
});
cargarGrafica();
</script>
""")

@app.route('/api/ventas_gastos')
def api_ventas_gastos():
    periodo=request.args.get('periodo','mes')
    labels=[]; ventas_data=[]; gastos_data=[]
    now=datetime.utcnow()
    if periodo=='dia':
        for i in range(6,-1,-1):
            day=now - timedelta(days=i)
            start=day.replace(hour=0,minute=0,second=0,microsecond=0)
            end=start+timedelta(days=1)
            v=sum([x.total or 0 for x in Venta.query.filter(Venta.fecha>=start,Venta.fecha<end).all()])
            g=sum([x.monto or 0 for x in Gasto.query.filter(Gasto.fecha>=start,Gasto.fecha<end).all()])
            labels.append(start.strftime("%d/%m"))
            ventas_data.append(v); gastos_data.append(g)
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
            start=datetime(y,m,1)
            if m==12: end=datetime(y+1,1,1)
            else: end=datetime(y,m+1,1)
            v=sum([x.total or 0 for x in Venta.query.filter(Venta.fecha>=start,Venta.fecha<end).all()])
            g=sum([x.monto or 0 for x in Gasto.query.filter(Gasto.fecha>=start,Gasto.fecha<end).all()])
            labels.append(start.strftime("%b %Y"))
            ventas_data.append(v); gastos_data.append(g)
    return jsonify({'labels':labels,'ventas':ventas_data,'gastos':gastos_data,'total_ventas':sum(ventas_data),'total_gastos':sum(gastos_data)})

@app.route('/api/gasto', methods=['POST'])
def api_gasto():
    data=request.get_json()
    g=Gasto(concepto=data.get('concepto','Gasto'),monto=float(data.get('monto',0)))
    db.session.add(g); db.session.commit()
    return jsonify({'ok':True})

@app.route('/admin/config', methods=['GET','POST'])
def admin_config():
    if not session.get('is_admin'): return redirect('/dashboard')
    cfg=get_config()
    if request.method=='POST':
        if 'logo' in request.files:
            new_logo=save_upload(request.files['logo'])
            if new_logo: cfg.logo_path=new_logo
        cfg.mod_pos_mesero='mod_pos_mesero' in request.form
        db.session.commit(); return redirect('/admin/config')
    return render_template_string(STYLE_BASE+nav()+"""
<div class="container mt-4" style="max-width:600px"><div class="card" style="border-color:#ff4d8a"><h4 style="color:#ff4d8a">⚙️ Config + Logo + POS mesero</h4><div class="text-center"><img src="/static/{{cfg.logo_path}}" style="width:100px;height:100px;border-radius:50%;background:white;padding:5px;object-fit:cover;border:3px solid #ff4d8a"></div>
<form method="POST" enctype="multipart/form-data" class="mt-3"><label style="color:#ff4d8a">Cambiar logo (negro/rosado)</label><input name="logo" type="file" class="form-control mb-2" accept="image/*" style="background:#000!important;border:2px solid #ff4d8a!important"><div class="form-check mt-2"><input type="checkbox" name="mod_pos_mesero" {{'checked' if cfg.mod_pos_mesero}} style="accent-color:#ff4d8a"><label style="color:white"> POS para mesero habilitado</label></div><button class="btn-rosa w-100 mt-3">Guardar</button></form></div></div>""", cfg=cfg)

@app.route('/ticket/<int:id>')
def ticket(id):
    v=Venta.query.get(id)
    if not v: return redirect('/dashboard')
    cfg=get_config()
    return render_template_string(STYLE_BASE+f'<div class="container mt-5" style="max-width:350px"><div class="card" style="background:white;color:black;border:3px solid #ff4d8a"><div class="text-center"><img src="/static/{cfg.logo_path}" style="width:80px;height:80px;border-radius:50%;background:white;padding:3px;object-fit:cover"><h5>Ticket #{v.id}</h5></div><hr><p><b>{v.producto_nombre}</b><br>Cant: {v.cantidad}<br>Total: ${v.total}<br>Pago: {v.metodo_pago}<br>Vendedor: {v.vendedor}</p><button onclick="window.print()" class="btn-rosa w-100">🖨️ Imprimir</button><a href="/dashboard" class="btn btn-dark w-100 mt-2">Volver POS</a></div></div>')

@app.route('/ventas')
def ventas():
    if 'user' not in session: return redirect('/')
    vs=Venta.query.order_by(Venta.id.desc()).limit(100).all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card" style="border-color:#ff4d8a"><h5 style="color:#ff4d8a">🧾 Ventas (100 últimas)</h5><table class="table table-dark table-sm"><tr><th>Fecha</th><th>Producto</th><th>Total</th><th>Pago</th><th>Vendedor</th></tr>{% for v in vs %}<tr><td>{{v.fecha.strftime('%d/%m %H:%M')}}</td><td>{{v.producto_nombre}} x{{v.cantidad}}</td><td>${{v.total}}</td><td><span style="background:{% if v.metodo_pago=='efectivo' %}#25D366{% elif v.metodo_pago=='tarjeta' %}#3f51b5{% else %}#0097a7{% endif %};padding:2px 6px;border-radius:4px;font-size:10px">{{v.metodo_pago}}</span></td><td>{{v.vendedor}}</td></tr>{% endfor %}</table></div></div>""", vs=vs)

@app.route('/reporte')
def reporte():
    vs=Venta.query.all(); total=sum([v.total for v in vs]) if vs else 0
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card" style="border-color:#ff4d8a"><h4 style="color:#ff4d8a">📊 Reporte Total: ${{total}} - {{vs|length}} ventas</h4><p style="color:#888">Ve el detalle en Dueño + Gráfica</p></div></div>""", total=total, vs=vs)

@app.route('/admin/usuarios', methods=['GET','POST'])
def admin_usuarios():
    if not session.get('is_admin'): return redirect('/dashboard')
    if request.method=='POST':
        if not User.query.filter_by(username=request.form['username']).first():
            es_admin='is_admin' in request.form; rol=request.form.get('rol','cajero')
            if es_admin: rol='admin'
            db.session.add(User(username=request.form['username'],password=generate_password_hash(request.form['password']),is_admin=es_admin,rol=rol)); db.session.commit()
        return redirect('/admin/usuarios')
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card" style="border-color:#ff4d8a"><h5 style="color:#ff4d8a">👥 Usuarios</h5><form method="POST" class="row g-2"><div class="col-md-3"><input name="username" class="form-control" placeholder="Usuario" required style="background:#000!important;border:2px solid #ff4d8a!important"></div><div class="col-md-3"><input name="password" class="form-control" placeholder="Contraseña" required style="background:#000!important;border:2px solid #ff4d8a!important"></div><div class="col-md-2"><select name="rol" class="form-control" style="background:#000!important;border:2px solid #ff4d8a!important"><option value="cajero">Cajero</option><option value="mesero">Mesero</option><option value="cocina">Cocina</option></select></div><div class="col-md-2"><label><input type="checkbox" name="is_admin" style="accent-color:#ff4d8a"> Admin</label></div><div class="col-md-2"><button class="btn-rosa w-100">Crear</button></div></form><table class="table table-dark mt-3"><tr><th>Usuario</th><th>Rol</th></tr>{% for u in usuarios %}<tr><td>{{u.username}}</td><td>{% if u.is_admin %}ADMIN{% else %}{{u.rol}}{% endif %}</td></tr>{% endfor %}</table></div></div>""", usuarios=User.query.all())

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))