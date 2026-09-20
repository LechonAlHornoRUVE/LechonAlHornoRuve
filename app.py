from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "lechon-ruve-2026"
db_url = os.environ.get("DATABASE_URL","")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://","postgresql://",1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///lechon.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

METODOS_PAGO = ["EFECTIVO", "TRANSFERENCIA", "TARJETA"]

class Usuario(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(80),unique=True)
    password=db.Column(db.String(80))
    rol=db.Column(db.String(20))
    pin=db.Column(db.String(10))
class Mesa(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    numero=db.Column(db.Integer,unique=True)
    zona=db.Column(db.String(50),default="Salon")
    estado=db.Column(db.String(20),default="LIBRE")
    pax=db.Column(db.Integer,default=0)
class Producto(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    nombre=db.Column(db.String(100))
    precio=db.Column(db.Float)
    categoria=db.Column(db.String(50))
    activo=db.Column(db.Boolean,default=True)
class Pedido(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    mesa_id=db.Column(db.Integer,db.ForeignKey('mesa.id'))
    total=db.Column(db.Float,default=0)
    estado=db.Column(db.String(20),default="ABIERTO")
    metodo_pago=db.Column(db.String(20))
    creado=db.Column(db.DateTime,default=datetime.utcnow)

with app.app_context():
    db.create_all()
    if not Usuario.query.first():
        db.session.add_all([
            Usuario(username="admin",password="admin123",rol="ADMIN",pin="1234"),
            Usuario(username="cajero",password="cajero123",rol="CAJERO",pin="1111"),
            Usuario(username="mesero",password="mesero123",rol="MESERO"),
            Usuario(username="cocina",password="cocina123",rol="COCINA"),
        ])
        db.session.commit()
    if not Mesa.query.first():
        for i in range(1,13):
            db.session.add(Mesa(numero=i,zona="Salon" if i<=8 else "Terraza"))
        db.session.commit()
    if not Producto.query.first():
        db.session.add_all([
            Producto(nombre="Lechon al Horno 1kg",precio=350,categoria="Lechon"),
            Producto(nombre="Cochinita 1kg",precio=320,categoria="Lechon"),
            Producto(nombre="Refresco 600ml",precio=30,categoria="Bebidas"),
        ])
        db.session.commit()

@app.route('/')
def index():
    if 'rol' not in session: return redirect('/login')
    r=session['rol']
    if r=='ADMIN': return redirect('/admin')
    if r=='CAJERO': return redirect('/pos')
    if r=='MESERO': return redirect('/mesero')
    if r=='COCINA': return redirect('/cocina')
    return f"<h1>LechonAlHornoRuve - {r}</h1><a href='/logout'>Salir</a>"
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=Usuario.query.filter_by(username=request.form['username'],password=request.form['password']).first()
        if u:
            session['user_id']=u.id; session['rol']=u.rol; session['username']=u.username
            return redirect('/')
    return render_template('login.html')
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/admin')
def admin():
    if session.get('rol')!='ADMIN': return redirect('/login')
    return render_template('admin.html',mesas=Mesa.query.all(),productos=Producto.query.all(),metodos=METODOS_PAGO)
@app.route('/pos')
def pos():
    if session.get('rol') not in ['ADMIN','CAJERO']: return redirect('/login')
    return render_template('pos.html',mesas=Mesa.query.filter(Mesa.estado!='LIBRE').all(),metodos=METODOS_PAGO)
@app.route('/mesero')
def mesero():
    if session.get('rol') not in ['ADMIN','MESERO']: return redirect('/login')
    return render_template('mesero.html',mesas=Mesa.query.all(),productos=Producto.query.filter_by(activo=True).all())
@app.route('/cocina')
def cocina():
    if session.get('rol') not in ['ADMIN','COCINA']: return redirect('/login')
    return render_template('cocina.html',pedidos=Pedido.query.filter_by(estado='ABIERTO').all())
@app.route('/api/mesa/<int:id>/abrir',methods=['POST'])
def abrir_mesa(id):
    m=Mesa.query.get(id); m.estado='OCUPADA'; m.pax=request.form.get('pax',2,type=int); db.session.commit(); return redirect('/mesero')