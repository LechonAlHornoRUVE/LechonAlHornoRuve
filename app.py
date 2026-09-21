from flask import Flask, request, redirect, session, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'ruve-lechona-2026-final'
db_url = os.environ.get('DATABASE_URL', 'sqlite:///ruve.db')
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELOS FASE 1-4 ---
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(120))

class Producto(db.Model): # Inventario
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    stock = db.Column(db.Float, default=0) # libras de lechona
    precio_libra = db.Column(db.Float, default=28000)
    costo_libra = db.Column(db.Float, default=15000)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.String(200))

class Venta(db.Model): # Pedidos
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=True)
    libras = db.Column(db.Float)
    total = db.Column(db.Float)
    abono = db.Column(db.Float, default=0)
    estado = db.Column(db.String(20), default='Pendiente') # Pendiente, Entregado, Pagado
    fecha = db.Column(db.DateTime, default=datetime.now)
    cliente = db.relationship('Cliente')

with app.app_context():
    db.create_all()
    if not Usuario.query.first():
        db.session.add(Usuario(username='admin', password='admin123'))
        db.session.commit()
    if not Producto.query.first():
        db.session.add(Producto(nombre='Lechona Tolimense', stock=50, precio_libra=28000, costo_libra=15000))
        db.session.commit()

