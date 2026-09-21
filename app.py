from flask import Flask, request, redirect, session, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'ruve-profesional-final-mxn'

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
    nombre_completo=db.Column(db.String(100), default="")
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
class Venta(db.Model):
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
def get_mesa_principal(mesa):
    if mesa and mesa.unida_a_id:
        principal = Mesa.query.get(mesa.unida_a_id)
        while principal and principal.unida_a_id:
            principal = Mesa.query.get(principal.unida_a_id)
        return principal or mesa
    return mesa
def format_mxn(n): return f"${n:,.2f} MXN"

with app.app_context():
    db.create_all()
    from sqlalchemy import text
    for q in [
        "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS nombre_completo VARCHAR(100) DEFAULT ''",
        "ALTER TABLE user ADD COLUMN IF NOT EXISTS nombre_completo VARCHAR(100) DEFAULT ''",
        "ALTER TABLE venta ADD COLUMN IF NOT EXISTS vendedor_nombre VARCHAR(100) DEFAULT ''",
        "ALTER TABLE comanda ADD COLUMN IF NOT EXISTS mesero_nombre VARCHAR(100) DEFAULT ''",
    ]:
        try: db.session.execute(text(q)); db.session.commit()
        except: db.session.rollback()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin',nombre_completo='Administrador General',password=generate_password_hash('admin123'),is_admin=True,rol='admin'))
    if Categoria.query.count()==0:
        for cat in ["Sin categoría","Lechón","Tortas","Órdenes","Bebidas","Extras"]:
            db.session.add(Categoria(nombre=cat))
    if Mesa.query.count()==0:
        for i in range(1,13): db.session.add(Mesa(nombre=f"Mesa {i}"))
    db.session.commit()

