from flask import Flask, request, redirect, session, render_template_string, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os, urllib.parse, io

app = Flask(__name__)
app.secret_key = 'ruve-crear-articulo-estilo-foto'

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
    articulo_compuesto=db.Column(db.Boolean, default=False)
    seguir_inventario=db.Column(db.Boolean, default=True)
    inventario_bajo=db.Column(db.Integer, default=0)
    stock_optimo=db.Column(db.Integer, default=0)
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
class Config(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    numero_whatsapp=db.Column(db.String(20), default="529831000000")
    mod_mesas=db.Column(db.Boolean, default=True)
    mod_cocina=db.Column(db.Boolean, default=True)
    mod_clientes=db.Column(db.Boolean, default=True)
    mod_reservas=db.Column(db.Boolean, default=True)
    mod_llevar=db.Column(db.Boolean, default=True)
    mod_dueno=db.Column(db.Boolean, default=True)
    mod_pos_mesero=db.Column(db.Boolean, default=False)
    logo_path=db.Column(db.String(200), default="logo.png")
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
    editado=db.Column(db.Boolean, default=False)
    leyenda=db.Column(db.String(200), default="")
    mesa = db.relationship('Mesa', backref='comandas', foreign_keys=[mesa_id])

def get_config():
    c=Config.query.first()
    if not c: c=Config(); db.session.add(c); db.session.commit()
    return c
def allowed_file(f): return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED_EXT
def save_upload(file):
    if file and file.filename and allowed_file(file.filename):
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(file.filename)}"
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        return f"uploads/{filename}"
    return ""
def get_producto_imagen(p):
    if p.imagen: return f"/static/{p.imagen}"
    cfg=get_config()
    if cfg.logo_path: return f"/static/{cfg.logo_path}"
    return "/static/logo.png"

with app.app_context():
    from sqlalchemy import text
    db.create_all()
    cols=[
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS imagen VARCHAR(200) DEFAULT \'\'',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS descripcion TEXT DEFAULT \'\'',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS categoria VARCHAR(50) DEFAULT \'Sin categoria\'',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS disponible BOOLEAN DEFAULT TRUE',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS vendido_por VARCHAR(20) DEFAULT \'Unidad\'',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS ref VARCHAR(50) DEFAULT \'\'',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS codigo_barras VARCHAR(100) DEFAULT \'\'',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS articulo_compuesto BOOLEAN DEFAULT FALSE',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS seguir_inventario BOOLEAN DEFAULT TRUE',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS inventario_bajo INTEGER DEFAULT 0',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS stock_optimo INTEGER DEFAULT 0',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS proveedor VARCHAR(100) DEFAULT \'\'',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS costo_compra FLOAT DEFAULT 0',
        'ALTER TABLE producto ADD COLUMN IF NOT EXISTS costo FLOAT DEFAULT 0',
        'ALTER TABLE config ADD COLUMN IF NOT EXISTS logo_path VARCHAR(200) DEFAULT \'logo.png\'',
        'ALTER TABLE config ADD COLUMN IF NOT EXISTS mod_pos_mesero BOOLEAN DEFAULT FALSE',
        'ALTER TABLE venta ADD COLUMN IF NOT EXISTS metodo_pago VARCHAR(20) DEFAULT \'efectivo\'',
        'ALTER TABLE venta ADD COLUMN IF NOT EXISTS costo_total FLOAT DEFAULT 0',
    ]
    for q in cols:
        try: db.session.execute(text(q)); db.session.commit()
        except: db.session.rollback()

