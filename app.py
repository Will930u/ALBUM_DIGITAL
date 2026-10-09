import os
import hmac
import hashlib
import urllib.parse
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# Variables de entorno configuradas en Render
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")

# Cliente Supabase
supabase_client: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error al inicializar Supabase: {e}")

def send_telegram_message(chat_id: str, text: str):
    """Auxiliar para enviar notificaciones a Telegram."""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.ok
    except Exception as e:
        print(f"Error notificando a Telegram: {e}")
        return False

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "online",
        "service": "Álbum Digital Backend",
        "version": "2.0.0"
    }), 200

@app.route("/api/bcv", methods=["GET"])
def get_bcv_rate():
    try:
        res = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=5)
        if res.ok:
            data = res.json()
            return jsonify({"status": "success", "promedio": data.get("promedio", 0)}), 200
        return jsonify({"status": "error", "message": "No se pudo obtener la tasa BCV"}), 502
    except Exception as e:
        return jsonify({"status": "error", "details": str(e)}), 500

@app.route("/api/sincronizar-usuario", methods=["POST"])
def sincronizar_usuario():
    data = request.get_json(silent=True) or {}
    usuario_id = data.get("usuario_id")
    nombre = data.get("nombre", "Usuario Telegram")

    if not usuario_id:
        return jsonify({"status": "error", "message": "Falta usuario_id"}), 400

    if supabase_client:
        try:
            res = supabase_client.table("usuarios").upsert({
                "id": str(usuario_id),
                "nombre": str(nombre)
            }).execute()
            return jsonify({"status": "success", "data": res.data}), 200
        except Exception as e:
            return jsonify({"status": "error", "details": str(e)}), 500

    return jsonify({"status": "warning", "message": "Supabase no configurado"}), 200

@app.route("/api/notificar-compra", methods=["POST"])
def notificar_compra():
    data = request.get_json(silent=True) or {}
    usuario_id = data.get("usuario_id")
    barajitas_qty = data.get("barajitas_qty")
    monto_bs = data.get("monto_bs")
    monto_usd = data.get("monto_usd", 0.0)
    referencia = data.get("referencia")

    if not all([usuario_id, barajitas_qty, monto_bs, referencia]):
        return jsonify({"status": "error", "message": "Campos incompletos"}), 400

    if supabase_client:
        try:
            # 1. Asegurar registro en usuarios
            supabase_client.table("usuarios").upsert({"id": str(usuario_id)}).execute()
            
            # 2. Insertar en la tabla real de Supabase: compras_barajitas
            supabase_client.table("compras_barajitas").insert({
                "usuario_id": str(usuario_id),
                "barajitas_qty": int(barajitas_qty),
                "monto_bs": float(monto_bs),
                "monto_usd": float(monto_usd),
                "referencia": str(referencia),
                "estado": "pendiente"
            }).execute()
        except Exception as e:
            print(f"Error guardando compra en Supabase: {e}")

    mensaje = (
        f"🛒 *NUEVA SOLICITUD DE COMPRA*\n\n"
        f"👤 *Usuario:* `{usuario_id}`\n"
        f"🎴 *Barajitas:* {barajitas_qty}\n"
        f"💰 *Monto:* Bs. {float(monto_bs):.2f} (${float(monto_usd):.2f})\n"
        f"🔢 *Referencia:* `{referencia}`"
    )

    sent = send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, mensaje)
    return jsonify({"status": "success", "telegram_sent": sent}), 200

@app.route("/api/notificar-retiro", methods=["POST"])
def notificar_retiro():
    data = request.get_json(silent=True) or {}
    usuario_id = data.get("usuario_id")
    tipo = data.get("tipo", "hito_parcial")
    milestone = data.get("milestone", 0)
    monto_bs = data.get("monto_bs")
    monto_usd = data.get("monto_usd")
    datos_pago = data.get("datos_pago")

    if not all([usuario_id, monto_bs, monto_usd, datos_pago]):
        return jsonify({"status": "error", "message": "Campos incompletos"}), 400

    if supabase_client:
        try:
            # Insertar en la tabla real de Supabase: pagos_pendientes
            supabase_client.table("pagos_pendientes").insert({
                "usuario_id": str(usuario_id),
                "tipo": str(tipo),
                "milestone": int(milestone),
                "monto_bs": float(monto_bs),
                "monto_usd": float(monto_usd),
                "datos_pago": str(datos_pago),
                "estado": "pendiente"
            }).execute()
        except Exception as e:
            print(f"Error registrando retiro en Supabase: {e}")

    if tipo == "liquidacion_total":
        mensaje = (
            f"🔴 *SOLICITUD DE LIQUIDACIÓN TOTAL*\n\n"
            f"👤 *Usuario:* `{usuario_id}`\n"
            f"💰 *Monto Total:* Bs. {float(monto_bs):.2f} (${float(monto_usd):.2f} USD)\n"
            f"🏦 *Pago Móvil:* {datos_pago}\n"
            f"⚠️ *Acción:* Vaciar álbum al aprobar."
        )
    else:
        mensaje = (
            f"🏆 *SOLICITUD DE PREMIO HITO ($200)*\n\n"
            f"👤 *Usuario:* `{usuario_id}`\n"
            f"🎯 *Hito:* Barajita #{milestone}\n"
            f"💰 *Premio:* ${monto_usd} USD (Bs. {float(monto_bs):.2f})\n"
            f"🏦 *Pago Móvil:* {datos_pago}"
        )

    sent = send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, mensaje)
    return jsonify({"status": "success", "telegram_sent": sent}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