STYLE_BASE = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#0a0a0a;color:#fff;font-family:'Segoe UI',Arial;margin:0}
.card{background:#141414;border:1.5px solid #ff4d8a;border-radius:12px;padding:20px}
.btn-rosa{background:#ff4d8a;color:white;border:none;padding:10px 18px;border-radius:8px;font-weight:600;letter-spacing:0.3px}
.btn-rosa:hover{background:#e63e7a;color:white}
.navbar{background:#000!important;border-bottom:1.5px solid #ff4d8a;padding:12px 20px;display:flex;justify-content:space-between;align-items:center}
.navbar a{color:#fff;text-decoration:none;font-size:13px;font-weight:500;margin-right:18px}
.navbar a:hover{color:#ff4d8a}
.pos-container{display:flex;height:calc(100vh - 58px);gap:10px;padding:10px}
.pos-left{width:36%;background:#111;border:1.5px solid #ff4d8a;border-radius:12px;display:flex;flex-direction:column}
.pos-center{width:13%;display:flex;flex-direction:column;gap:7px}
.pos-right{width:51%;background:#111;border:1.5px solid #222;border-radius:12px;padding:10px;overflow-y:auto}
.cat-btn{background:#1e1e1e;color:#fff;border:1.5px solid #2a2a2a;border-radius:8px;padding:12px;font-size:12px;font-weight:600;cursor:pointer;text-align:center}
.cat-btn.active{background:#ff4d8a;border-color:#ff4d8a;color:white}
.prod-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}
.prod-card{background:#1a1a1a;border:1.5px solid #252525;border-radius:10px;padding:10px;text-align:center;cursor:pointer;transition:0.2s}
.prod-card:hover{border-color:#ff4d8a;transform:translateY(-1px)}
.prod-card img{width:68px;height:68px;object-fit:cover;border-radius:8px;background:#fff;padding:4px}
.prod-card h6{color:#fff;margin:7px 0 2px 0;font-size:12px;font-weight:600}
.ticket-header{background:#0f0f0f;padding:12px;border-bottom:1.5px solid #ff4d8a;display:flex;justify-content:space-between;align-items:center}
.ticket-body{flex:1;overflow-y:auto;padding:10px;background:#fff;color:#111}
.ticket-footer{background:#0f0f0f;padding:12px;border-top:1.5px solid #ff4d8a}
.btn-cash{background:#1f9d5a;color:white;font-weight:700;padding:11px;border:none;border-radius:8px;width:32%;font-size:12px}
.btn-pay{background:#2d4bcc;color:white;font-weight:700;padding:11px;border:none;border-radius:8px;width:32%;font-size:12px}
.btn-trans{background:#0e8a9a;color:white;font-weight:700;padding:11px;border:none;border-radius:8px;width:32%;font-size:12px}
.btn-clear{background:#2a2a2a;color:#ccc;border:1px solid #333;width:100%;padding:9px;border-radius:8px;font-size:12px;font-weight:600;margin-top:8px}
.btn-clear:hover{background:#333;color:white}
.dropdown{position:relative;display:inline-block}
.dropbtn{background:#111;color:#ff4d8a;border:1.5px solid #ff4d8a;padding:7px 14px;border-radius:8px;font-weight:600;cursor:pointer;font-size:12px}
.dropdown-content{display:none;position:absolute;right:0;background:#111;border:1.5px solid #ff4d8a;border-radius:10px;min-width:230px;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,0.9)}
.dropdown-content a{display:block;padding:11px 16px;color:#fff;text-decoration:none;font-size:12.5px;border-bottom:1px solid #1e1e1e}
.dropdown-content a:hover{background:#1a1a1a;color:#ff4d8a}
.dropdown-content.show{display:block}
.input-rosa{border:none!important;border-bottom:1.5px solid #ff4d8a!important;background:#111!important;color:#fff!important;border-radius:0!important;padding:10px 0!important;width:100%;font-size:13px}
.label-rosa{font-size:10px;color:#ff4d8a;font-weight:700;letter-spacing:0.6px;margin-top:16px;display:block;text-transform:uppercase}
.select-rosa{background:#111!important;color:#fff!important;border:1.5px solid #ff4d8a!important;border-radius:8px!important;padding:8px!important;font-size:13px}
.header-rosa{background:#000;border-bottom:2px solid #ff4d8a;color:#ff4d8a;padding:14px 20px;display:flex;align-items:center;font-weight:700;font-size:14px;letter-spacing:0.8px;text-transform:uppercase}
.card-negra{background:#111;border:1.5px solid #ff4d8a;border-radius:12px;padding:20px;margin:12px;box-shadow:0 0 15px rgba(255,77,138,0.15)}
</style>
"""

def nav():
    cfg=get_config(); rol=session.get('rol','cajero'); is_admin=session.get('is_admin', False); nombre=session.get('nombre_completo') or session.get('user','')
    logo_url=f"/static/{cfg.logo_path}"
    if not is_admin and rol=='cocina':
        return f'<nav class="navbar"><div class="d-flex align-items-center"><img src="{logo_url}" style="width:36px;height:36px;border-radius:50%;background:white;padding:2px;object-fit:cover"><span style="margin-left:10px;font-weight:600;font-size:13px">COCINA - {nombre}</span></div><div><a href="/cocina">COCINA</a><a href="/logout">SALIR</a></div></nav>'
    links=""
    if is_admin or rol=='cajero': links+='<a href="/dashboard">POS</a>'
    if rol=='mesero' and cfg.mod_pos_mesero: links+='<a href="/dashboard">POS</a>'
    if is_admin or rol in ['cajero','mesero']: links+='<a href="/mesas">MESAS</a>'
    if is_admin or rol=='cajero': links+='<a href="/cocina">COCINA</a>'
    admin_drop=""
    if is_admin:
        admin_drop=f'''
        <div class="dropdown">
          <button onclick="toggleDropdown()" class="dropbtn">ADMINISTRACION</button>
          <div id="adminDropdown" class="dropdown-content">
            <a href="/productos">PRODUCTOS</a>
            <a href="/productos/nuevo">CREAR ARTICULO</a>
            <a href="/admin/mesas">MESAS</a>
            <a href="/ventas">VENTAS</a>
            <a href="/dueno">REPORTE Y GRAFICA</a>
            <a href="/admin/config">CONFIGURACION</a>
            <a href="/admin/usuarios">USUARIOS</a>
          </div>
        </div>
        <script>
        function toggleDropdown(){{ document.getElementById("adminDropdown").classList.toggle("show"); }}
        window.onclick = function(e){{ if (!e.target.matches('.dropbtn')) {{ var d=document.getElementById("adminDropdown"); if(d && d.classList.contains('show')) d.classList.remove('show'); }} }}
        </script>
        '''
    return f'<nav class="navbar"><div class="d-flex align-items-center"><img src="{logo_url}" style="width:36px;height:36px;border-radius:50%;background:white;padding:2px;object-fit:cover"><span style="margin-left:10px;font-weight:700;font-size:12px;letter-spacing:0.5px;color:#ff4d8a">RUVE - {nombre.upper()}</span></div><div>{links}{admin_drop}<a href="/logout" style="margin-left:10px">SALIR</a><span id="relojPC" style="margin-left:15px;color:#ff4d8a;font-size:11px;font-weight:600"></span></div></nav><script>function actualizarReloj(){{let ahora=new Date();document.getElementById("relojPC").textContent=ahora.toLocaleString("es-MX",{{hour12:false}})}};setInterval(actualizarReloj,1000);actualizarReloj();</script>'

@app.route('/', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user']=u.username; session['nombre_completo']=u.nombre_completo or u.username; session['is_admin']=u.is_admin; session['rol']=u.rol; session['carrito']=[]
            if u.rol=='cocina' and not u.is_admin: return redirect('/cocina')
            if u.rol=='mesero' and not u.is_admin: return redirect('/mesas')
            return redirect('/dashboard')
    cfg=get_config()
    return render_template_string(STYLE_BASE+f'<div class="container" style="max-width:380px;margin-top:60px"><div class="card text-center"><img src="/static/{cfg.logo_path}" style="width:90px;height:90px;object-fit:cover;border-radius:50%;background:white;padding:4px;border:2px solid #ff4d8a"><h5 class="mt-3" style="color:#ff4d8a;font-weight:700;letter-spacing:1px">RUVE SISTEMA</h5><p style="font-size:11px;color:#888">ACCESO PROFESIONAL</p><form method="POST" class="mt-3 text-start"><label class="label-rosa">Usuario</label><input name="username" class="form-control mb-2" style="background:#000!important;border:1.5px solid #ff4d8a!important" required><label class="label-rosa">Contraseña</label><input name="password" type="password" class="form-control mb-3" style="background:#000!important;border:1.5px solid #ff4d8a!important" required><button class="btn-rosa w-100">INGRESAR</button></form></div></div>')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    cfg=get_config(); rol=session.get('rol'); is_admin=session.get('is_admin')
    if not is_admin and rol=='mesero' and not cfg.mod_pos_mesero: return redirect('/mesas')
    if not is_admin and rol=='cocina': return redirect('/cocina')
    productos=Producto.query.filter_by(disponible=True).all()
    for p in productos: p.img_url=get_producto_imagen(p)
    carrito=session.get('carrito',[]); total=sum([x['precio']*x['cant'] for x in carrito])
    mesas_ocupadas=[m for m in Mesa.query.filter_by(estado='ocupada').all() if not m.unida_a_id]
    cats=Categoria.query.all()
    return render_template_string(STYLE_BASE+nav()+"""
<div class="pos-container">
    <div class="pos-left">
        <div class="ticket-header"><span style="font-size:11px;font-weight:700;color:#ff4d8a">TICKET - MOSTRADOR</span><span id="fechaPOS" style="font-size:10px;color:#888"></span></div>
        <div class="ticket-body">
            {% for item in carrito %}<div style="display:flex;justify-content:space-between;border-bottom:1px dashed #ccc;padding:6px 0;font-size:12px"><span>{{item.nombre}} x{{item.cant}}</span><span>{{item.total_mxn}}</span></div>{% endfor %}
            {% if not carrito %}<p style="color:#888;text-align:center;margin-top:30px;font-size:12px">SELECCIONA UN PRODUCTO</p>{% endif %}
            {% if mesas_ocupadas %}<hr><div style="background:#fff3cd;color:#111;padding:6px;border-radius:6px;font-size:10px;font-weight:600">MESAS POR COBRAR: {% for m in mesas_ocupadas %}<div style="display:flex;justify-content:space-between;padding:3px 0"><span>{{m.nombre}} - {{m.total_mxn}}</span><a href="/mesa/{{m.id}}/cobrar" style="background:#1f9d5a;color:white;padding:2px 6px;border-radius:4px;font-size:10px">COBRAR</a></div>{% endfor %}</div>{% endif %}
        </div>
        <div class="ticket-footer">
            <div style="display:flex;justify-content:space-between;color:white;font-weight:700;font-size:16px"><span>TOTAL</span><span id="totalMXN">${{total}} MXN</span></div>
            <div style="display:flex;gap:6px;margin-top:10px">
                <button onclick="pagar('efectivo')" class="btn-cash">EFECTIVO</button>
                <button onclick="pagar('tarjeta')" class="btn-pay">TARJETA</button>
                <button onclick="pagar('transferencia')" class="btn-trans">TRANSFER</button>
            </div>
            <form method="POST" action="/pos/clear" style="margin:0"><button type="submit" class="btn-clear">LIMPIAR TICKET</button></form>
        </div>
    </div>
    <div class="pos-center">
        <button class="cat-btn active" onclick="filtrar('todos')" id="btn-todos">TODOS</button>
        {% for cat in cats %}<button class="cat-btn" onclick="filtrar('{{cat.nombre}}')" id="btn-{{cat.nombre}}">{{cat.nombre.upper()}}</button>{% endfor %}
    </div>
    <div class="pos-right">
        <div class="prod-grid">
            {% for p in productos %}
            <div class="prod-card" data-cat="{{p.categoria}}" onclick="location='/pos/add/{{p.id}}'">
                <img src="{{p.img_url}}"><h6>{{p.nombre}}</h6><small style="color:#ff4d8a;font-weight:700">{{p.precio_mxn}}</small><br><small style="color:#666;font-size:9px">{{p.categoria}} | {{p.stock}}</small>
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
function pagar(tipo){fetch('/pos/pagar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tipo:tipo})}).then(r=>r.json()).then(d=>{if(d.ok)location='/ticket/'+d.ticket_id})}
document.getElementById('fechaPOS').textContent=new Date().toLocaleString('es-MX');
</script>
""", productos=[{'id':p.id,'nombre':p.nombre,'categoria':p.categoria,'stock':p.stock,'img_url':p.img_url,'precio_mxn':format_mxn(p.precio)} for p in productos], carrito=[{'nombre':x['nombre'],'cant':x['cant'],'total_mxn':format_mxn(x['precio']*x['cant'])} for x in carrito], total=f"{total:,.2f}", mesas_ocupadas=[{'id':m.id,'nombre':m.nombre,'total_mxn':format_mxn(m.total or 0)} for m in mesas_ocupadas], cats=cats)

@app.route('/pos/add/<int:id>')
def pos_add(id):
    prod=Producto.query.get(id)
    if not prod: return redirect('/dashboard')
    carrito=session.get('carrito',[])
    for it in carrito:
        if it['id']==prod.id: it['cant']+=1; session['carrito']=carrito; session.modified=True; return redirect('/dashboard')
    carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':prod.precio,'cant':1}); session['carrito']=carrito; session.modified=True; return redirect('/dashboard')

@app.route('/pos/clear', methods=['POST'])
def pos_clear():
    session['carrito']=[]; session.modified=True
    return redirect('/dashboard')

@app.route('/pos/pagar', methods=['POST'])
def pos_pagar():
    data=request.get_json(); metodo=data.get('tipo','efectivo'); carrito=session.get('carrito',[]); last=None
    vendedor=session.get('user'); vendedor_nombre=session.get('nombre_completo','')
    for it in carrito:
        prod=Producto.query.get(it['id'])
        if prod and prod.stock>=it['cant']: prod.stock-=it['cant']
        v=Venta(cliente='Mostrador',producto_nombre=it['nombre'],cantidad=it['cant'],total=it['precio']*it['cant'],vendedor=vendedor,vendedor_nombre=vendedor_nombre,metodo_pago=metodo); db.session.add(v); db.session.flush(); last=v.id
    db.session.commit(); session['carrito']=[]; session.modified=True
    return jsonify({'ok':True,'ticket_id':last})

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
<div class="container mt-3"><div class="card"><h6 style="color:#ff4d8a;font-weight:700">ADMINISTRACION DE MESAS</h6>
<form method="POST" class="d-flex gap-2 mt-3"><input name="nombre" class="form-control" placeholder="Nombre Ej: Mesa 13" required style="background:#000!important;border:1.5px solid #ff4d8a!important"><button class="btn-rosa">AGREGAR MESA</button></form>
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-top:20px">
{% for m in mesas %}<div style="background:#111;border:1.5px solid {% if m.estado=='ocupada' %}#ff4d8a{% else %}#2a2a2a{% endif %};border-radius:10px;padding:12px;text-align:center"><b style="font-size:12px">{{m.nombre}}</b><br><small style="color:#888">{{m.estado}} - {{m.total_mxn}}</small><br><a href="/admin/mesas/eliminar/{{m.id}}" onclick="return confirm('¿Eliminar {{m.nombre}}?')" style="color:#ff4d8a;font-size:11px;font-weight:600;margin-top:6px;display:block">ELIMINAR</a></div>{% endfor %}
</div></div></div>
""", mesas=[{'id':m.id,'nombre':m.nombre,'estado':m.estado.upper(),'total_mxn':format_mxn(m.total or 0)} for m in mesas])

@app.route('/admin/mesas/eliminar/<int:id>')
def admin_mesas_eliminar(id):
    if not session.get('is_admin'): return redirect('/dashboard')
    m=Mesa.query.get(id)
    if m and m.estado=='libre': db.session.delete(m); db.session.commit()
    return redirect('/admin/mesas')

@app.route('/mesas')
def mesas_view():
    mesas=Mesa.query.all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><h6 style="color:#ff4d8a;font-weight:700;margin-bottom:15px">MESAS</h6><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px">{% for m in mesas %}<div style="background:{% if m.estado=='ocupada' %}#2a1018{% else %}#101a14{% endif %};color:white;border:1.5px solid {% if m.estado=='ocupada' %}#ff4d8a{% else %}#1f9d5a{% endif %};padding:14px;border-radius:10px;text-align:center;cursor:pointer" onclick="location='/mesa/{{m.id}}'"><b style="font-size:12px">{{m.nombre}}</b><br><small style="font-size:10px">{{m.estado.upper()}}</small><br><b style="font-size:12px;color:#ff4d8a">{{m.total_mxn}}</b></div>{% endfor %}</div></div>""", mesas=[{'id':m.id,'nombre':m.nombre,'estado':m.estado,'total_mxn':format_mxn(m.total or 0)} for m in mesas])

@app.route('/mesa/<int:id>')
def mesa_detalle(id):
    mesa=Mesa.query.get(id)
    if mesa.unida_a_id: mesa=get_mesa_principal(mesa); return redirect(f'/mesa/{mesa.id}')
    productos=Producto.query.filter_by(disponible=True).all()
    for p in productos: p.img_url=get_producto_imagen(p)
    carrito=session.get(f'mesa_carrito_{id}',[]); total_nuevo=sum([x['precio']*x['cant'] for x in carrito]); comandas=[c for c in mesa.comandas if c.estado!='entregado']
    return render_template_string(STYLE_BASE+nav()+"""
<div style="display:flex;height:calc(100vh - 58px);gap:10px;padding:10px">
<div style="width:42%;background:#111;border:1.5px solid #00e5ff;border-radius:12px;padding:12px;overflow:auto;display:flex;flex-direction:column">
<h6 style="color:#00e5ff;font-weight:700">{{mesa.nombre}} - {{mesa.total_mxn}}</h6>
<div style="flex:1;overflow:auto;margin-top:10px">
{% for c in comandas %}<div style="background:white;color:#111;padding:7px;border-radius:6px;margin-bottom:6px;font-size:11px"><b>{{c.cantidad}}x {{c.producto_nombre}}</b> {% if c.comentario %}<span style="background:#c62828;color:white;padding:2px 5px;border-radius:4px;font-size:10px">💬 {{c.comentario}}</span>{% endif %}</div>{% endfor %}
<hr style="border-color:#333">
<b style="color:#ffcc00;font-size:10px;font-weight:700">NUEVO PEDIDO - COMENTARIO ANTES DE COCINA</b>
{% for it in carrito %}<div style="background:#fffde7;color:#111;padding:6px;border-radius:6px;margin-top:6px;font-size:11px">{{it.nombre}} x{{it.cant}} - {{it.total_mxn}}<form action="/mesa/{{mesa.id}}/carrito/coment/{{loop.index0}}" method="POST" style="display:flex;gap:4px;margin-top:4px"><input name="comentario" value="{{it.comentario}}" class="form-control" style="font-size:10px;padding:4px" placeholder="Comentario"><button style="font-size:10px;background:#000;color:white;border:none;padding:4px 8px;border-radius:4px">OK</button></form></div>{% endfor %}
</div>
<div style="border-top:1.5px solid #ff4d8a;padding-top:10px;margin-top:10px"><div style="display:flex;justify-content:space-between;font-weight:700"><span>TOTAL</span><span style="color:#ff4d8a">{{total_final_mxn}}</span></div><a href="/mesa/{{mesa.id}}/enviar" style="background:#00e5ff;color:#000;padding:10px;display:block;text-align:center;border-radius:8px;margin-top:8px;font-weight:700;font-size:12px;text-decoration:none">ENVIAR A COCINA</a><a href="/mesa/{{mesa.id}}/cobrar" style="background:#1f9d5a;color:white;padding:10px;display:block;text-align:center;border-radius:8px;margin-top:8px;font-weight:700;font-size:12px;text-decoration:none">COBRAR MESA</a></div>
</div>
<div style="width:58%;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;overflow:auto;align-content:start">
{% for p in productos %}<div style="background:#fff;color:#111;border-radius:8px;padding:8px;text-align:center;cursor:pointer;border:1.5px solid #e0e0e0" onclick="location='/mesa/{{mesa.id}}/add/{{p.id}}'"><img src="{{p.img_url}}" style="width:56px;height:56px;object-fit:cover;border-radius:6px;background:#eee"><br><small style="font-weight:700;font-size:11px">{{p.nombre}}</small><br><small style="color:#ff4d8a;font-weight:700">{{p.precio_mxn}}</small></div>{% endfor %}
</div>
</div>
""", mesa={'id':mesa.id,'nombre':mesa.nombre,'total_mxn':format_mxn(mesa.total or 0)}, productos=[{'id':p.id,'nombre':p.nombre,'precio_mxn':format_mxn(p.precio),'img_url':p.img_url} for p in productos], carrito=[{'nombre':x['nombre'],'cant':x['cant'],'comentario':x.get('comentario',''),'total_mxn':format_mxn(x['precio']*x['cant'])} for x in carrito], comandas=comandas, total_final_mxn=format_mxn((mesa.total or 0)+total_nuevo))

@app.route('/mesa/<int:mesa_id>/add/<int:prod_id>')
def mesa_add(mesa_id, prod_id):
    prod=Producto.query.get(prod_id); carrito=session.get(f'mesa_carrito_{mesa_id}',[])
    for it in carrito:
        if it['id']==prod.id and it.get('comentario','')=='': it['cant']+=1; session[f'mesa_carrito_{mesa_id}']=carrito; session.modified=True; return redirect(f'/mesa/{mesa_id}')
    carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':prod.precio,'cant':1,'comentario':''}); session[f'mesa_carrito_{mesa_id}']=carrito; session.modified=True; return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:mesa_id>/carrito/coment/<int:index>', methods=['POST'])
def mesa_carrito_coment(mesa_id,index):
    carrito=session.get(f'mesa_carrito_{mesa_id}',[]);
    if 0 <= index < len(carrito):
        carrito[index]['comentario']=request.form.get('comentario','')[:200]; session[f'mesa_carrito_{mesa_id}']=carrito; session.modified=True
    return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:mesa_id>/enviar')
def mesa_enviar(mesa_id):
    mesa=Mesa.query.get(mesa_id); carrito=session.get(f'mesa_carrito_{mesa_id}',[])
    if not carrito: return redirect(f'/mesa/{mesa_id}')
    mesero=session.get('user'); mesero_nombre=session.get('nombre_completo','')
    for it in carrito:
        com=Comanda(mesa_id=mesa.id,producto_nombre=it['nombre'],cantidad=it['cant'],mesero=mesero,mesero_nombre=mesero_nombre,estado='cocina',comentario=it.get('comentario','')); mesa.total=(mesa.total or 0)+it['precio']*it['cant']; mesa.estado='ocupada'; db.session.add(com)
    db.session.commit(); session[f'mesa_carrito_{mesa_id}']=[]; session.modified=True; return redirect(f'/mesa/{mesa_id}')
@app.route('/mesa/<int:id>/cobrar')
def mesa_cobrar_view(id):
    mesa=Mesa.query.get(id); total=mesa.total or 0
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4" style="max-width:480px"><div class="card" style="border-color:#1f9d5a"><h6 style="color:#1f9d5a;font-weight:700">COBRAR {{mesa.nombre}} - {{total_mxn}}</h6><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:15px"><a href="/mesa/{{mesa.id}}/cobrar_final/efectivo" style="background:#1f9d5a;color:white;padding:18px;text-align:center;border-radius:10px;font-weight:700;text-decoration:none;font-size:12px">EFECTIVO</a><a href="/mesa/{{mesa.id}}/cobrar_final/tarjeta" style="background:#2d4bcc;color:white;padding:18px;text-align:center;border-radius:10px;font-weight:700;text-decoration:none;font-size:12px">TARJETA</a><a href="/mesa/{{mesa.id}}/cobrar_final/transferencia" style="background:#0e8a9a;color:white;padding:18px;text-align:center;border-radius:10px;font-weight:700;text-decoration:none;font-size:12px">TRANSFER</a></div></div></div>""", mesa=mesa, total_mxn=format_mxn(total))
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
    comandas=Comanda.query.filter_by(estado='cocina').order_by(Comanda.fecha.asc()).all()
    from collections import defaultdict
    grupos=defaultdict(list)
    for c in comandas:
        principal=get_mesa_principal(c.mesa) if c.mesa else None
        key=principal.id if principal else c.mesa_id
        grupos[key].append(c)
    grupos_list=[{'mesa':Mesa.query.get(mid),'comandas':lista} for mid,lista in grupos.items() if Mesa.query.get(mid)]
    return render_template_string(STYLE_BASE+nav()+"""<div class="container-fluid mt-3"><h6 style="color:#ffcc00;font-weight:700">COCINA - {{grupos_list|length}} MESAS PENDIENTES</h6><div class="row g-3 mt-2">{% for g in grupos_list %}<div class="col-md-4"><div class="card" style="border-color:#ff3d57;background:#1a1212"><h6 style="color:#00e5ff;font-weight:700;font-size:12px">{{g.mesa.nombre}} - {{g.mesa.total_mxn}} - POR {{g.comandas[0].mesero_nombre}}</h6>{% for c in g.comandas %}<div style="background:white;color:#111;padding:7px;border-radius:6px;margin-bottom:6px;font-size:11px"><b>{{c.cantidad}}x {{c.producto_nombre}}</b><br>{% if c.comentario %}<span style="background:#c62828;color:white;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700">💬 {{c.comentario}}</span>{% endif %}</div>{% endfor %}<a href="/cocina/mesa_listo/{{g.mesa.id}}" style="background:#1f9d5a;color:white;padding:8px;text-align:center;border-radius:8px;display:block;font-weight:700;font-size:12px;text-decoration:none">MESA LISTA</a></div></div>{% endfor %}{% if not grupos_list %}<div class="col-12 text-center p-4"><h5 style="color:#1f9d5a;font-weight:700">SIN PEDIDOS</h5></div>{% endif %}</div></div><script>setTimeout(()=>location.reload(),15000)</script>""", grupos_list=[{'mesa':{'id':g['mesa'].id,'nombre':g['mesa'].nombre,'total_mxn':format_mxn(g['mesa'].total or 0)},'comandas':g['comandas']} for g in grupos_list])

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
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card"><div style="display:flex;justify-content:space-between;align-items:center"><h6 style="color:#ff4d8a;font-weight:700">PRODUCTOS ({{productos|length}})</h6><a href="/productos/nuevo" style="background:#ff4d8a;color:white;padding:7px 14px;border-radius:8px;text-decoration:none;font-weight:700;font-size:12px">NUEVO ARTICULO</a></div><table class="table mt-3" style="color:white;font-size:12px"><tr><th style="color:#ff4d8a">FOTO</th><th>NOMBRE</th><th>CATEGORIA</th><th>PRECIO MXN</th><th>STOCK</th><th></th></tr>{% for p in productos %}<tr><td><img src="{{p.img_url}}" style="width:42px;height:42px;object-fit:cover;border-radius:6px;background:white"></td><td><b>{{p.nombre}}</b></td><td>{{p.categoria}}</td><td style="color:#ff4d8a;font-weight:700">{{p.precio_mxn}}</td><td>{{p.stock}}</td><td><a href="/productos/eliminar/{{p.id}}" style="color:#ff4d8a">ELIMINAR</a></td></tr>{% endfor %}</table></div></div>""", productos=[{'id':p.id,'nombre':p.nombre,'categoria':p.categoria,'stock':p.stock,'img_url':p.img_url,'precio_mxn':format_mxn(p.precio)} for p in productos])

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
<div class="header-rosa">CREAR ARTICULO <a href="/productos" style="margin-left:auto;background:#111;color:#ff4d8a;border:1.5px solid #ff4d8a;padding:6px 12px;border-radius:8px;text-decoration:none;font-size:11px">VOLVER</a></div>
<form method="POST" enctype="multipart/form-data">
<div class="card-negra">
<div class="row"><div class="col-md-6"><label class="label-rosa">Nombre del producto *</label><input name="nombre" class="input-rosa" placeholder="Ej: Agua 500ml" style="font-size:16px;font-weight:600" required></div>
<div class="col-md-6"><label class="label-rosa">Categoria</label><div style="display:flex;gap:6px"><select name="categoria" id="catSelect" class="select-rosa" style="flex:1">{% for cat in categorias %}<option value="{{cat.nombre}}">{{cat.nombre}}</option>{% endfor %}</select><button type="button" onclick="nuevaCategoria()" style="background:#ff4d8a;color:white;border:none;padding:6px 12px;border-radius:8px;font-size:11px;font-weight:700">+ NUEVA</button></div></div></div>
<label class="label-rosa">Descripcion</label><textarea name="descripcion" class="input-rosa" rows="2" placeholder="Opcional"></textarea>
<div class="row mt-2"><div class="col-md-4"><label class="label-rosa">Precio MXN</label><input name="precio" type="number" step="0.01" class="input-rosa" placeholder="0.00" required></div><div class="col-md-4"><label class="label-rosa">En stock</label><input name="en_stock" type="number" class="input-rosa" placeholder="0"></div><div class="col-md-4"><label class="label-rosa">Foto (todos los usuarios ven la misma)</label><input name="imagen" type="file" class="form-control" accept="image/*" style="background:#111!important;color:white!important;border:1.5px solid #ff4d8a!important;font-size:12px"></div></div>
<div style="margin-top:15px"><label style="font-size:11px"><input type="checkbox" name="disponible" checked style="accent-color:#ff4d8a"> Disponible para venta</label></div>
<button style="background:#ff4d8a;color:white;border:none;padding:11px 24px;border-radius:8px;font-weight:700;margin-top:20px">GUARDAR ARTICULO</button>
</div>
</form>
</div>
<script>
function nuevaCategoria(){
  let nombre=prompt("Nombre de la nueva categoría:");
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
<div class="container mt-3">
<div class="card"><h6 style="color:#ff4d8a;font-weight:700">REPORTE VENTAS VS GASTOS</h6>
<div style="display:flex;gap:10px;margin-top:12px;align-items:center"><select id="periodo" class="form-control" style="width:170px;background:#000!important;color:white!important;border:1.5px solid #ff4d8a!important;font-size:12px" onchange="cargarGrafica()"><option value="dia">DIA - ULTIMOS 7 DIAS</option><option value="mes" selected>MES - ULTIMOS 12 MESES</option><option value="ano">AÑO</option></select><button onclick="cargarGrafica()" style="background:#ff4d8a;color:white;border:none;padding:7px 14px;border-radius:8px;font-weight:700;font-size:11px">ACTUALIZAR</button></div>
<div style="background:#0a0a0a;border:1.5px solid #ff4d8a;border-radius:10px;padding:14px;margin-top:14px"><canvas id="graficaVentasGastos" height="90"></canvas></div>
<div class="row mt-3 g-2"><div class="col-md-4"><div class="card" style="padding:12px"><small style="color:#888">VENTAS</small><h5 id="totalVentas" style="color:#1f9d5a;margin:0">$0.00 MXN</h5></div></div><div class="col-md-4"><div class="card" style="padding:12px"><small style="color:#888">GASTOS</small><h5 id="totalGastos" style="color:#ff4d8a;margin:0">$0.00 MXN</h5></div></div><div class="col-md-4"><div class="card" style="padding:12px;background:#1a0a10"><small style="color:#888">GANANCIA</small><h5 id="totalGanancia" style="color:#ff4d8a;margin:0">$0.00 MXN</h5></div></div></div>
<div class="card mt-3"><h6 style="font-size:11px;color:#ff4d8a">REGISTRAR GASTO</h6><form id="formGasto" class="d-flex gap-2 mt-2"><input id="concepto" class="form-control" placeholder="Concepto" required style="background:#000!important;border:1.5px solid #ff4d8a!important;font-size:12px"><input id="monto" type="number" step="0.01" class="form-control" placeholder="$ MXN" required style="background:#000!important;border:1.5px solid #ff4d8a!important;font-size:12px"><button style="background:#ff4d8a;color:white;border:none;padding:7px 14px;border-radius:8px;font-weight:700;font-size:11px">AGREGAR</button></form></div>
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
    chart=new Chart(ctx,{type:'line',data:{labels:data.labels,datasets:[{label:'Ventas',data:data.ventas,borderColor:'#1f9d5a',backgroundColor:'rgba(31,157,90,0.15)',tension:0.4,fill:true},{label:'Gastos',data:data.gastos,borderColor:'#ff4d8a',backgroundColor:'rgba(255,77,138,0.15)',tension:0.4,fill:true}]},options:{responsive:true,plugins:{legend:{labels:{color:'white',font:{size:10}}}},scales:{x:{ticks:{color:'white',font:{size:9}},grid:{color:'#222'}},y:{ticks:{color:'white',font:{size:9}},grid:{color:'#222'},beginAtZero:true}}}});
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
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-4" style="max-width:520px"><div class="card"><h6 style="color:#ff4d8a;font-weight:700">CONFIGURACION</h6><div class="text-center"><img src="/static/{{cfg.logo_path}}" style="width:90px;height:90px;border-radius:50%;background:white;padding:3px;border:2px solid #ff4d8a;object-fit:cover"></div><form method="POST" enctype="multipart/form-data" class="mt-3"><label class="label-rosa">Logo</label><input name="logo" type="file" class="form-control mb-2" accept="image/*" style="background:#000!important;border:1.5px solid #ff4d8a!important;font-size:12px"><div class="form-check mt-2"><input type="checkbox" name="mod_pos_mesero" {{'checked' if cfg.mod_pos_mesero}} style="accent-color:#ff4d8a"><label style="font-size:12px"> Habilitar POS para mesero</label></div><button class="btn-rosa w-100 mt-3">GUARDAR</button></form></div></div>""", cfg=cfg)

@app.route('/ticket/<int:id>')
def ticket(id):
    v=Venta.query.get(id)
    if not v: return redirect('/dashboard')
    cfg=get_config()
    return render_template_string(STYLE_BASE+f'''
<div class="container mt-4" style="max-width:360px"><div class="card" style="background:white;color:#111;border:2px solid #ff4d8a"><div class="text-center"><img src="/static/{cfg.logo_path}" style="width:70px;height:70px;border-radius:50%;background:white;padding:3px;object-fit:cover;border:2px solid #ff4d8a"><h6 style="font-weight:700;margin-top:8px">RUVE</h6><small style="font-size:10px">TICKET #{v.id}</small><br><small id="fechaPC" style="font-size:10px;color:#666"></small></div><hr style="margin:10px 0"><div style="font-size:12px"><b>Cliente:</b> {v.cliente}<br><b>Producto:</b> {v.producto_nombre}<br><b>Cantidad:</b> {v.cantidad}<br><b>Total:</b> <span style="color:#ff4d8a;font-weight:700">{format_mxn(v.total)}</span><br><b>Pago:</b> {v.metodo_pago.upper()}<br><b>Atendio:</b> {v.vendedor_nombre or v.vendedor}<br><small style="color:#888">Vendedor usuario: {v.vendedor}</small></div><hr><button onclick="window.print()" class="btn-rosa w-100" style="font-size:12px">IMPRIMIR TICKET</button><a href="/dashboard" class="btn btn-dark w-100 mt-2" style="font-size:12px">VOLVER AL POS</a></div></div>
<script>document.getElementById('fechaPC').textContent=new Date().toLocaleString('es-MX',{{timeZone:'America/Cancun'}})</script>
''')

@app.route('/ventas')
def ventas():
    vs=Venta.query.order_by(Venta.id.desc()).limit(150).all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><div class="card"><h6 style="color:#ff4d8a;font-weight:700">VENTAS - PESOS MEXICANOS</h6><table class="table table-dark table-sm" style="font-size:11px"><tr><th style="color:#ff4d8a">FECHA</th><th>CLIENTE</th><th>PRODUCTO</th><th>TOTAL</th><th>PAGO</th><th>VENDEDOR</th></tr>{% for v in vs %}<tr><td>{{v.fecha.strftime('%d/%m %H:%M')}}</td><td>{{v.cliente}}</td><td>{{v.producto_nombre}} x{{v.cantidad}}</td><td style="color:#ff4d8a;font-weight:700">{{v.total_mxn}}</td><td>{{v.metodo_pago.upper()}}</td><td><span title="{{v.vendedor}}">{{v.vendedor_nombre}}</span></td></tr>{% endfor %}</table></div></div>""", vs=[{'fecha':v.fecha,'cliente':v.cliente,'producto_nombre':v.producto_nombre,'cantidad':v.cantidad,'total_mxn':format_mxn(v.total),'metodo_pago':v.metodo_pago,'vendedor':v.vendedor,'vendedor_nombre':v.vendedor_nombre or v.vendedor} for v in vs])

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
<div class="container mt-3"><div class="card"><h6 style="color:#ff4d8a;font-weight:700">GESTION DE USUARIOS</h6><p style="font-size:10px;color:#888">NOMBRE COMPLETO APARECE SOLO EN TICKET DE COBRO</p>
<form method="POST" class="row g-2 mt-2">
<div class="col-md-3"><label class="label-rosa">Nombre completo *</label><input name="nombre_completo" class="form-control" placeholder="Ej: Juan Pérez López" required style="background:#000!important;border:1.5px solid #ff4d8a!important;font-size:12px"></div>
<div class="col-md-2"><label class="label-rosa">Usuario *</label><input name="username" class="form-control" placeholder="jperez" required style="background:#000!important;border:1.5px solid #ff4d8a!important;font-size:12px"></div>
<div class="col-md-2"><label class="label-rosa">Contraseña *</label><input name="password" type="password" class="form-control" placeholder="****" required style="background:#000!important;border:1.5px solid #ff4d8a!important;font-size:12px"></div>
<div class="col-md-2"><label class="label-rosa">Rol</label><select name="rol" class="form-control" style="background:#000!important;border:1.5px solid #ff4d8a!important;font-size:12px"><option value="cajero">Cajero</option><option value="mesero">Mesero</option><option value="cocina">Cocina</option></select></div>
<div class="col-md-1"><label class="label-rosa">Admin</label><br><input type="checkbox" name="is_admin" style="accent-color:#ff4d8a;width:18px;height:18px"></div>
<div class="col-md-2"><label class="label-rosa"> </label><button class="btn-rosa w-100" style="font-size:11px">CREAR USUARIO</button></div>
</form>
<table class="table table-dark mt-4" style="font-size:11px"><tr><th style="color:#ff4d8a">NOMBRE COMPLETO</th><th>USUARIO</th><th>ROL</th><th></th></tr>
{% for u in usuarios %}<tr><td>{{u.nombre_completo}}</td><td>{{u.username}}</td><td>{% if u.is_admin %}ADMIN{% else %}{{u.rol.upper()}}{% endif %}</td><td><a href="/admin/usuarios/eliminar/{{u.id}}" onclick="return confirm('Eliminar {{u.username}}?')" style="color:#ff4d8a;font-size:10px">ELIMINAR</a></td></tr>{% endfor %}
</table>
</div></div>
""", usuarios=usuarios)

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