STYLE_BASE = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#000;color:white;font-family:Arial}
.card{background:#111;border:2px solid #ff4d8a;border-radius:15px;padding:20px}
.btn-rosa{background:#ff4d8a;color:white;border:none;padding:10px 18px;border-radius:10px;font-weight:bold}
.navbar{background:#000!important;border-bottom:2px solid #ff4d8a;display:flex;justify-content:space-between}
input,select,textarea{background:#222!important;color:white!important;border:1px solid #ff4d8a!important}
.prod-card img{width:70px;height:70px;object-fit:cover;border-radius:10px;background:white;padding:5px}
.dropdown{position:relative;display:inline-block}
.dropbtn{background:#111;color:#ff4d8a;border:2px solid #ff4d8a;padding:6px 12px;border-radius:8px;font-weight:bold;cursor:pointer}
.dropdown-content{display:none;position:absolute;right:0;background:#111;border:2px solid #ff4d8a;border-radius:10px;min-width:220px;z-index:1000}
.dropdown-content a{display:block;padding:10px 14px;color:white;text-decoration:none;font-size:13px}
.dropdown-content a:hover{background:#222;color:#ff4d8a}
.dropdown:hover.dropdown-content{display:block}
.form-crear{background:#f5f5f5;color:#333;padding:0;border-radius:4px}
.header-verde{background:#4caf50;color:white;padding:12px 20px;display:flex;align-items:center;gap:15px;font-weight:bold;font-size:18px}
.card-blanca{background:white;color:#333;border-radius:4px;padding:20px;margin:15px;box-shadow:0 1px 3px rgba(0,0,0,0.2)}
.input-line{border:none;border-bottom:1px solid #ccc!important;background:white!important;color:#333!important;border-radius:0;padding:8px 0;width:100%}
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
    cfg=get_config()
    rol=session.get('rol','cajero'); is_admin=session.get('is_admin', False); user=session.get('user','')
    logo = cfg.logo_path if cfg.logo_path else "logo.png"
    logo_url = f"/static/{logo}"
    if not is_admin and rol=='cocina':
        return f'<nav class="navbar p-3 no-print"><div class="d-flex align-items-center"><img src="{logo_url}" style="width:40px;height:40px;border-radius:50%;background:white;padding:3px"><h6 class="m-0 ms-2" style="color:#ffcc00">Cocina {user}</h6></div><a href="/logout" style="color:#ffcc00">Salir</a></nav>'
    links=""
    if is_admin or rol in ['cajero','admin']: links+='<a href="/dashboard" class="me-3">POS</a>'
    if rol=='mesero' and cfg.mod_pos_mesero: links+='<a href="/dashboard" class="me-3">POS</a>'
    if is_admin or rol in ['cajero','mesero']: links+='<a href="/mesas" class="me-3" style="color:#00e5ff">🪑 Mesas</a>'
    admin_drop=""
    if is_admin:
        admin_drop=f'<div class="dropdown"><button class="dropbtn">⚙️ Herramientas admin ▾</button><div class="dropdown-content"><a href="/productos">📦 Productos</a><a href="/productos/nuevo">➕ Crear artículo</a><a href="/ventas">🧾 Ventas</a><a href="/reporte">📊 Reporte</a><a href="/dueno" style="color:#ff4d8a">💰 Dueño</a><a href="/admin/config">⚙️ Config + Logo</a><a href="/admin/usuarios">👥 Usuarios</a></div></div>'
    return f'<nav class="navbar p-3 no-print"><div class="d-flex align-items-center"><img src="{logo_url}" style="width:40px;height:40px;border-radius:50%;background:white;padding:3px;object-fit:cover"><h6 class="m-0 ms-2" style="color:#ff4d8a">Ruve {user}</h6></div><div>{links}{admin_drop}<a href="/logout" class="ms-3">Salir</a></div></nav>'

@app.route('/productos/nuevo', methods=['GET','POST'])
def productos_nuevo():
    if not session.get('is_admin'): return redirect('/dashboard')
    cfg=get_config()
    if request.method=='POST':
        imagen_path=""
        if 'imagen' in request.files:
            imagen_path = save_upload(request.files['imagen'])
        p=Producto(
            nombre=request.form.get('nombre','').strip() or 'Sin nombre',
            descripcion=request.form.get('descripcion',''),
            categoria=request.form.get('categoria','Sin categoria'),
            disponible='disponible' in request.form,
            vendido_por=request.form.get('vendido_por','Unidad'),
            precio=float(request.form.get('precio') or 0),
            costo=float(request.form.get('coste') or request.form.get('costo') or 0),
            costo_compra=float(request.form.get('costo_compra') or 0),
            ref=request.form.get('ref',''),
            codigo_barras=request.form.get('codigo_barras',''),
            articulo_compuesto='articulo_compuesto' in request.form,
            seguir_inventario='seguir_inventario' in request.form,
            stock=int(request.form.get('en_stock') or 0),
            inventario_bajo=int(request.form.get('inventario_bajo') or 0),
            stock_optimo=int(request.form.get('stock_optimo') or 0),
            proveedor=request.form.get('proveedor',''),
            imagen=imagen_path
        )
        db.session.add(p); db.session.commit()
        return redirect('/productos')

    return render_template_string(STYLE_BASE+nav()+"""
<div style="background:#eee;min-height:100vh;padding:0">
<div class="header-verde">
<span style="font-size:22px">☰</span> Crear artículo
<div style="margin-left:auto;display:flex;gap:10px">
<a href="/productos" style="background:#388e3c;color:white;padding:6px 12px;border-radius:4px;text-decoration:none;font-size:13px">← Volver</a>
</div>
</div>

<form method="POST" enctype="multipart/form-data">
<div class="card-blanca">
<div class="row">
<div class="col-md-8">
<label class="label-small">Nombre</label>
<input name="nombre" class="input-line" placeholder="Ej: Agua, botella 0.5L" style="font-size:22px;font-weight:bold">
</div>
<div class="col-md-4">
<label class="label-small">Categoría</label>
<select name="categoria" class="input-line">
<option>Sin categoría</option>
<option>Lechón</option>
<option>Tortas</option>
<option>Órdenes</option>
<option>Bebidas</option>
<option>Extras</option>
</select>
</div>
</div>

<label class="label-small">Descripción</label>
<textarea name="descripcion" class="input-line" rows="2" placeholder="Descripción opcional"></textarea>

<div style="margin-top:20px;display:flex;align-items:center;gap:10px">
<input type="checkbox" name="disponible" checked style="width:18px;height:18px">
<label>El artículo está disponible para la venta</label>
</div>

<div style="margin-top:15px">
<label class="label-small">Vendido por</label>
<div style="display:flex;gap:20px;margin-top:5px">
<label><input type="radio" name="vendido_por" value="Unidad" checked> Unidad</label>
<label><input type="radio" name="vendido_por" value="Peso/Volumen"> Peso/Volumen</label>
</div>
</div>

<div class="row" style="margin-top:15px">
<div class="col-md-6">
<label class="label-small">Precio</label>
<input name="precio" type="number" step="0.01" class="input-line" placeholder="€10,00">
<small style="font-size:11px;color:#888">Deje el campo en blanco para indicar el precio durante la venta</small>
</div>
<div class="col-md-6">
<label class="label-small">Coste</label>
<input name="coste" type="number" step="0.01" class="input-line" placeholder="€5,00">
</div>
</div>

<div class="row" style="margin-top:15px">
<div class="col-md-6">
<label class="label-small">REF</label>
<input name="ref" class="input-line" placeholder="10028">
</div>
<div class="col-md-6">
<label class="label-small">Código de barras</label>
<input name="codigo_barras" class="input-line" placeholder="Código de barras">
</div>
</div>

<div style="margin-top:20px">
<label class="label-small">Foto del producto (se verá para TODOS los usuarios: cajero, mesero, cocina)</label>
<input name="imagen" type="file" class="form-control" accept="image/*">
</div>

</div>

<div class="card-blanca">
<h5>Inventario</h5>

<div style="display:flex;justify-content:space-between;align-items:center;margin-top:20px">
<div>
<label>Artículo compuesto</label> <small style="color:#888;border:1px solid #888;border-radius:50%;padding:0 5px">i</small>
</div>
<label class="switch"><input type="checkbox" name="articulo_compuesto"><span class="slider"></span></label>
</div>

<div style="display:flex;justify-content:space-between;align-items:center;margin-top:15px">
<label>Seguir el Inventario</label>
<label class="switch"><input type="checkbox" name="seguir_inventario" checked><span class="slider"></span></label>
</div>

<div class="row" style="margin-top:15px">
<div class="col-md-6">
<label class="label-small">En stock</label>
<input name="en_stock" type="number" class="input-line" placeholder="0">
</div>
<div class="col-md-6">
<label class="label-small">Inventario bajo</label>
<input name="inventario_bajo" type="number" class="input-line" placeholder="">
<small style="font-size:10px;color:#888">Cantidad de articulos minima para recibir notificación</small>
</div>
</div>

<div style="margin-top:15px">
<label class="label-small">Stock óptimo</label>
<input name="stock_optimo" type="number" class="input-line" style="width:50%" placeholder="">
<small style="font-size:10px;color:#888;display:block">Utilice este campo para rellenar la cantidad del artículo en la orden de compra</small>
</div>

<div class="row" style="margin-top:20px">
<div class="col-md-6">
<label class="label-small">Proveedor principal</label>
<input name="proveedor" class="input-line" placeholder="">
</div>
<div class="col-md-6">
<label class="label-small">Costo de compra por defecto</label>
<input name="costo_compra" type="number" step="0.01" class="input-line" placeholder="">
</div>
</div>

<button style="background:#4caf50;color:white;border:none;padding:12px 30px;border-radius:4px;margin-top:25px;font-weight:bold">💾 Guardar artículo</button>
<a href="/productos" style="margin-left:10px;color:#666">Cancelar</a>
</div>
</form>
</div>
""")

@app.route('/productos', methods=['GET'])
def productos_list():
    if not session.get('is_admin'): return redirect('/dashboard')
    productos=Producto.query.all()
    for p in productos: p.img_url=get_producto_imagen(p)
    cfg=get_config()
    return render_template_string(STYLE_BASE+nav()+"""
<div class="container mt-3">
<div style="background:white;color:#333;border-radius:4px;padding:15px">
<div style="display:flex;justify-content:space-between;align-items:center">
<h4 style="margin:0">📦 Productos ({{productos|length}})</h4>
<a href="/productos/nuevo" style="background:#4caf50;color:white;padding:8px 16px;border-radius:4px;text-decoration:none">+ Crear artículo</a>
</div>
<table class="table mt-3">
<tr><th>Foto</th><th>Nombre</th><th>Categoría</th><th>Precio</th><th>Stock</th><th>Disponible</th><th></th></tr>
{% for p in productos %}
<tr>
<td><img src="{{p.img_url}}" style="width:45px;height:45px;object-fit:cover;border-radius:6px;background:#eee"></td>
<td><b>{{p.nombre}}</b><br><small style="color:#888">{{p.descripcion[:30]}}</small></td>
<td>{{p.categoria}}</td>
<td>€{{p.precio}}</td>
<td>{{p.stock}}</td>
<td>{% if p.disponible %}✅{% else %}❌{% endif %}</td>
<td><a href="/productos/editar/{{p.id}}" style="color:#4caf50">Editar</a> | <a href="/productos/eliminar/{{p.id}}" style="color:red" onclick="return confirm('¿Borrar?')">Borrar</a></td>
</tr>
{% endfor %}
</table>
</div>
</div>
""", productos=productos)

# Resto de rutas iguales (POS, Mesas, Cocina, etc) - copia tu archivo actual y solo reemplaza las dos de productos
# Para no hacer muy largo, aquí te dejo las esenciales que faltan:
@app.route('/', methods=['GET','POST'])
def login():
    if request.method=='POST':
        from werkzeug.security import check_password_hash
        u=User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user']=u.username; session['is_admin']=u.is_admin; session['rol']=u.rol or 'cajero'
            if u.rol=='cocina' and not u.is_admin: return redirect('/cocina')
            if u.rol=='mesero' and not u.is_admin: return redirect('/mesas')
            return redirect('/dashboard')
    cfg=get_config()
    return render_template_string(STYLE_BASE+f'<div class="container" style="max-width:400px;margin-top:50px"><div class="card text-center"><img src="/static/{cfg.logo_path}" style="width:150px;height:150px;object-fit:cover;border-radius:50%;background:white;padding:5px"><h3 style="color:#ff4d8a" class="mt-3">Ruve</h3><form method="POST" class="mt-3"><input name="username" class="form-control mb-2" placeholder="Usuario" required><input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required><button class="btn-rosa w-100">Entrar</button></form></div></div>')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    productos=Producto.query.filter_by(disponible=True).all()
    for p in productos: p.img_url=get_producto_imagen(p)
    return render_template_string(STYLE_BASE+nav()+"""
<div class="container-fluid mt-2"><div class="row">
<div class="col-md-8">
<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px">
{% for p in productos %}
<div style="background:white;color:#333;border-radius:8px;padding:10px;text-align:center;cursor:pointer" onclick="location='/pos/add/{{p.id}}'">
<img src="{{p.img_url}}" style="width:80px;height:80px;object-fit:cover;border-radius:8px;background:#eee"><br>
<b style="font-size:12px">{{p.nombre}}</b><br><small>€{{p.precio}}</small>
</div>
{% endfor %}
</div>
</div>
<div class="col-md-4"><div class="card"><h6>POS - Todos ven la misma foto que sube el admin</h6></div></div>
</div></div>
""", productos=productos)

@app.route('/pos/add/<int:id>')
def pos_add(id):
    # logica simple para demo, usa tu logica real de carrito
    return redirect('/dashboard')

@app.route('/mesas')
def mesas_view():
    mesas=Mesa.query.all()
    return render_template_string(STYLE_BASE+nav()+"""<div class="container mt-3"><h5>Mesas</h5>{% for m in mesas %}<a href="/mesa/{{m.id}}" class="btn btn-dark m-1">{{m.nombre}}</a>{% endfor %}</div>""", mesas=mesas)

@app.route('/mesa/<int:id>')
def mesa_detalle(id):
    mesa=Mesa.query.get(id)
    productos=Producto.query.filter_by(disponible=True).all()
    for p in productos: p.img_url=get_producto_imagen(p)
    return render_template_string(STYLE_BASE+nav()+"""
<div class="container-fluid mt-2"><div class="row">
<div class="col-md-6"><div class="card"><h5>{{mesa.nombre}}</h5></div></div>
<div class="col-md-6"><div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
{% for p in productos %}<div style="background:white;color:#333;border-radius:8px;padding:8px;text-align:center"><img src="{{p.img_url}}" style="width:60px;height:60px;object-fit:cover;border-radius:6px"><br><small>{{p.nombre}}</small><br><small>€{{p.precio}}</small></div>{% endfor %}
</div></div></div></div>
""", mesa=mesa, productos=productos)

@app.route('/productos/editar/<int:id>', methods=['GET','POST'])
def editar_producto(id):
    p=Producto.query.get(id)
    if request.method=='POST':
        if 'imagen' in request.files:
            new = save_upload(request.files['imagen'])
            if new: p.imagen=new
        p.nombre=request.form.get('nombre',p.nombre)
        p.descripcion=request.form.get('descripcion',p.descripcion)
        p.categoria=request.form.get('categoria',p.categoria)
        p.precio=float(request.form.get('precio') or 0)
        p.stock=int(request.form.get('en_stock') or 0)
        db.session.commit()
        return redirect('/productos')
    return render_template_string(STYLE_BASE+nav()+f'<div class="container mt-3"><div class="card"><h5>Editar {p.nombre}</h5><form method="POST" enctype="multipart/form-data"><input name="nombre" class="form-control mb-2" value="{p.nombre}"><input name="imagen" type="file" class="form-control mb-2"><button class="btn-rosa">Guardar</button></form></div></div>')

@app.route('/productos/eliminar/<int:id>')
def eliminar_producto(id):
    p=Producto.query.get(id)
    if p: db.session.delete(p); db.session.commit()
    return redirect('/productos')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))