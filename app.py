# Copia y pega esto completo en tu app.py
from flask import Flask, request, redirect, session, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
app = Flask(__name__)
app.secret_key = 'lechon-ruve-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lechon.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
class User(db.Model):
 id = db.Column(db.Integer, primary_key=True)
 username = db.Column(db.String(80), unique=True)
 password = db.Column(db.String(200))
class Producto(db.Model):
 id = db.Column(db.Integer, primary_key=True)
 nombre = db.Column(db.String(100))
 precio = db.Column(db.Float)
 stock = db.Column(db.Integer, default=0)
class Venta(db.Model):
 id = db.Column(db.Integer, primary_key=True)
 cliente = db.Column(db.String(100))
 producto_nombre = db.Column(db.String(100))
 cantidad = db.Column(db.Integer)
 total = db.Column(db.Float)
 fecha = db.Column(db.DateTime, default=datetime.utcnow)
with app.app_context():
 db.create_all()
 if not User.query.filter_by(username='admin').first():
  db.session.add(User(username='admin', password=generate_password_hash('admin123')))
  db.session.commit()
STYLE = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#000;color:white;font-family:Arial}.card{background:#111;border:2px solid #ff4d8a;border-radius:15px;padding:20px}.btn-rosa{background:#ff4d8a;color:white;border:none;padding:10px 15px;border-radius:8px;font-weight:bold}.navbar{background:#000!important;border-bottom:2px solid #ff4d8a}input,select{background:#222!important;color:white!important;border:1px solid #ff4d8a!important}a{color:#ff4d8a;text-decoration:none}</style>
"""
LOGIN_HTML = STYLE + """
<div class="container" style="max-width:420px;margin-top:30px"><div class="card text-center">
<img src="/static/logo.png?v=ruve" style="width:200px;height:200px;object-fit:contain;margin:0 auto 10px auto;display:block;background:white;border-radius:50%;padding:5px;border:3px solid #ff4d8a">
<h2 style="color:#ff4d8a;margin:0">LechonAlHornoRuve</h2><p style="font-size:12px;color:#aaa">EL SABOR HACE LA DIFERENCIA 🔥</p>
<form method="POST" class="mt-4 text-start"><input name="username" class="form-control mb-3" placeholder="Usuario" required><input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required><button class="btn-rosa w-100">ENTRAR</button></form><small style="color:#666">admin / admin123</small></div></div>
"""
DASH_HTML = STYLE + """
<nav class="navbar p-3"><div class="d-flex align-items-center"><img src="/static/logo.png?v=ruve" style="width:45px;height:45px;border-radius:50%;margin-right:10px;background:white;padding:2px"><h4 style="color:#ff4d8a" class="m-0">Ruve</h4></div><div><a href="/productos" class="me-2">Productos</a><a href="/ventas" class="me-2">Ventas</a><a href="/logout">Salir</a></div></nav>
<div class="container mt-4"><div class="card"><h4 style="color:#ff4d8a">Vender Rápido - Chetumal</h4><form action="/vender" method="POST" class="row g-2 mt-2"><div class="col-md-4"><input name="cliente" class="form-control" placeholder="👤 Cliente (Mostrador)"></div><div class="col-md-4"><select name="producto_id" class="form-control" required>{% for p in productos %}<option value="{{p.id}}">{{p.nombre}} - ${{p.precio}}</option>{% endfor %}</select></div><div class="col-md-2"><input name="cantidad" type="number" value="1" min="1" class="form-control" required></div><div class="col-md-2"><button class="btn-rosa w-100">VENDER</button></div></form></div><div class="card mt-3"><table class="table table-dark table-bordered"><tr><th>Cliente</th><th>Producto</th><th>Total</th></tr>{% for v in ventas %}<tr><td>{{v.cliente}}</td><td>{{v.cantidad}}x {{v.producto_nombre}}</td><td>${{v.total}}</td></tr>{% endfor %}</table></div></div>
"""
@app.route('/', methods=['GET','POST'])
def login():
 if request.method=='POST':
  u=User.query.filter_by(username=request.form['username']).first()
  if u and check_password_hash(u.password, request.form['password']):
   session['user']=u.username
   return redirect('/dashboard')
 return render_template_string(LOGIN_HTML)
@app.route('/dashboard')
def dashboard():
 if 'user' not in session: return redirect('/')
 return render_template_string(DASH_HTML, productos=Producto.query.all(), ventas=Venta.query.order_by(Venta.id.desc()).limit(10).all())
@app.route('/productos', methods=['GET','POST'])
def productos_route():
 if 'user' not in session: return redirect('/')
 if request.method=='POST':
  db.session.add(Producto(nombre=request.form['nombre'], precio=float(request.form['precio']), stock=int(request.form['stock']))); db.session.commit()
  return redirect('/productos')
 return render_template_string(STYLE + """<nav class="navbar p-3"><h4 style="color:#ff4d8a">Productos</h4><a href="/dashboard">Dashboard</a></nav><div class="container mt-4"><div class="card"><form method="POST" class="row g-2"><div class="col-md-4"><input name="nombre" class="form-control" placeholder="Nombre" required></div><div class="col-md-3"><input name="precio" type="number" class="form-control" placeholder="Precio" required></div><div class="col-md-2"><input name="stock" type="number" class="form-control" placeholder="Stock" required></div><div class="col-md-3"><button class="btn-rosa w-100">Agregar</button></div></form></div></div>""", productos=Producto.query.all())
@app.route('/vender', methods=['POST'])
def vender():
 prod=Producto.query.get(int(request.form['producto_id']))
 cliente = request.form.get('cliente') or "Mostrador"
 if cliente.strip()=="": cliente="Mostrador"
 v=Venta(cliente=cliente, producto_nombre=prod.nombre, cantidad=int(request.form['cantidad']), total=prod.precio*int(request.form['cantidad']))
 if prod.stock>=int(request.form['cantidad']): prod.stock-=int(request.form['cantidad'])
 db.session.add(v); db.session.commit()
 return redirect('/dashboard')
@app.route('/ventas')
def ventas_route():
 return render_template_string(STYLE + """<div class="container mt-4"><div class="card"><h3>Ventas</h3><a href="/dashboard">Volver</a></div></div>""")
@app.route('/logout')
def logout():
 session.clear(); return redirect('/')
if __name__=='__main__':
 app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))