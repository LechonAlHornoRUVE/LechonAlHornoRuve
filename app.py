from flask import Flask, request, redirect, session, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
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

# Crear admin sin que crashee
try:
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password=generate_password_hash('admin123')))
            db.session.commit()
except:
    pass

LOGIN = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#000;color:white} .card{background:#111;border:2px solid #ff1493;border-radius:15px;padding:25px} .btn-rosa{background:#ff1493;color:white;width:100%;padding:10px;border:none;border-radius:8px;font-weight:bold} input{background:#222!important;color:white!important;border:1px solid #ff1493!important}</style>
<div class="container" style="max-width:400px;margin-top:80px">
<div class="card text-center">
<h2 style="color:#ff1493">🐖 LechonAlHornoRuve</h2>
<form method="POST" class="mt-4 text-start">
<input name="username" class="form-control mb-3" placeholder="Usuario" required>
<input name="password" type="password" class="form-control mb-3" placeholder="Contraseña" required>
<button class="btn-rosa">ENTRAR</button>
</form>
{% if error %}<p style="color:red" class="mt-3">{{error}}</p>{% endif %}
<small class="mt-3 d-block">admin / admin123</small>
</div></div>
"""

DASH = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#000;color:white} .navbar{background:#000!important;border-bottom:2px solid #ff1493} .card{background:#111;border:1px solid #ff1493;border-radius:12px;padding:20px}</style>
<nav class="navbar p-3"><h4 style="color:#ff1493" class="m-0">🐖 LechonAlHornoRuve</h4><a href="/logout" style="color:#ff1493">Salir</a></nav>
<div class="container mt-4"><div class="card">
<h3 style="color:#ff1493">¡Bienvenido {{user}}!</h3>
<p>Sistema de Lechón al Horno - Chetumal, Quintana Roo</p>
<div class="alert" style="background:#ff14931a;border:1px solid #ff1493">✅ Sistema funcionando correctamente en Render</div>
</div></div>
"""

@app.route('/', methods=['GET','POST'])
def login():
    error=None
    if request.method=='POST':
        u=User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            session['user']=u.username
            return redirect('/dashboard')
        error="Datos incorrectos"
    return render_template_string(LOGIN, error=error)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    return render_template_string(DASH, user=session['user'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))