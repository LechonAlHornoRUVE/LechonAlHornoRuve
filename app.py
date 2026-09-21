from flask import Flask, request, redirect, session, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'ruve-502-fix-definitivo'

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db_url = os.environ.get('DATABASE_URL', 'sqlite:///lechon.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Cloudinary opcional - si no está, no tumba la app
CLOUDINARY_ENABLED = False
try:
    import cloudinary, cloudinary.uploader
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
        secure=True
    )
    if os.environ.get('CLOUDINARY_CLOUD_NAME'):
        CLOUDINARY_ENABLED = True
except:
    pass

class User(db.Model):
    __tablename__='usuarios'
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True)
    nombre_completo=db.Column(db.String(100), default="")
    password=db.Column(db.String(200))
    is_admin=db.Column(db.Boolean, default=False)
    rol=db.Column(db.String(20), default="cajero")
class Producto(db.Model):
    __tablename__='productos'
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(100))
    precio=db.Column(db.Float, default=0)
    stock=db.Column(db.Integer, default=0)
    imagen=db.Column(db.Text, default="")
    categoria=db.Column(db.String(50), default="Sin categoria")
    disponible=db.Column(db.Boolean, default=True)
class Config(db.Model):
    __tablename__='config'
    id=db.Column(db.Integer, primary_key=True)
    logo_path=db.Column(db.Text, default="logo.png")
    mod_pos_mesero=db.Column(db.Boolean, default=False)
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
    mesero_nombre=db.Column(db.String(100), default="")
    comentario=db.Column(db.String(200), default="")
    mesa=db.relationship('Mesa', backref='comandas')
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

def get_config():
    c=Config.query.first()
    if not c:
        c=Config()
        db.session.add(c)
        db.session.commit()
    return c

def save_upload(file):
    if not file or not file.filename: return ""
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

def get_img(p=None):
    try:
        if p and getattr(p,'imagen',None) and p.imagen.startswith('http'):
            return p.imagen
    except: pass
    cfg=get_config()
    if cfg.logo_path and cfg.logo_path.startswith('http'):
        return cfg.logo_path
    return "/static/"+cfg.logo_path

def mxn(n):
    try: return "${:,.2f} MXN".format(float(n))
    except: return "$0.00 MXN"

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin',nombre_completo='Admin',password=generate_password_hash('admin123'),is_admin=True,rol='admin'))
    if Mesa.query.count()==0:
        for i in range(1,13):
            db.session.add(Mesa(nombre="Mesa "+str(i)))
    db.session.commit()

