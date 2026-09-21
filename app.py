from flask import Flask, request, redirect, session, render_template_string, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, urllib.parse, io

app = Flask(__name__)
app.secret_key = 'lechon-ruve-2026-final'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lechon.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), unique=True)
    password=db.Column(db.String(200))
    is_admin=db.Column(db.Boolean, default=False)
class Producto(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    nombre=db.Column(db.String(100))
    precio=db.Column(db.Float)
    stock=db.Column(db.Integer, default=0)
class Venta(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    cliente=db.Column(db.String(100))
    producto_nombre=db.Column(db.String(100))
    cantidad=db.Column(db.Integer)
    total=db.Column(db.Float)
    fecha=db.Column(db.DateTime, default=datetime.utcnow)
    vendedor=db.Column(db.String(80), default="admin")
class Config(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    whatsapp_btn=db.Column(db.Boolean, default=True)
    tickets=db.Column(db.Boolean, default=True)
    reporte_pdf=db.Column(db.Boolean, default=True)
    total_whatsapp=db.Column(db.Boolean, default=True)
    numero_whatsapp=db.Column(db.String(20), default="529831000000")

def get_config():
    c=Config.query.first()
    if not c: c=Config(); db.session.add(c); db.session.commit()
    return c

with app.app_context():
    db.create_all()
    # Crear admin si no existe
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password=generate_password_hash('admin123'), is_admin=True))
        db.session.commit()
    else:
        u=User.query.filter_by(username='admin').first()
        u.is_admin=True; db.session.commit()
    get_config()
    if Producto.query.count()==0:
        db.session.add_all([Producto(nombre='Lechón por Kilo', precio=350, stock=50), Producto(nombre='Lechón Entero', precio=3500, stock=5), Producto(nombre='Torta de Lechón', precio=70, stock=30)]); db.session.commit()

STYLE = """<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><style>
body{background:#000;color:white;font-family:Arial}.card{background:#111;border:2px solid #ff4d8a;border-radius:15px;padding:20px}
.btn-rosa{background:#ff4d8a;color:white;border:none;padding:10px 18px;border-radius:10px;font-weight:bold}
.btn-whats{background:#25D366;color:white;padding:6px 12px;border-radius:8px;text-decoration:none;font-size:12px;font-weight:bold}
.navbar{background:#000!important;border-bottom:2px solid #ff4d8a}
input,select{background:#222!important;color:white!important;border:1px solid #ff4d8a!important}
a{color:#ff4d8a;text-decoration:none}
@media print{.no-print{display:none} body{background:white;color:black}}
</style>"""

def nav():
    is_admin = session.get('is_admin', False)
    admin_links = f'<a href="/admin/config" class="me-3" style="color:#25D366">⚙️ Config</a><a href="/admin/usuarios" class="me-3" style="color:#ffcc00">👥 Usuarios</a>' if is_admin else ''
    prod_link = '<a href="/productos" class="me-3">Productos</a>' if is_admin else ''
    return f'<nav class="navbar p-3"><div class="d-flex align-items-center"><img src="/static/logo.png?v=ruve3" style="width:45px;height:45px;border-radius:50%;margin-right:10px;background:white;padding:3px"><h4 style="color:#ff4d8a" class="m-0">Ruve</h4> <small style="color:#aaa;margin-left:10px">{session.get("user")} {"(Admin)" if is_admin else "(Empleado)"}</small></div><div><a href="/dashboard" class="me-3">Dashboard</a>{prod_link}<a href="/ventas" class="me-3">Ventas</a><a href="/reporte" class="me-3">Reporte</a>{admin_links}<a href="/logout">Salir</a></div></nav>'

def make_whats_msg(v): return urllib.parse.quote(f"Hola {v.cliente}! 🐖 Tu pedido Ruve: {v.cantidad}x {v.producto_nombre} - ${v.total}. Ticket #{v.id} - EL SABOR HACE LA DIFERENCIA 🔥")
def admin_required():
    if 'user' not in session: return redirect('/')
    if not session.get('is_admin'): return redirect('/dashboard')
    return None

@app.route('/', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user']=u.username; session['is_admin']=u.is_admin; return redirect('/dashboard')
    return render_template_string(STYLE+f'<div class="container" style="max-width:420px;margin-top:25px"><div class="card text-center"><img src="/static/logo.png?v=ruve3" style="width:210px;height:210px;object-fit:contain;background:white;border-radius:50%;padding:8px;border:3px solid #ff4d8a;margin:0 auto"><h2 style="color:#ff4d8a" class="mt-3">LechonAlHornoRuve</h2><form method="POST" class="mt-4 text-start"><input name="username" class="form-control mb-3" placeholder="Usuario" required><input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required><button class="btn-rosa w-100">ENTRAR</button></form><small style="color:#555">admin / admin123</small></div></div>')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    cfg=get_config(); productos=Producto.query.all(); ventas=Venta.query.order_by(Venta.id.desc()).limit(12).all()
    hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0); total_hoy=sum([v.total for v in Venta.query.filter(Venta.fecha>=hoy).all()])
    html=STYLE+nav()+"""<div class="container mt-4"><div class="row"><div class="col-md-4"><div class="card text-center"><h6>Ventas Hoy</h6><h2 style="color:#ff4d8a">${{total_hoy}}</h2></div></div><div class="col-md-4"><div class="card text-center"><h6>Productos</h6><h2 style="color:#ff4d8a">{{num_prod}}</h2></div></div><div class="col-md-4"><div class="card text-center"><h6>Tickets</h6><h2 style="color:#ff4d8a">{{num_ventas}}</h2></div></div></div>
    <div class="card mt-4"><h5 style="color:#ff4d8a">Vender Rápido - Chetumal (Vendedor: {{session.get('user')}})</h5>
    <form action="/vender" method="POST" class="row g-2 mt-3"><div class="col-md-3"><input name="cliente" class="form-control" placeholder="👤 Cliente"></div><div class="col-md-4"><select name="producto_id" class="form-control" required>{% for p in productos %}<option value="{{p.id}}">{{p.nombre}} - ${{p.precio}} (Stock: {{p.stock}})</option>{% endfor %}</select></div><div class="col-md-2"><input name="cantidad" type="number" value="1" min="1" class="form-control"></div><div class="col-md-3"><button class="btn-rosa w-100">💰 VENDER</button></div></form></div>
    <div class="card mt-4"><h5>Últimas Ventas</h5><table class="table table-dark table-bordered mt-3"><tr><th>Cliente</th><th>Producto</th><th>Total</th><th>Vendedor</th><th>Acciones</th></tr>
    {% for v in ventas %}<tr><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td><td>{{v.vendedor}}</td><td>{% if cfg.tickets %}<a href="/ticket/{{v.id}}" class="btn-rosa" style="font-size:11px;padding:4px 8px">🎫 TICKET</a>{% endif %}{% if cfg.whatsapp_btn %}<a href="https://wa.me/?text={{v.msj}}" target="_blank" class="btn-whats ms-1">📲 WA</a>{% endif %}</td></tr>{% endfor %}</table></div></div>"""
    for v in ventas: v.msj=make_whats_msg(v)
    return render_template_string(html, productos=productos, ventas=ventas, total_hoy=total_hoy, num_prod=Producto.query.count(), num_ventas=Venta.query.count(), cfg=cfg)

@app.route('/vender', methods=['POST'])
def vender():
    if 'user' not in session: return redirect('/')
    cfg=get_config(); prod=Producto.query.get(int(request.form['producto_id']))
    v=Venta(cliente=(request.form.get('cliente') or "Mostrador").strip() or "Mostrador", producto_nombre=prod.nombre, cantidad=int(request.form['cantidad']), total=prod.precio*int(request.form['cantidad']), vendedor=session.get('user'))
    if prod.stock>=v.cantidad: prod.stock-=v.cantidad
    db.session.add(v); db.session.commit()
    if cfg.tickets: return redirect(f'/ticket/{v.id}')
    return redirect('/dashboard')

@app.route('/ticket/<int:id>')
def ticket(id):
    if 'user' not in session: return redirect('/')
    cfg=get_config()
    if not cfg.tickets: return redirect('/dashboard')
    v=Venta.query.get(id); msj=make_whats_msg(v)
    return render_template_string(STYLE+f'<div class="container" style="max-width:380px;margin-top:20px"><div class="card" style="background:white;color:black;border:2px dashed black"><div class="text-center"><img src="/static/logo.png?v=ruve3" style="width:110px"><h5 style="font-weight:bold">LECHÓN AL HORNO RUVE</h5><small>EL SABOR HACE LA DIFERENCIA</small></div><hr style="border-top:1px dashed black"><p><b>Ticket #{v.id}</b><br>Cliente: {v.cliente}<br>Vendedor: {v.vendedor}<br>Fecha: {v.fecha.strftime("%d/%m/%Y %H:%M")}<br>Producto: {v.producto_nombre}<br>Cant: {v.cantidad}<br><b>Total: ${v.total}</b></p><hr style="border-top:1px dashed black"><p class="text-center" style="font-size:12px">¡Gracias por su compra! 🔥<br>Chetumal, Q. Roo</p><div class="text-center no-print"><button onclick="window.print()" class="btn-rosa">🖨️ IMPRIMIR</button>'+(f'<a href="https://wa.me/?text={msj}" target="_blank" class="btn-whats ms-2 p-2">📲 WhatsApp</a>' if cfg.whatsapp_btn else '')+f'<a href="/dashboard" class="btn btn-dark ms-2">Volver</a></div></div></div>')

@app.route('/productos', methods=['GET','POST'])
def productos_route():
    if 'user' not in session: return redirect('/')
    if not session.get('is_admin'): return redirect('/dashboard')
    if request.method=='POST':
        db.session.add(Producto(nombre=request.form['nombre'], precio=float(request.form['precio']), stock=int(request.form['stock']))); db.session.commit(); return redirect('/productos')
    return render_template_string(STYLE+nav()+'<div class="container mt-4"><div class="card"><h5>Agregar Producto (Solo Admin)</h5><form method="POST" class="row g-2 mt-2"><div class="col-md-4"><input name="nombre" class="form-control" placeholder="Nombre" required></div><div class="col-md-3"><input name="precio" type="number" step="0.01" class="form-control" placeholder="Precio" required></div><div class="col-md-2"><input name="stock" type="number" class="form-control" placeholder="Stock" required></div><div class="col-md-3"><button class="btn-rosa w-100">Agregar</button></div></form><table class="table table-dark table-bordered mt-4"><tr><th>Nombre</th><th>Precio</th><th>Stock</th><th></th></tr>{% for p in productos %}<tr><td>{{p.nombre}}</td><td>${{p.precio}}</td><td>{{p.stock}}</td><td><a href="/eliminar_producto/{{p.id}}" style="color:red">Eliminar</a></td></tr>{% endfor %}</table></div></div>', productos=Producto.query.all())

@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):
    if not session.get('is_admin'): return redirect('/dashboard')
    p=Producto.query.get(id)
    if p: db.session.delete(p); db.session.commit()
    return redirect('/productos')

