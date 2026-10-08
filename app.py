import os
import hmac
import hashlib
import urllib.parse
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
# Habilitar CORS para permitir peticiones desde el frontend en Supabase / GitHub Pages
CORS(app)

# Configuración de Variables de Entorno en Render
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")

# Inicialización del cliente de Supabase
supabase_client: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error al inicializar Supabase: {e}")

def validar_telegram_init_data(init_data_str: str) -> bool:
    """Verifica matemáticamente que los datos provienen de Telegram y no han sido manipulados."""
    if not init_data_str or not TELEGRAM_BOT_TOKEN:
        return False
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data_str))
        received_hash = parsed_data.pop("hash", None)
        if not received_hash:
            return False

        # Ordenar alfabéticamente las claves para recrear la cadena de verificación
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        
        # Generar clave secreta usando HMAC con 'WebAppData' y el Token del Bot
        secret_key = hmac.new(b"WebAppData", TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()
        # Generar hash esperado
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        return hmac.compare_digest(calculated_hash, received_hash)
    except Exception as e:
        print(f"Error en validación de seguridad: {e}")
        return False

def send_telegram_message(chat_id: str, text: str):
    """Función auxiliar para enviar mensajes a Telegram mediante la API oficial."""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.ok
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")
        return False

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "online",
        "service": "Álbum Digital Backend",
        "version": "1.0.0"
    }), 200

@app.route("/api/bcv", methods=["GET"])
def get_bcv_rate():
    """Obtiene la tasa del BCV directamente desde DolarApi para sincronizar con la app."""
    try:
        res = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=5)
        if res.ok:
            data = res.json()
            return jsonify({"status": "success", "promedio": data.get("promedio", 0)}), 200
        return jsonify({"status": "error", "message": "No se pudo obtener la tasa BCV"}), 502
    except Exception as e:
        return jsonify({"status": "error", "details": str(e)}), 500

@app.route("/webhook/telegram", methods=["POST"])
def telegram_webhook():
    """Recibe comandos o mensajes desde el Bot de Telegram."""
    update = request.get_json(silent=True) or {}
    
    if "message" in update:
        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"].get("text", "")

        if text == "/start":
            send_telegram_message(
                chat_id, 
                "🤖 *Bot de Gestión del Álbum Digital*\n\n"
                "Recibirás notificaciones en tiempo real sobre:\n"
                "• Reportes de pago de barajitas\n"
                "• Solicitudes de retiro por hito ($200)\n"
                "• Liquidaciones totales del álbum"
            )
        elif text == "/status":
            send_telegram_message(chat_id, "✅ El sistema backend está operando correctamente en Render.")

    return jsonify({"status": "received"}), 200

@app.route("/api/sincronizar-usuario", methods=["POST"])
def sincronizar_usuario():
    """Valida la firma de Telegram y registra/actualiza al usuario en Supabase al abrir la Mini App."""
    data = request.get_json(silent=True) or {}
    init_data = data.get("initData")
    usuario_id = data.get("usuario_id")
    nombre = data.get("nombre", "Usuario Telegram")

    # Si se envía initData, se verifica la firma de seguridad
    if init_data and not validar_telegram_init_data(init_data):
        return jsonify({"status": "error", "message": "Acceso no autorizado o firma de Telegram inválida"}), 401

    if not usuario_id:
        return jsonify({"status": "error", "message": "Falta el ID del usuario"}), 400

    if supabase_client:
        try:
            # Registra o actualiza en la tabla usuarios
            res = supabase_client.table("usuarios").upsert({
                "id": str(usuario_id),
                "nombre": str(nombre)
            }).execute()
            return jsonify({"status": "success", "data": res.data}), 200
        except Exception as e:
            print(f"Error al guardar usuario en Supabase: {e}")
            return jsonify({"status": "error", "details": str(e)}), 500

    return jsonify({"status": "warning", "message": "Cliente de Supabase no inicializado"}), 200