STYLE = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
:root{--rosa:#ff4d8a}
body{background:#000;color:white;margin:0;font-family:Arial}
.card{background:#111;border:2px solid var(--rosa);border-radius:15px;padding:20px}
.btn-rosa{background:var(--rosa);color:white;border:none;padding:10px 18px;border-radius:10px;font-weight:bold}
.navbar{background:#000!important;border-bottom:2px solid var(--rosa);display:flex;justify-content:space-between;padding:10px 15px}
.prod-card{background:#1a1a1a;border:2px solid #333;border-radius:12px;padding:10px;text-align:center;cursor:pointer}
.prod-card img{width:70px;height:70px;object-fit:cover;border-radius:10px;background:white;padding:5px}
</style>
"""

def nav():
    cfg=get_config()
    logo=get_img(cfg)
    nombre=session.get('nombre_completo') or session.get('user','')
    is_admin=session.get('is_admin', False)
    links='<a href="/dashboard" class="me-3">POS</a><a href="/mesas" class="me-3" style="color:#00e5ff">Mesas</a><a href="/cocina" class="me-3" style="color:#ffcc00">Cocina</a>'
    if is_admin:
        links+='<a href="/productos" class="me-3">Productos</a><a href="/admin/config" class="me-3">Config</a><a href="/ventas" class="me-3">Ventas</a>'
    return '<nav class="navbar"><div><img src="'+logo+'" style="width:40px;height:40px;border-radius:50%;background:white;padding:3px"><span style="color:var(--rosa);margin-left:8px">Ruve '+nombre+'</span></div><div>'+links+'<a href="/logout">Salir</a></div></nav>'

@app.route('/', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user']=u.username
            session['nombre_completo']=u.nombre_completo or u.username
            session['is_admin']=u.is_admin
            session['rol']=u.rol
            session['carrito']=[]
            if u.rol=='mesero' and not u.is_admin: return redirect('/mesas')
            if u.rol=='cocina' and not u.is_admin: return redirect('/cocina')
            return redirect('/dashboard')
    cfg=get_config()
    logo=get_img(cfg)
    return render_template_string(STYLE+nav()+'<div style="min-height:80vh;display:flex;justify-content:center;align-items:center"><div class="card" style="width:360px;text-align:center"><div style="display:flex;justify-content:center;margin-bottom:15px"><img src="'+logo+'" style="width:130px;height:130px;border-radius:50%;background:white;padding:5px;border:3px solid var(--rosa)"></div><h3 style="color:var(--rosa)">Ruve</h3><form method="POST"><input name="username" class="form-control mb-3" placeholder="Usuario" required style="background:white!important;color:#333!important;padding:12px"><input name="password" type="password" class="form-control mb-3" placeholder="Contra" required style="background:white!important;color:#333!important;padding:12px"><button class="btn-rosa w-100" style="padding:12px">Entrar</button></form></div></div>')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    productos=Producto.query.all()
    prod_list=[{'id':p.id,'nombre':p.nombre,'img_url':get_img(p),'precio_mxn':mxn(p.precio or 0)} for p in productos if getattr(p,'disponible',True)]
    carrito=session.get('carrito',[])
    total=sum([float(x.get('precio',0))*int(x.get('cant',0)) for x in carrito])
    mesas_por_cobrar=Mesa.query.filter_by(estado='por_cobrar').all()
    return render_template_string(STYLE+nav()+"""
<div style="display:flex;gap:10px;padding:10px;height:calc(100vh - 60px)">
<div style="width:35%;background:#0f0f0f;border:2px solid var(--rosa);border-radius:15px;padding:10px;display:flex;flex-direction:column">
<div style="flex:1;overflow:auto;background:white;color:black;padding:10px;border-radius:10px">
{% for item in carrito %}<div style="display:flex;justify-content:space-between;font-size:12px;border-bottom:1px dashed #ccc;padding:4px 0"><span>{{item.nombre}} x{{item.cant}}</span><span>{{item.total_mxn}}</span></div>{% endfor %}
{% if mesas_por_cobrar %}
<div style="background:#ffeb3b;color:black;padding:8px;border-radius:8px;margin-top:10px;border:3px solid #ff9800"><b>SOLICITUDES MESERO A CAJA:</b>
{% for m in mesas_por_cobrar %}<div style="display:flex;justify-content:space-between;background:white;padding:6px;border-radius:4px;margin-top:5px"><span><b>{{m.nombre}}</b> {{m.total_mxn}}</span><a href="/mesa/{{m.id}}/cobrar" style="background:#25D366;color:white;padding:4px 8px;border-radius:4px;text-decoration:none">COBRAR</a></div>{% endfor %}</div>
{% endif %}
</div>
<div style="margin-top:10px"><b>TOTAL ${{total}} MXN</b><br><a href="/pos/clear" style="color:#888;font-size:12px">Limpiar</a><br><a href="/pos/pagar/efectivo" style="background:#25D366;color:white;display:block;text-align:center;padding:10px;border-radius:8px;margin-top:5px;text-decoration:none">COBRAR EFECTIVO</a></div>
</div>
<div style="width:65%;background:#0f0f0f;border:2px solid #333;border-radius:15px;padding:10px;overflow:auto;display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
{% for p in productos %}<div class="prod-card" onclick="location='/pos/add/{{p.id}}'"><img src="{{p.img_url}}"><h6 style="color:var(--rosa);margin-top:8px">{{p.nombre}}</h6><small style="color:var(--rosa)">{{p.precio_mxn}}</small></div>{% endfor %}
</div>
</div>
""", productos=prod_list, carrito=[{'nombre':x.get('nombre',''),'cant':x.get('cant',0),'total_mxn':mxn(float(x.get('precio',0))*int(x.get('cant',0)))} for x in carrito], total="{:,.2f}".format(total), mesas_por_cobrar=[{'id':m.id,'nombre':m.nombre,'total_mxn':mxn(m.total or 0)} for m in mesas_por_cobrar])

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

@app.route('/pos/clear')
def pos_clear():
    session['carrito']=[]; session.modified=True; return redirect('/dashboard')

@app.route('/pos/pagar/<metodo>')
def pos_pagar(metodo):
    carrito=session.get('carrito',[])
    if not carrito: return redirect('/dashboard')
    vendedor=session.get('user')
    for it in carrito:
        v=Venta(cliente='Mostrador',producto_nombre=it['nombre'],cantidad=it['cant'],total=float(it['precio'])*int(it['cant']),vendedor=vendedor,metodo_pago=metodo)
        db.session.add(v)
    db.session.commit()
    session['carrito']=[]; session.modified=True
    return redirect('/dashboard')

@app.route('/mesas')
def mesas_view():
    mesas=Mesa.query.all()
    return render_template_string(STYLE+nav()+"""<div class="container mt-3"><h5 style="color:var(--rosa)">Mesas - Amarillo = Por cobrar en caja (solicitud mesero)</h5><div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:10px">{% for m in mesas %}<div style="background:{% if m.estado=='por_cobrar' %}#ffeb3b{% elif m.estado=='ocupada' %}#fde8e8{% else %}#e8f5e9{% endif %};color:black;padding:15px;border-radius:10px;text-align:center;cursor:pointer;border:{% if m.estado=='por_cobrar' %}3px solid #ff9800{% else %}none{% endif %}" onclick="location='/mesa/{{m.id}}'"><b>{{m.nombre}}</b><br>{% if m.estado=='por_cobrar' %}POR COBRAR{% else %}{{m.estado}}{% endif %}<br>{{m.total_mxn}}</div>{% endfor %}</div></div>""", mesas=[{'id':m.id,'nombre':m.nombre,'estado':m.estado,'total_mxn':mxn(m.total or 0)} for m in mesas])

@app.route('/mesa/<int:id>')
def mesa_detalle(id):
    mesa=Mesa.query.get(id)
    if not mesa: return redirect('/mesas')
    productos=Producto.query.all()
    prod_list=[{'id':p.id,'nombre':p.nombre,'precio_mxn':mxn(p.precio or 0),'img_url':get_img(p)} for p in productos if getattr(p,'disponible',True)]
    carrito=session.get('mesa_carrito_'+str(id),[])
    if not isinstance(carrito, list): carrito=[]
    total_nuevo=sum([float(x.get('precio',0))*int(x.get('cant',0)) for x in carrito])
    comandas=[c for c in mesa.comandas if c.estado!='entregado']
    puede_cobrar=session.get('is_admin') or session.get('rol')=='cajero'
    return render_template_string(STYLE+nav()+"""
<div style="display:flex;height:calc(100vh - 60px);gap:10px;padding:10px">
<div style="width:45%;background:#111;border:2px solid #00e5ff;border-radius:12px;padding:10px;overflow:auto;display:flex;flex-direction:column">
<h6 style="color:#00e5ff">{{mesa.nombre}} - {{mesa.total_mxn}} {% if mesa.estado=='por_cobrar' %}<span style="background:#ffeb3b;color:black;padding:2px 6px;border-radius:4px">POR COBRAR</span>{% endif %}</h6>
<div style="flex:1;overflow:auto">
{% for c in comandas %}<div style="background:white;color:black;padding:8px;border-radius:8px;margin-bottom:6px;font-size:12px;display:flex;justify-content:space-between"><div><b>{{c.cantidad}}x {{c.producto_nombre}}</b><br><small>{{c.estado}}</small></div><a href="/mesa/{{mesa.id}}/comanda/eliminar/{{c.id}}" style="background:var(--rosa);color:white;padding:6px 10px;border-radius:6px;text-decoration:none">Quitar</a></div>{% endfor %}
{% for it in carrito %}<div style="background:#fffde7;color:black;padding:5px;border-radius:4px;margin-top:5px;font-size:12px;display:flex;justify-content:space-between"><span>{{it.nombre}} x{{it.cant}}</span><a href="/mesa/{{mesa.id}}/carrito/eliminar/{{loop.index0}}" style="color:var(--rosa)">X</a></div>{% endfor %}
</div>
<div style="border-top:2px solid var(--rosa);padding-top:10px"><b>Total {{total_final_mxn}}</b><br><a href="/mesa/{{mesa.id}}/enviar" style="background:#00e5ff;color:black;padding:8px;display:block;text-align:center;border-radius:6px;margin-top:5px;text-decoration:none">MANDAR A COCINA</a>
{% if puede_cobrar %}<a href="/mesa/{{mesa.id}}/cobrar" style="background:#25D366;color:white;padding:10px;display:block;text-align:center;border-radius:6px;margin-top:5px;text-decoration:none">COBRAR MESA (CAJA)</a>
{% else %}<a href="/mesa/{{mesa.id}}/solicitar_cuenta" style="background:#ffeb3b;color:black;padding:10px;display:block;text-align:center;border-radius:6px;margin-top:5px;font-weight:bold;border:2px solid #ff9800;text-decoration:none">SOLICITAR CUENTA A CAJA</a>{% endif %}
</div></div>
<div style="width:55%;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;overflow:auto">{% for p in productos %}<div style="background:white;color:#333;border-radius:8px;padding:6px;text-align:center;cursor:pointer" onclick="location='/mesa/{{mesa.id}}/add/{{p.id}}'"><img src="{{p.img_url}}" style="width:60px;height:60px;object-fit:cover;border-radius:6px"><br><small>{{p.nombre}}</small><br><small style="color:var(--rosa)">{{p.precio_mxn}}</small></div>{% endfor %}</div>
</div>
""", mesa={'id':mesa.id,'nombre':mesa.nombre,'total_mxn':mxn(mesa.total or 0),'estado':mesa.estado}, productos=prod_list, carrito=[{'nombre':x.get('nombre',''),'cant':x.get('cant',0)} for x in carrito], comandas=comandas, total_final_mxn=mxn((mesa.total or 0)+total_nuevo), puede_cobrar=puede_cobrar)

@app.route('/mesa/<int:mesa_id>/add/<int:prod_id>')
def mesa_add(mesa_id, prod_id):
    prod=Producto.query.get(prod_id)
    key='mesa_carrito_'+str(mesa_id)
    carrito=session.get(key,[])
    if not isinstance(carrito, list): carrito=[]
    carrito.append({'id':prod.id,'nombre':prod.nombre,'precio':float(prod.precio or 0),'cant':1})
    session[key]=carrito; session.modified=True
    return redirect('/mesa/'+str(mesa_id))

@app.route('/mesa/<int:mesa_id>/carrito/eliminar/<int:index>')
def mesa_carrito_eliminar(mesa_id,index):
    key='mesa_carrito_'+str(mesa_id)
    carrito=session.get(key,[])
    if 0 <= index < len(carrito):
        carrito.pop(index); session[key]=carrito; session.modified=True
    return redirect('/mesa/'+str(mesa_id))

@app.route('/mesa/<int:mesa_id>/comanda/eliminar/<int:comanda_id>')
def mesa_comanda_eliminar(mesa_id, comanda_id):
    mesa=Mesa.query.get(mesa_id); com=Comanda.query.get(comanda_id)
    if mesa and com:
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
    for it in carrito:
        com=Comanda(mesa_id=mesa.id,producto_nombre=it['nombre'],cantidad=it['cant'],estado='cocina')
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
    mesa=Mesa.query.get(id)
    if not mesa: return redirect('/mesas')
    # Si es mesero sin permiso, lo mandamos a por_cobrar
    if not session.get('is_admin') and session.get('rol')=='mesero':
        mesa.estado='por_cobrar'; db.session.commit()
        # Pero si es el mismo mesero que quiere cobrar y es admin de prueba, permitimos si es cajero
        if session.get('rol')!='cajero' and not session.get('is_admin'):
            return redirect('/mesas')
    comandas=[c for c in mesa.comandas if c.estado!='entregado']
    return render_template_string(STYLE+nav()+"""
<div class="container mt-3" style="max-width:700px"><div class="card" style="border-color:#ffeb3b"><h4 style="color:#ffeb3b">Cobro {{mesa.nombre}} - {{total_mxn}}</h4>
<div style="background:white;color:black;padding:12px;border-radius:8px;margin-top:10px">
{% for c in comandas %}<div>{{c.cantidad}}x {{c.producto_nombre}}</div>{% endfor %}
<b>TOTAL {{total_mxn}}</b></div>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:15px">
<a href="/mesa/{{mesa.id}}/cobrar_final/efectivo" style="background:#25D366;color:white;padding:18px;text-align:center;border-radius:10px;text-decoration:none">Efectivo</a>
<a href="/mesa/{{mesa.id}}/cobrar_final/tarjeta" style="background:#3f51b5;color:white;padding:18px;text-align:center;border-radius:10px;text-decoration:none">Tarjeta</a>
<a href="/mesa/{{mesa.id}}/cobrar_final/transferencia" style="background:#0097a7;color:white;padding:18px;text-align:center;border-radius:10px;text-decoration:none">Transfer</a>
</div></div></div>
""", mesa={'id':mesa.id,'nombre':mesa.nombre}, total_mxn=mxn(mesa.total or 0), comandas=comandas)

@app.route('/mesa/<int:id>/cobrar_final/<metodo>')
def mesa_cobrar_final(id,metodo):
    mesa=Mesa.query.get(id)
    for c in list(mesa.comandas):
        if c.estado!='entregado':
            prod=Producto.query.filter_by(nombre=c.producto_nombre).first()
            precio=prod.precio if prod else 0
            v=Venta(cliente=mesa.nombre,producto_nombre=c.producto_nombre,cantidad=c.cantidad,total=precio*c.cantidad,vendedor=session.get('user'),metodo_pago=metodo)
            db.session.add(v); c.estado='entregado'
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
    return render_template_string(STYLE+nav()+"""<div class="container-fluid mt-3"><h3 style="color:#ffcc00">Cocina - {{grupos_list|length}} mesas</h3><div class="row g-3">{% for g in grupos_list %}<div class="col-md-4"><div class="card"><h5 style="color:#00e5ff">{{g.mesa.nombre}}</h5>{% for c in g.comandas %}<div style="background:white;color:black;padding:6px;border-radius:6px;margin-bottom:5px"><b>{{c.cantidad}}x {{c.producto_nombre}}</b></div>{% endfor %}<a href="/cocina/mesa_listo/{{g.mesa.id}}" style="background:#25D366;color:white;padding:8px;display:block;text-align:center;border-radius:6px;text-decoration:none">MESA LISTA</a></div></div>{% endfor %}</div></div>""", grupos_list=[{'mesa':{'id':g['mesa'].id,'nombre':g['mesa'].nombre},'comandas':g['comandas']} for g in grupos_list])

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
    lista=[{'id':p.id,'nombre':p.nombre,'img_url':get_img(p),'precio_mxn':mxn(p.precio or 0)} for p in productos]
    return render_template_string(STYLE+nav()+"""<div class="container mt-3"><div style="background:white;color:#333;border-radius:8px;padding:15px"><h4 style="color:black">Productos ({{productos|length}}) {% if cloudinary_enabled %}<small style="background:#25D366;color:white;padding:3px 8px;border-radius:8px">Cloudinary Activo</small>{% endif %}</h4><a href="/productos/nuevo" style="background:var(--rosa);color:white;padding:8px 16px;border-radius:4px;text-decoration:none">+ Crear</a><table class="table mt-3"><tr><th>Foto</th><th>Nombre</th><th>Precio</th><th>Acciones</th></tr>{% for p in productos %}<tr><td><img src="{{p.img_url}}" style="width:45px;height:45px"></td><td>{{p.nombre}}</td><td>{{p.precio_mxn}}</td><td><a href="/productos/editar/{{p.id}}">Editar</a> <a href="/productos/eliminar/{{p.id}}">Borrar</a></td></tr>{% endfor %}</table></div></div>""", productos=lista, cloudinary_enabled=CLOUDINARY_ENABLED)

@app.route('/productos/nuevo', methods=['GET','POST'])
def productos_nuevo():
    if not session.get('is_admin'): return redirect('/dashboard')
    if request.method=='POST':
        img=save_upload(request.files['imagen']) if 'imagen' in request.files else ""
        p=Producto(nombre=request.form.get('nombre','').strip() or 'Sin nombre',precio=float(request.form.get('precio') or 0),imagen=img)
        db.session.add(p); db.session.commit(); return redirect('/productos')
    return render_template_string(STYLE+nav()+"""<div class="container mt-3"><div class="card"><h5>Crear articulo</h5><form method="POST" enctype="multipart/form-data"><input name="nombre" class="form-control mb-2" placeholder="Nombre" required><input name="precio" type="number" step="0.01" class="form-control mb-2" placeholder="Precio" required><input name="imagen" type="file" class="form-control mb-2" accept="image/*"><button class="btn-rosa">Guardar</button></form></div></div>""")

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
        db.session.commit()
        return redirect('/productos')
    return render_template_string(STYLE+nav()+"""
<div class="container mt-3"><div class="card"><h5>Editar """+p.nombre+"""</h5><form method="POST" enctype="multipart/form-data"><input name="nombre" class="form-control mb-2" value=\""""+p.nombre+"""\" required><input name="precio" type="number" step="0.01" class="form-control mb-2" value=\""""+str(p.precio or 0)+"""\"><p>Actual: <img src=\""""+get_img(p)+"""\" style="width:60px;height:60px"></p><input name="imagen" type="file" class="form-control mb-2" accept="image/*"><button class="btn-rosa">Guardar cambios</button></form></div></div>
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
        db.session.commit()
        return redirect('/admin/config')
    logo=get_img(cfg)
    c1="checked" if getattr(cfg,'mod_pos_mesero',False) else ""
    return render_template_string(STYLE+nav()+'<div class="container mt-3"><div class="card"><h5>Config + Logo</h5><img src="'+logo+'" style="width:80px;height:80px;border-radius:50%;background:white;padding:5px"><form method="POST" enctype="multipart/form-data" class="mt-3"><input name="logo" type="file" class="form-control mb-2"><label><input type="checkbox" name="mod_pos_mesero" '+c1+'> POS mesero</label><br><small style="color:#888">Mesero ahora NO puede cobrar directo, solo solicita cuenta a caja. Cajero cobra.</small><br><button class="btn-rosa mt-2">Guardar</button></form></div></div>')

@app.route('/ventas')
def ventas():
    vs=Venta.query.order_by(Venta.id.desc()).limit(100).all()
    return render_template_string(STYLE+nav()+"""<div class="container mt-3"><div class="card"><h5>Ventas</h5><table class="table table-dark table-sm"><tr><th>ID</th><th>Producto</th><th>Total</th></tr>{% for v in vs %}<tr><td>{{v.id}}</td><td>{{v.producto_nombre}} x{{v.cantidad}}</td><td>{{v.total_mxn}}</td></tr>{% endfor %}</table></div></div>""", vs=[{'id':v.id,'producto_nombre':v.producto_nombre,'cantidad':v.cantidad,'total_mxn':mxn(v.total)} for v in vs])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))