@app.route('/ventas')
def ventas_route():
    if 'user' not in session: return redirect('/')
    cfg=get_config(); ventas=Venta.query.order_by(Venta.id.desc()).all()
    for v in ventas: v.msj=make_whats_msg(v)
    return render_template_string(STYLE+nav()+'<div class="container mt-4"><div class="card"><h5>Historial - Total: ${{total}}</h5><table class="table table-dark table-bordered mt-3"><tr><th>Cliente</th><th>Producto</th><th>Total</th><th>Vendedor</th><th>Acciones</th></tr>{% for v in ventas %}<tr><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td><td>{{v.vendedor}}</td><td>{% if cfg.tickets %}<a href="/ticket/{{v.id}}" class="btn-rosa" style="font-size:11px">TICKET</a>{% endif %}{% if cfg.whatsapp_btn %}<a href="https://wa.me/?text={{v.msj}}" target="_blank" class="btn-whats ms-1">WA</a>{% endif %}</td></tr>{% endfor %}</table></div></div>', ventas=ventas, total=sum([v.total for v in ventas]), cfg=cfg)

@app.route('/reporte')
def reporte():
    if 'user' not in session: return redirect('/')
    cfg=get_config(); hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    ventas_hoy=Venta.query.filter(Venta.fecha>=hoy).order_by(Venta.fecha.desc()).all(); total_hoy=sum([v.total for v in ventas_hoy])
    msg=f"📊 REPORTE RUVE {datetime.now().strftime('%d/%m/%Y')} - Total: ${total_hoy} - {len(ventas_hoy)} ventas"; msg_enc=urllib.parse.quote(msg)
    return render_template_string(STYLE+nav()+'<div class="container mt-4"><div class="card"><h4>Total Hoy: <span style="color:#25D366">${{total_hoy}}</span> ({{ventas_hoy|length}} ventas)</h4><div class="no-print mt-3"><button onclick="window.print()" class="btn-rosa me-2">🖨️ IMPRIMIR</button>{% if cfg.reporte_pdf %}<a href="/reporte_pdf" class="btn btn-light me-2">📄 PDF</a>{% endif %}{% if cfg.total_whatsapp %}<a href="https://wa.me/{{cfg.numero_whatsapp}}?text={{msg_enc}}" target="_blank" class="btn-whats p-2">📲 Total a mi WhatsApp</a>{% endif %}</div><table class="table table-dark table-bordered mt-4"><tr><th>Hora</th><th>Cliente</th><th>Producto</th><th>Vendedor</th><th>Total</th></tr>{% for v in ventas_hoy %}<tr><td>{{v.fecha.strftime("%H:%M")}}</td><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>{{v.vendedor}}</td><td>${{v.total}}</td></tr>{% endfor %}</table></div></div>', ventas_hoy=ventas_hoy, total_hoy=total_hoy, cfg=cfg, msg_enc=msg_enc)