@app.route("/api/notificar-compra", methods=["POST"])
def notificar_compra():
    """Endpoint para guardar compras en Supabase y notificar al admin por Telegram."""
    data = request.get_json(silent=True) or {}
    
    usuario_id = data.get("usuario_id")
    barajitas_qty = data.get("barajitas_qty")
    monto_bs = data.get("monto_bs")
    monto_usd = data.get("monto_usd")
    referencia = data.get("referencia")

    if not all([usuario_id, barajitas_qty, monto_bs, referencia]):
        return jsonify({"status": "error", "message": "Faltan campos requeridos"}), 400

    if supabase_client:
        try:
            # 1. Asegurar la existencia del usuario en la tabla 'usuarios'
            supabase_client.table("usuarios").upsert({
                "id": str(usuario_id),
                "nombre": data.get("nombre_usuario", f"Usuario {usuario_id}")
            }).execute()

            # 2. Registrar la operacion en la tabla 'transacciones'
            supabase_client.table("transacciones").insert({
                "usuario_id": str(usuario_id),
                "barajitas": int(barajitas_qty),
                "monto": float(monto_bs),
                "referencia": str(referencia),
                "estado": "pendiente"
            }).execute()

            # 3. Registrar el detalle en la tabla 'compras'
            supabase_client.table("compras").insert({
                "usuario_id": str(usuario_id),
                "barajitas_qty": int(barajitas_qty),
                "monto_bs": float(monto_bs),
                "monto_usd": float(monto_usd or 0.0),
                "referencia": str(referencia)
            }).execute()
        except Exception as e:
            print(f"Error guardando compra en Supabase: {e}")

    # 4. Disparar notificacion a Telegram
    mensaje = (
        f"🛒 *NUEVA SOLICITUD DE COMPRA*\n\n"
        f"👤 *Usuario:* `{usuario_id}`\n"
        f"🎴 *Barajitas:* {barajitas_qty}\n"
        f"💰 *Monto:* Bs. {float(monto_bs):.2f} (${float(monto_usd or 0):.2f})\n"
        f"🔢 *Referencia:* `{referencia}`"
    )

    sent = send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, mensaje)
    return jsonify({"status": "success", "telegram_sent": sent}), 200

@app.route("/api/notificar-retiro", methods=["POST"])
def notificar_retiro():
    """Endpoint para registrar y notificar solicitudes de retiro parcial o liquidación total."""
    data = request.get_json(silent=True) or {}
    
    usuario_id = data.get("usuario_id")
    tipo = data.get("tipo", "hito_parcial")
    milestone = data.get("milestone", 0)
    monto_bs = data.get("monto_bs")
    monto_usd = data.get("monto_usd")
    datos_pago = data.get("datos_pago")

    if not all([usuario_id, monto_bs, monto_usd, datos_pago]):
        return jsonify({"status": "error", "message": "Faltan campos requeridos"}), 400

    if supabase_client:
        try:
            tabla_destino = "retiros_premios" if tipo == "hito_parcial" else "retiros"
            supabase_client.table(tabla_destino).insert({
                "usuario_id": str(usuario_id),
                "monto_bs": float(monto_bs),
                "monto_usd": float(monto_usd),
                "datos_pago": str(datos_pago),
                "estado": "pendiente"
            }).execute()
        except Exception as e:
            print(f"Error al registrar retiro en Supabase: {e}")

    if tipo == "liquidacion_total":
        mensaje = (
            f"🔴 *SOLICITUD DE LIQUIDACIÓN TOTAL (VALOR NETO)*\n\n"
            f"👤 *Usuario:* `{usuario_id}`\n"
            f"💰 *Monto Total:* Bs. {float(monto_bs):.2f} (${float(monto_usd):.2f} USD)\n"
            f"🏦 *Pago Móvil:* {datos_pago}\n"
            f"⚠️ *Acción:* Vaciar álbum e ir a cero al aprobar."
        )
    else:
        mensaje = (
            f"💸 *SOLICITUD DE PREMIO HITO ($200)*\n\n"
            f"👤 *Usuario:* `{usuario_id}`\n"
            f"🎴 *Hito:* Barajita #{milestone}\n"
            f"💰 *Premio:* ${monto_usd} USD (Bs. {float(monto_bs):.2f})\n"
            f"🏦 *Pago Móvil:* {datos_pago}"
        )

    sent = send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, mensaje)
    return jsonify({"status": "success", "telegram_sent": sent}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