# --- TEMPLATE BASE ---
BASE = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>RUVE</title><style>
body{background:#000;color:#fff;font-family:Arial;margin:0}
nav{background:#111;padding:15px;display:flex;gap:15px;overflow:auto}
nav a{color:#fff;text-decoration:none;padding:8px 14px;border-radius:20px;background:#222}
nav a.active{background:#ff2e88}
.box{padding:20px;max-width:1000px;margin:auto}
.card{background:#111;border:1px solid #222;padding:15px;border-radius:15px;margin-bottom:15px}
input,select{padding:10px;border-radius:8px;border:none;background:#222;color:#fff;margin:5px}
.btn{background:#ff2e88;color:#fff;border:none;padding:10px 18px;border-radius:8px;font-weight:bold;cursor:pointer}
table{width:100%;border-collapse:collapse} th,td{padding:8px;border-bottom:1px solid #222;text-align:left}
</style></head><body>
<nav>
<a href="/" class="{{'active' if page=='dash' else ''}}">📊 Dashboard</a>
<a href="/ventas" class="{{'active' if page=='ventas' else ''}}">🍖 Ventas</a>
<a href="/inventario" class="{{'active' if page=='inv' else ''}}">📦 Inventario</a>
<a href="/clientes" class="{{'active' if page=='cli' else ''}}">👥 Clientes</a>
<a href="/logout">Salir</a>
</nav><div class="box">{{content|safe}}</div></body></html>
"""

def render(page, content, **kwargs):
    return render_template_string(BASE, content=content, page=page, **kwargs)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=Usuario.query.filter_by(username=request.form['username'], password=request.form['password']).first()
        if u:
            session['user']=u.username
            return redirect('/')
    html="""<div class="card" style="max-width:320px;margin:60px auto;text-align:center">
    <h2 style="color:#ff2e88">🍖 RUVE LECHONA</h2>
    <form method="POST"><input name="username" placeholder="Usuario" required style="width:90%"><br>
    <input name="password" type="password" placeholder="Contraseña" required style="width:90%"><br>
    <button class="btn" style="width:95%;margin-top:10px">Entrar</button></form>
    <p style="font-size:12px;color:#888">admin / admin123</p></div>"""
    return render_template_string(BASE.replace("{{content|safe}}", html).replace("{{'active' if page=='dash' else ''}}",""), content="", page="login")

@app.route('/')
def dashboard():
    if 'user' not in session: return redirect('/login')
    ventas = Venta.query.all()
    total_vendido = sum([v.total for v in ventas])
    total_abonado = sum([v.abono for v in ventas])
    por_cobrar = total_vendido - total_abonado
    prod = Producto.query.first()
    ganancia = sum([(v.total - (v.libras * prod.costo_libra)) for v in ventas]) if prod else 0
    content = f"""
    <h2>Dashboard</h2>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
    <div class="card"><h3>${total_vendido:,.0f}</h3><p>Total Vendido</p></div>
    <div class="card"><h3 style="color:#ff2e88">${por_cobrar:,.0f}</h3><p>Por Cobrar</p></div>
    <div class="card"><h3 style="color:#0f0">${ganancia:,.0f}</h3><p>Ganancia Est.</p></div>
    <div class="card"><h3>{prod.stock if prod else 0} lbs</h3><p>Stock Lechona</p></div>
    </div>
    """
    return render('dash', content)

@app.route('/inventario', methods=['GET','POST'])
def inventario():
    if 'user' not in session: return redirect('/login')
    if request.method=='POST':
        p=Producto.query.first()
        p.stock=float(request.form['stock'])
        p.precio_libra=float(request.form['precio'])
        p.costo_libra=float(request.form['costo'])
        db.session.commit()
        return redirect('/inventario')
    p=Producto.query.first()
    content=f"""
    <h2>Inventario Lechona</h2>
    <div class="card">
    <form method="POST">
    Stock (lbs): <input name="stock" type="number" step="0.1" value="{p.stock}">
    Precio Venta x Libra: <input name="precio" type="number" value="{p.precio_libra}"><br>
    Costo x Libra: <input name="costo" type="number" value="{p.costo_libra}">
    <button class="btn">Actualizar</button>
    </form></div>
    """
    return render('inv', content)

@app.route('/clientes', methods=['GET','POST'])
def clientes():
    if 'user' not in session: return redirect('/login')
    if request.method=='POST':
        db.session.add(Cliente(nombre=request.form['nombre'], telefono=request.form['tel'], direccion=request.form['dir']))
        db.session.commit()
        return redirect('/clientes')
    clis=Cliente.query.all()
    rows="".join([f"<tr><td>{c.nombre}</td><td>{c.telefono}</td><td>{c.direccion}</td></tr>" for c in clis])
    content=f"""
    <h2>Clientes</h2>
    <div class="card"><form method="POST"><input name="nombre" placeholder="Nombre" required><input name="tel" placeholder="Tel"><input name="dir" placeholder="Dirección"><button class="btn">Agregar</button></form></div>
    <div class="card"><table><tr><th>Nombre</th><th>Tel</th><th>Dirección</th></tr>{rows}</table></div>
    """
    return render('cli', content)

@app.route('/ventas', methods=['GET','POST'])
def ventas():
    if 'user' not in session: return redirect('/login')
    prod=Producto.query.first()
    clientes=Cliente.query.all()
    if request.method=='POST':
        libras=float(request.form['libras'])
        if prod.stock < libras:
            return render('ventas', f"<div class='card' style='color:red'>No hay stock suficiente. Solo {prod.stock} lbs</div><a href='/ventas' class='btn'>Volver</a>")
        total=libras*prod.precio_libra
        abono=float(request.form['abono'] or 0)
        cid=int(request.form['cliente']) if request.form['cliente'] else None
        v=Venta(cliente_id=cid, libras=libras, total=total, abono=abono, estado=request.form['estado'])
        prod.stock-=libras
        db.session.add(v)
        db.session.commit()
        return redirect('/ventas')
    ventas=Venta.query.order_by(Venta.fecha.desc()).all()
    rows="".join([f"<tr><td>{v.id}</td><td>{v.cliente.nombre if v.cliente else 'General'}</td><td>{v.libras} lbs</td><td>${v.total:,.0f}</td><td>${v.abono:,.0f}</td><td>{v.estado}</td><td>{v.fecha.strftime('%d/%m %H:%M')}</td></tr>" for v in ventas])
    opt="".join([f"<option value='{c.id}'>{c.nombre}</option>" for c in clientes])
    content=f"""
    <h2>Ventas / Pedidos</h2>
    <div class="card">
    <form method="POST">
    <select name="cliente"><option value="">Cliente General</option>{opt}</select>
    Libras: <input name="libras" type="number" step="0.1" required>
    Abono: <input name="abono" type="number" value="0">
    <select name="estado"><option>Pendiente</option><option>Entregado</option><option>Pagado</option></select>
    <button class="btn">Registrar Venta</button>
    </form>
    <p style="color:#888">Precio actual: ${prod.precio_libra:,.0f} x libra | Stock: {prod.stock} lbs</p>
    </div>
    <div class="card"><table><tr><th>#</th><th>Cliente</th><th>Lbs</th><th>Total</th><th>Abono</th><th>Estado</th><th>Fecha</th></tr>{rows}</table></div>
    """
    return render('ventas', content)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)