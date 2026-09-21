from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <body style="background:#0a0a0a; color:#ff1493; font-family:Arial; text-align:center; padding-top:100px">
        <h1>🐖 LechonAlHornoRuve</h1>
        <h2 style="color:white">¡YA ESTÁ LIVE!</h2>
        <p>Si ves esto, Render ya funciona. Ahora sí metemos el login.</p>
        <p style="color:green">HTTP 200 - OK</p>
    </body>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)