@app.route('/reporte_pdf')
def reporte_pdf():
    if 'user' not in session: return redirect('/')
    cfg=get_config()
    if not cfg.reporte_pdf: return redirect('/reporte')
    hoy=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0); ventas=Venta.query.filter(Venta.fecha>=hoy).all(); total=sum([v.total for v in ventas])
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    buffer=io.BytesIO(); c=canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 16); c.drawString(50,750,"LECHON AL HORNO RUVE - REPORTE"); c.setFont("Helvetica", 12); c.drawString(50,730,f"Fecha: {datetime.now().strftime('%d/%m/%Y')} - Total: ${total} - Ventas: {len(ventas)}")
    y=700
    for v in ventas:
        c.drawString(50,y,f"{v.fecha.strftime('%H:%M')} - {v.cliente} - {v.cantidad}x {v.producto_nombre} - ${v.total} - Vend: {v.vendedor}"); y-=20
        if y<50: c.showPage(); y=750
    c.save(); buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"reporte_ruve_{datetime.now().strftime('%d%m%Y')}.pdf", mimetype='application/pdf')

@app.route('/admin/config', methods=['GET','POST'])
def admin_config():
    chk=admin_required()
    if chk: return chk
    cfg=get_config()
    if request.method=='POST':
        cfg.whatsapp_btn = 'whatsapp_btn' in request.form; cfg.tickets = 'tickets' in request.form; cfg.reporte_pdf = 'reporte_pdf' in request.form; cfg.total_whatsapp = 'total_whatsapp' in request.form
        cfg.numero_whatsapp = request.form.get('numero_whatsapp','').strip() or cfg.numero_whatsapp; db.session.commit(); return redirect('/admin/config')
    return render_template_string(STYLE+nav()+"""<div class="container mt-4" style="max-width:600px"><div class="card"><h4 style="color:#ff4d8a">⚙️ Configuración Admin</h4><form method="POST" class="mt-4">
    <label style="display:flex;align-items:center;border:2px solid #333;border-radius:12px;padding:15px;margin-bottom:15px;cursor:pointer;background:#0a0a0a"><input type="checkbox" name="whatsapp_btn" style="width:28px;height:28px;accent-color:#ff4d8a" {{'checked' if cfg.whatsapp_btn}}><span style="margin-left:15px"><b>📲 1. Botón WhatsApp</b></span></label>
    <label style="display:flex;align-items:center;border:2px solid #333;border-radius:12px;padding:15px;margin-bottom:15px;cursor:pointer;background:#0a0a0a"><input type="checkbox" name="tickets" style="width:28px;height:28px;accent-color:#ff4d8a" {{'checked' if cfg.tickets}}><span style="margin-left:15px"><b>🎫 2. Tickets</b></span></label>
    <label style="display:flex;align-items:center;border:2px solid #333;border-radius:12px;padding:15px;margin-bottom:15px;cursor:pointer;background:#0a0a0a"><input type="checkbox" name="reporte_pdf" style="width:28px;height:28px;accent-color:#ff4d8a" {{'checked' if cfg.reporte_pdf}}><span style="margin-left:15px"><b>📄 3. Reporte PDF</b></span></label>
    <label style="display:flex;align-items:center;border:2px solid #333;border-radius:12px;padding:15px;margin-bottom:15px;cursor:pointer;background:#0a0a0a"><input type="checkbox" name="total_whatsapp" style="width:28px;height:28px;accent-color:#ff4d8a" {{'checked' if cfg.total_whatsapp}}><span style="margin-left:15px"><b>💰 4. Total a mi WhatsApp</b></span></label>
    <div class="mb-4"><label style="color:#ff4d8a">Tu número WhatsApp:</label><input name="numero_whatsapp" class="form-control mt-2" value="{{cfg.numero_whatsapp}}"></div>
    <button class="btn-rosa w-100" style="padding:14px">💾 GUARDAR</button></form></div></div>""", cfg=cfg)

