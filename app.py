from flask import Flask, request, redirect, session, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import func
import os

app = Flask(__name__)
app.secret_key = 'ruve-final-categorias-grafica-pos-anterior'

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
    color=db.Column(db.String(20), default="#4caf50")
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
    costo_total=db.Column(db.Float, default=0)
    metodo_pago=db.Column(db.String(20), default="efectivo")
class Gasto(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    concepto=db.Column(db.String(100))
    monto=db.Column(db.Float)
    categoria=db.Column(db.String(50), default="general")
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
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

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin',password=generate_password_hash('admin123'),is_admin=True,rol='admin'))
    if Categoria.query.count()==0:
        for cat in ["Sin categoría","Lechón","Tortas","Órdenes","Bebidas","Extras"]:
            db.session.add(Categoria(nombre=cat))
    if Producto.query.count()==0:
        db.session.add(Producto(nombre='Lechón por Kilo',precio=350,stock=50,categoria='Lechón'))
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
.btn-cash{background:#25D366;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:32%}
.btn-pay{background:#3f51b5;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:32%}
.btn-trans{background:#0097a7;color:white;font-weight:bold;padding:12px;border:none;border-radius:8px;width:32%}
.dropdown{position:relative;display:inline-block}
.dropbtn{background:#111;color:#ff4d8a;border:2px solid #ff4d8a;padding:6px 14px;border-radius:8px;font-weight:bold;cursor:pointer}
.dropdown-content{display:none;position:absolute;right:0;background:#111;border:2px solid #ff4d8a;border-radius:10px;min-width:230px;z-index:9999}
.dropdown-content a{display:block;padding:12px 16px;color:white;text-decoration:none;font-size:13px;border-bottom:1px solid #222}
.dropdown-content a:hover{background:#222;color:#ff4d8a}
.dropdown-content.show{display:block}
.header-verde{background:#4caf50;color:white;padding:12px 20px;display:flex;align-items:center;font-weight:bold;font-size:18px}
.card-blanca{background:white;color:#333;border-radius:4px;padding:20px;margin:15px;box-shadow:0 1px 3px rgba(0,0,0,0.2)}
.input-line{border:none!important;border-bottom:1px solid #ccc!important;background:white!important;color:#333!important;border-radius:0!important;padding:8px 0!important;width:100%}
.label-small{font-size:11px;color:#888;margin-top:15px;display:block}
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
            <a href="/productos/nuevo">➕ Crear artículo</a>
            <a href="/categorias">🏷️ Categorías</a>
            <a href="/ventas">🧾 Ventas</a>
            <a href="/reporte">📊 Reporte</a>
            <a href="/dueno" style="color:#ff4d8a">💰 Dueño + Gráfica</a>
            <a href="/admin/config">⚙️ Config + Logo</a>
            <a href="/admin/usuarios">👥 Usuarios</a>
          </div>
        </div>
        <script>
        function toggleDropdown(){{ document.getElementById("adminDropdown").classList.toggle("show"); }}
        window.onclick = function(e){{ if (!e.target.matches('.dropbtn')) {{ var d=document.getElementById("adminDropdown"); if(d && d.classList.contains('show')) d.classList.remove('show'); }} }}
        </script>
        '''
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
    for p in productos: p.img_url=get_producto_imagen(p)
    carrito=session.get('carrito',[]); total=sum([x['precio']*x['cant'] for x in carrito])
    mesas_ocupadas=[m for m in Mesa.query.filter_by(estado='ocupada').all() if not m.unida_a_id]
    return render_template_string(STYLE_BASE+nav()+"""
<div class="pos-container">
    <div class="pos-left">
        <div class="ticket-header"><small style="color:#aaa">Mostrador - {{fecha}}</small></div>
        <div class="ticket-body">
            {% for item in carrito %}<div style="display:flex;justify-content:space-between;border-bottom:1px dashed #ccc;padding:5px;font-size:12px"><span>{{item.nombre}} x{{item.cant}}</span><span>${{item.precio*item.cant}}</span></div>{% endfor %}
            {% if mesas_ocupadas %}<hr><b style="font-size:11px;color:#856404">Mesas por cobrar:</b>{% for m in mesas_ocupadas %}<div style="display:flex;justify-content:space-between"><span>{{m.nombre}} ${{m.total}}</span><a href="/mesa/{{m.id}}/cobrar" style="background:#25D366;color:white;padding:2px 6px;border-radius:4px">Cobrar</a></div>{% endfor %}{% endif %}
        </div>
        <div class="ticket-footer">
            <div style="display:flex;justify-content:space-between;color:white;font-weight:bold;font-size:18px"><span>Total</span><span>${{total}}</span></div>
            <div style="display:flex;gap:6px;margin-top:10px">
                <button onclick="pagar('efectivo')" class="btn-cash">💵 Efectivo</button>
                <button onclick="pagar('tarjeta')" class="btn-pay">💳 Tarjeta</button>
                <button onclick="pagar('transferencia')" class="btn-trans">🏦 Transfer</button>
            </div>
            <a href="/pos/clear" style="display:block;text-align:center;background:#555;color:white;padding:8px;border-radius:8px;margin-top:8px">🗑️ Limpiar</a>
        </div>
    </div>
    <div class="pos-center">
        <button class="cat-btn active" onclick="filtrar('todos')" id="btn-todos">Todos</button>
        {% for cat in categorias %}<button class="cat-btn" onclick="filtrar('{{cat.nombre}}')" id="btn-{{cat.nombre}}">{{cat.nombre}}</button>{% endfor %}
    </div>
    <div class="pos-right">
        <div class="prod-grid">
            {% for p in productos %}
            <div class="prod-card" data-cat="{{p.categoria}}" onclick="location='/pos/add/{{p.id}}'">
                <img src="{{p.img_url}}"><h6>{{p.nombre}}</h6><small>${{p.precio}}</small><br><small style="color:#888">{{p.categoria}}</small>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
<script>
function filtrar(cat){document.querySelectorAll('.cat-btn').forEach(b=>b.classList.remove('active'));document.getElementById('btn-'+cat)?.classList.add('active');document.querySelectorAll('.prod-card').forEach(c=>{if(cat=='todos'||c.dataset.cat==cat)c.style.display='block';else c.style.display='none';})}
function pagar(tipo){fetch('/pos/pagar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tipo:tipo})}).then(r=>r.json()).then(d=>{if(d.ok)location='/ticket/'+d.ticket_id})}
</script>
""", productos=productos, carrito=carrito, total=total, mesas_ocupadas=mesas_ocupadas, categorias=Categoria.query.all(), fecha=datetime.now().strftime("%d/%m/%Y"))

@app.route('/pos/add/<int:id>')
def pos_add(id):
    prod=Producto.query.get(id); carrito=session.get('carrito',[]);
    for it in carrito:
        if it['id']==prod.id: it['cant']+=1; session['carrito']=carrito; return redirect('/dashboard')
    carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':prod.precio,'cant':1}); session['carrito']=carrito; return redirect('/dashboard')
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
    carrito=session.get(f'mesa_carrito_{id}',[]); comandas=[c for c in mesa.comandas if c.estado!='entregado']
    return render_template_string(STYLE_BASE+nav()+"""
<div style="display:flex;height:calc(100vh - 60px);gap:10px;padding:10px">
<div style="width:45%;background:#111;border:2px solid #00e5ff;border-radius:12px;padding:10px;overflow:auto">
<h6 style="color:#00e5ff">{{mesa.nombre}} - ${{mesa.total or 0}}</h6>
{% for c in comandas %}<div style="background:white;color:black;padding:6px;border-radius:6px;margin-bottom:5px;font-size:12px"><b>{{c.cantidad}}x {{c.producto_nombre}}</b> {% if c.comentario %}<span style="background:#c62828;color:white;padding:2px 4px;border-radius:4px">💬 {{c.comentario}}</span>{% endif %}</div>{% endfor %}
<hr><b style="color:#ffcc00;font-size:12px">Nuevo - comentario ANTES de cocina</b>
{% for it in carrito %}<div style="background:#fffde7;color:black;padding:5px;border-radius:4px;margin-top:5px;font-size:12px">{{it.nombre}} x{{it.cant}}<form action="/mesa/{{mesa.id}}/carrito/coment/{{loop.index0}}" method="POST" style="display:flex;gap:3px"><input name="comentario" value="{{it.comentario}}" class="form-control" style="font-size:11px" placeholder="💬 Comentario"><button>💾</button></form></div>{% endfor %}
<div style="margin-top:10px"><a href="/mesa/{{mesa.id}}/enviar" style="background:#00e5ff;color:black;padding:8px;display:block;text-align:center;border-radius:6px;margin-top:5px">MANDAR A COCINA</a><a href="/mesa/{{mesa.id}}/cobrar" style="background:#25D366;color:white;padding:8px;display:block;text-align:center;border-radius:6px;margin-top:5px">💰 COBRAR</a></div>
</div>
<div style="width:55%;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;overflow:auto">
{% for p in productos %}<div style="background:white;color:#333;border-radius:8px;padding:6px;text-align:center;cursor:pointer" onclick="location='/mesa/{{mesa.id}}/add/{{p.id}}'"><img src="{{p.img_url}}" style="width:60px;height:60px;object-fit:cover;border-radius:6px"><br><small>{{p.nombre}}</small><br><small>${{p.precio}}</small></div>{% endfor %}
</div>
</div>
""", mesa=mesa, productos=productos, carrito=carrito, comandas=comandas)

@app.route('/mesa/<int:mesa_id>/add/<int:prod_id>')
def mesa_add(mesa_id, prod_id):
    prod=Producto.query.get(prod_id); carrito=session.get(f'mesa_carrito_{mesa_id}',[])
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
    grupos_list=[{'mesa':Mesa.query.get(mid),'comandas':lista} for mid,lista in grupos.items() if Mesa.query.get(mid)]
    return render_template_string(STYLE_BASE+nav()+"""<div class="container-fluid mt-3"><h3 style="color:#ffcc00">🔥 Cocina - {{grupos_list|length}} mesas</h3><div class="row g-3 mt-2">{% for g in grupos_list %}<div class="col-md-4"><div class="card" style="border-color:#ff4d3a;background:#1a1a0a"><h5 style="color:#00e5ff">🪑 {{g.mesa.nombre}}</h5>{% for c in g.comandas %}<div style="background:white;color:black;padding:6px;border-radius:6px;margin-bottom:5px"><b>{{c.cantidad}}x {{c.producto_nombre}}</b><br>{% if c.comentario %}<span style="background:#c62828;color:white;padding:2px 6px;border-radius:4px;font-size:11px">💬 {{c.comentario}}</span>{% endif %}</div>{% endfor %}<a href="/cocina/mesa_listo/{{g.mesa.id}}" class="btn-rosa w-100 mt-2" style="background:#25D366">✅ MESA LISTA</a></div></div>{% endfor %}</div></div><script>setTimeout(()=>location.reload(),15000)</script>""", grupos_list=grupos_list)

@app.route('/cocina/mesa_listo/<int:mesa_id>')
def cocina_mesa_listo(mesa_id):
    mesa=Mesa.query.get(mesa_id)
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
<div class="container mt-4" style="max-width:600px"><div style="background:white;color:#333;border-radius:8px;padding:20px">
<h4 style="color:#4caf50">🏷️ Categorías</h4>
<form method="POST" class="d-flex gap-2 mt-3">
<input name="nombre" class="form-control" placeholder="Nueva categoría ej: Postres" required style="background:white!important;color:#333!important;border:1px solid #ccc!important">
<button style="background:#4caf50;color:white;border:none;padding:8px 16px;border-radius:4px">Crear</button>
</form>
<table class="table mt-3"><tr><th>Nombre</th><th></th></tr>
{% for c in cats %}<tr><td>{{c.nombre}}</td><td><a href="/categorias/eliminar/{{c.id}}" style="color:red" onclick="return confirm('¿Borrar?')">Borrar</a> | <a href="/categorias/editar/{{c.id}}" style="color:#4caf50">Editar</a></td></tr>{% endfor %}
</table>
<a href="/productos/nuevo" style="background:#4caf50;color:white;padding:8px 12px;border-radius:4px;text-decoration:none">← Volver a Crear artículo</a>
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
        c.nombre=request.form.get('nombre','').strip() or c.nombre
        db.session.commit(); return redirect('/categorias')
    return render_template_string(STYLE_BASE+nav()+f'<div class="container mt-4" style="max-width:400px"><div style="background:white;color:#333;padding:20px;border-radius:8px"><h5>Editar categoría</h5><form method="POST"><input name="nombre" class="form-control" value="{c.nombre}" required><button style="background:#4caf50;color:white;border:none;padding:8px 16px;border-radius:4px;margin-top:10px">Guardar</button></form></div></div>')

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
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div style="background:white;color:#333;border-radius:8px;padding:15px"><div style="display:flex;justify-content:space-between"><h4>📦 Productos ({{productos|length}})</h4><a href="/productos/nuevo" style="background:#4caf50;color:white;padding:8px 16px;border-radius:4px;text-decoration:none">+ Crear artículo</a></div><table class="table mt-3"><tr><th>Foto</th><th>Nombre</th><th>Categoría</th><th>Precio</th><th>Stock</th><th></th></tr>{% for p in productos %}<tr><td><img src="{{p.img_url}}" style="width:45px;height:45px;object-fit:cover;border-radius:6px"></td><td>{{p.nombre}}</td><td>{{p.categoria}}</td><td>${{p.precio}}</td><td>{{p.stock}}</td><td><a href="/productos/eliminar/{{p.id}}" style="color:red">Borrar</a></td></tr>{% endfor %}</table></div></div>""", productos=productos)

@app.route('/productos/nuevo', methods=['GET','POST'])
def productos_nuevo():
    if not session.get('is_admin'): return redirect('/dashboard')
    categorias=Categoria.query.all()
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
<div class="row"><div class="col-md-6"><label class="label-small">Nombre *</label><input name="nombre" class="input-line" placeholder="Ej: Agua, botella 0.5L" style="font-size:20px;font-weight:bold" required></div>
<div class="col-md-4"><label class="label-small">Categoría (editable)</label>
<div style="display:flex;gap:5px"><select name="categoria" id="catSelect" class="input-line">
{% for cat in categorias %}<option value="{{cat.nombre}}">{{cat.nombre}}</option>{% endfor %}
</select><button type="button" onclick="nuevaCategoria()" style="background:#4caf50;color:white;border:none;padding:5px 8px;border-radius:4px;font-size:11px">+ Nueva</button></div>
</div>
<div class="col-md-2"><a href="/categorias" style="font-size:11px;color:#4caf50">Editar categorías</a></div>
</div>
<label class="label-small">Descripción</label><textarea name="descripcion" class="input-line" rows="2" placeholder="Descripción opcional"></textarea>
<div style="margin-top:15px"><input type="checkbox" name="disponible" checked> El artículo está disponible para la venta</div>
<div style="margin-top:10px"><label class="label-small">Vendido por</label><label><input type="radio" name="vendido_por" value="Unidad" checked> Unidad</label> <label style="margin-left:15px"><input type="radio" name="vendido_por" value="Peso/Volumen"> Peso/Volumen</label></div>
<div class="row" style="margin-top:15px"><div class="col-md-6"><label class="label-small">Precio</label><input name="precio" type="number" step="0.01" class="input-line" placeholder="10,00"></div><div class="col-md-6"><label class="label-small">Coste</label><input name="coste" type="number" step="0.01" class="input-line" placeholder="5,00"></div></div>
<div class="row" style="margin-top:10px"><div class="col-md-6"><label class="label-small">REF</label><input name="ref" class="input-line" placeholder="10028"></div><div class="col-md-6"><label class="label-small">Código de barras</label><input name="codigo_barras" class="input-line"></div></div>
<div style="margin-top:15px"><label class="label-small">Foto (visible para TODOS: cajero, mesero, cocina)</label><input name="imagen" type="file" class="form-control" accept="image/*"></div>
</div>
<div class="card-blanca"><h5>Inventario</h5>
<div class="row" style="margin-top:10px"><div class="col-md-6"><label class="label-small">En stock</label><input name="en_stock" type="number" class="input-line" placeholder="0"></div></div>
<button style="background:#4caf50;color:white;border:none;padding:12px 30px;border-radius:4px;margin-top:20px">💾 Guardar artículo</button>
</div>
</form>
</div>
<script>
function nuevaCategoria(){
  let nombre=prompt("Nombre nueva categoría:");
  if(!nombre) return;
  fetch('/api/categorias/crear',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nombre:nombre})}).then(r=>r.json()).then(d=>{
    if(d.ok){ let sel=document.getElementById('catSelect'); let opt=document.createElement('option'); opt.value=d.nombre; opt.text=d.nombre; opt.selected=true; sel.add(opt); alert("Categoría creada: "+d.nombre); }
    else alert("Ya existe o error");
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
<div class="card" style="border-color:#4caf50">
<h4 style="color:#4caf50">💰 Dueño - Ventas vs Gastos</h4>
<div style="display:flex;gap:10px;margin-top:15px;align-items:center">
<label>Ver por:</label>
<select id="periodo" class="form-control" style="width:150px" onchange="cargarGrafica()">
<option value="dia">Día (últimos 7 días)</option>
<option value="mes" selected>Mes (últimos 12 meses)</option>
<option value="ano">Año</option>
</select>
<button onclick="cargarGrafica()" style="background:#4caf50;color:white;border:none;padding:6px 12px;border-radius:6px">Actualizar</button>
</div>
<div style="background:white;border-radius:8px;padding:15px;margin-top:15px">
<canvas id="graficaVentasGastos" height="100"></canvas>
</div>
<div class="row mt-3">
<div class="col-md-4"><div class="card"><h6>Ventas Totales</h6><h3 id="totalVentas" style="color:#25D366">$0</h3></div></div>
<div class="col-md-4"><div class="card"><h6>Gastos Totales</h6><h3 id="totalGastos" style="color:#ff4d3a">$0</h3></div></div>
<div class="col-md-4"><div class="card" style="border-color:#4caf50"><h6>Ganancia</h6><h3 id="totalGanancia" style="color:#4caf50">$0</h3></div></div>
</div>
<div class="card mt-3">
<h6>Agregar gasto</h6>
<form id="formGasto" class="d-flex gap-2 mt-2">
<input id="concepto" class="form-control" placeholder="Concepto" required>
<input id="monto" type="number" step="0.01" class="form-control" placeholder="Monto" required>
<button style="background:#ff4d3a;color:white;border:none;padding:6px 12px;border-radius:6px">Agregar</button>
</form>
</div>
</div>
</div>
<script>
let chart;
function cargarGrafica(){
  let periodo=document.getElementById('periodo').value;
  fetch('/api/ventas_gastos?periodo='+periodo).then(r=>r.json()).then(data=>{
    document.getElementById('totalVentas').innerText='$'+data.total_ventas;
    document.getElementById('totalGastos').innerText='$'+data.total_gastos;
    document.getElementById('totalGanancia').innerText='$'+(data.total_ventas-data.total_gastos);
    let ctx=document.getElementById('graficaVentasGastos').getContext('2d');
    if(chart) chart.destroy();
    chart=new Chart(ctx,{
      type:'line',
      data:{
        labels:data.labels,
        datasets:[
          {label:'Ventas',data:data.ventas,borderColor:'#25D366',backgroundColor:'rgba(37,211,102,0.2)',tension:0.3,fill:true},
          {label:'Gastos',data:data.gastos,borderColor:'#ff4d3a',backgroundColor:'rgba(255,77,58,0.2)',tension:0.3,fill:true}
        ]
      },
      options:{responsive:true,plugins:{legend:{position:'top'}},scales:{y:{beginAtZero:true}}}
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
    else: # mes
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
<div class="container mt-4" style="max-width:600px"><div class="card"><h4>⚙️ Config + Logo</h4><div class="text-center"><img src="/static/{{cfg.logo_path}}" style="width:100px;height:100px;border-radius:50%;background:white;padding:5px;object-fit:cover"></div>
<form method="POST" enctype="multipart/form-data" class="mt-3"><label>Cambiar logo</label><input name="logo" type="file" class="form-control mb-2" accept="image/*"><label><input type="checkbox" name="mod_pos_mesero" {{'checked' if cfg.mod_pos_mesero}}> POS para mesero habilitado</label><br><button class="btn-rosa w-100 mt-2">Guardar</button></form></div></div>""", cfg=cfg)

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