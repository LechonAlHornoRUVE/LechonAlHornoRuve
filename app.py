# ... deja todo tu código igual arriba ...
# Solo reemplaza tu CONFIG_TEMPLATE por este:

CONFIG_TEMPLATE = BASE_NAV + """
<style>
body{background:#0a0a0a;color:white;font-family:Arial;margin:0;}
.config-container{max-width:900px;margin:30px auto;background:#111;border:2px solid #ff2d78;border-radius:12px;padding:25px;box-shadow:0 0 20px rgba(255,45,120,0.4);}
.config-container h2{color:#ff4d8d;text-align:center;margin-bottom:20px;}
details{background:#000;border:1px solid #ff2d78;border-radius:8px;margin-top:12px;padding:12px;}
summary{cursor:pointer;color:#ff4d8d;font-weight:bold;font-size:16px;list-style:none;}
summary::-webkit-details-marker{display:none;}
.cinta-item{padding:10px;background:#1a1a1a;border-radius:6px;margin:5px 0;display:flex;justify-content:space-between;align-items:center;border-left:4px solid #ff2d78;}
.cinta-item span{font-size:15px;}
.cinta-pos{color:#ff4d8d;border-left-color:#ff4d8d;}
.cinta-mesas{color:#00d4ff;border-left-color:#00d4ff;}
.cinta-cocina{color:#ffcc00;border-left-color:#ffcc00;}
.cinta-clientes{color:#00ff88;border-left-color:#00ff88;}
.cinta-dueno{color:#ff6b9d;border-left-color:#ff6b9d;}
.cinta-productos{color:#ff5c8a;border-left-color:#ff5c8a;}
.cinta-ventas{color:#ff5c8a;border-left-color:#ff5c8a;}
.cinta-reporte{color:#ff5c8a;border-left-color:#ff5c8a;}
.cinta-config{color:#4eff88;border-left-color:#4eff88;}
.cinta-usuarios{color:#ffcc00;border-left-color:#ffcc00;}
.cinta-salir{color:#ff4444;border-left-color:#ff4444;}
.btn-guardar{width:100%;background:#ff2d78;color:white;border:none;padding:12px;border-radius:8px;margin-top:20px;font-weight:bold;cursor:pointer;}
</style>

<div class="config-container">
  <h2>⚙️ Configuración Administrador</h2>

  <!-- AQUÍ ESTÁ TU CINTA EN LISTA DESPLEGABLE -->
  <details open>
    <summary>📌 CINTA PRINCIPAL - Menú del Sistema ▼ (igual a la foto)</summary>
    
    <div class="cinta-item cinta-pos"><span>🔴 POS</span> <span>Activo</span></div>
    <div class="cinta-item cinta-mesas"><span>🪑 Mesas</span> <a href="/mesas" style="color:#00d4ff;">Ir</a></div>
    <div class="cinta-item cinta-cocina"><span>🔥 Cocina</span> <a href="/cocina" style="color:#ffcc00;">Ir</a></div>
    <div class="cinta-item cinta-clientes"><span>👤 Clientes</span> <a href="/clientes" style="color:#00ff88;">Ir</a></div>
    <div class="cinta-item cinta-dueno"><span>💰 Dueño</span> <a href="/dueno" style="color:#ff6b9d;">Ir</a></div>
    <div class="cinta-item cinta-productos"><span>📦 Productos</span> <a href="/productos" style="color:#ff5c8a;">Ir</a></div>
    <div class="cinta-item cinta-ventas"><span>💵 Ventas</span> <a href="/ventas" style="color:#ff5c8a;">Ir</a></div>
    <div class="cinta-item cinta-reporte"><span>📊 Reporte</span> <a href="/reporte" style="color:#ff5c8a;">Ir</a></div>
    <div class="cinta-item cinta-config"><span>⚙️ Config</span> <span style="color:#4eff88;">Aquí estás</span></div>
    <div class="cinta-item cinta-usuarios"><span>👥 Usuarios</span> <a href="/usuarios" style="color:#ffcc00;">Ir</a></div>
    <div class="cinta-item cinta-salir"><span>🚪 Salir</span> <a href="/logout" style="color:#ff4444;">Salir</a></div>

  </details>

  <details>
    <summary>🛠️ Herramientas Admin Avanzadas ▼</summary>
    <div class="cinta-item"><span>Respaldar BD</span><a href="/admin/backup">Ejecutar</a></div>
    <div class="cinta-item"><span>Limpiar Tickets</span><a href="/admin/limpiar_tickets">Limpiar</a></div>
    <div class="cinta-item"><span>Reporte PDF</span><a href="/reporte">PDF</a></div>
  </details>

  <button class="btn-guardar">💾 GUARDAR CONFIGURACIÓN</button>
</div>
"""