@app.route('/admin/usuarios', methods=['GET','POST'])
def admin_usuarios():
    chk=admin_required()
    if chk: return chk
    if request.method=='POST':
        if User.query.filter_by(username=request.form['username']).first():
            return render_template_string(STYLE+nav()+'<div class="container mt-4"><div class="card"><h5 style="color:red">Ese usuario ya existe</h5><a href="/admin/usuarios" class="btn-rosa">Volver</a></div></div>')
        es_admin = 'is_admin' in request.form
        db.session.add(User(username=request.form['username'].strip(), password=generate_password_hash(request.form['password']), is_admin=es_admin)); db.session.commit(); return redirect('/admin/usuarios')
    return render_template_string(STYLE+nav()+"""
    <div class="container mt-4"><div class="row"><div class="col-md-4"><div class="card"><h5 style="color:#ffcc00">👥 Crear Usuario</h5>
    <form method="POST" class="mt-3"><input name="username" class="form-control mb-3" placeholder="Usuario (ej: maria)" required><input name="password" class="form-control mb-3" type="text" placeholder="Contraseña (ej: 1234)" required>
    <label style="display:flex;align-items:center;cursor:pointer;margin-bottom:15px"><input type="checkbox" name="is_admin" style="width:20px;height:20px;accent-color:#ff4d8a"> <span style="margin-left:10px">Es administrador (puede ver Config y Usuarios)</span></label>
    <button class="btn-rosa w-100">Crear Usuario</button></form><small style="color:#666" class="mt-3 d-block">Empleado: solo puede vender y ver reporte. Admin: todo.</small></div></div>
    <div class="col-md-8"><div class="card"><h5>Usuarios Actuales</h5><table class="table table-dark table-bordered mt-3"><tr><th>Usuario</th><th>Rol</th><th>Acción</th></tr>
    {% for u in usuarios %}<tr><td>{{u.username}}</td><td>{% if u.is_admin %}<span style="color:#25D366">ADMIN</span>{% else %}Empleado{% endif %}</td><td>{% if u.username!='admin' %}<a href="/admin/usuarios/eliminar/{{u.id}}" style="color:red" onclick="return confirm('¿Eliminar?')">Eliminar</a>{% else %}<small style="color:#555">No se puede eliminar</small>{% endif %}</td></tr>{% endfor %}</table></div></div></div></div>
    """, usuarios=User.query.all())

@app.route('/admin/usuarios/eliminar/<int:id>')
def eliminar_usuario(id):
    chk=admin_required()
    if chk: return chk
    u=User.query.get(id)
    if u and u.username!='admin': db.session.delete(u); db.session.commit()
    return redirect('/admin/usuarios')

@app.route('/logout')
def logout(): session.clear(); return redirect('/')

if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))