import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
# Permitir peticiones CORS desde cualquier origen (incluyendo Telegram WebApp)
CORS(app, resources={r"/*": {"origins": "*"}})

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
    """Auxiliar para enviar notificaciones a Telegram mediante HTML."""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        print("Falta TELEGRAM_BOT_TOKEN o TELEGRAM_ADMIN_CHAT_ID")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if not res.ok:
            print(f"Error Telegram API: {res.status_code} - {res.text}")
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
            return jsonify({"status": "success", "message": "Usuario sincronizado"}), 200
        except Exception as e:
            print(f"Error en sincronizar_usuario: {e}")
            return jsonify({"status": "error", "details": str(e)}), 500

    return jsonify({"status": "warning", "message": "Supabase no configurado en servidor"}), 200

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

    db_saved = False
    if supabase_client:
        try:
            # 1. Asegurar usuario
            try:
                supabase_client.table("usuarios").upsert({"id": str(usuario_id)}).execute()
            except Exception as u_err:
                print(f"Advertencia al asegurar usuario: {u_err}")

            # 2. Insertar en la tabla 'compras'
            supabase_client.table("compras").insert({
                "usuario_id": str(usuario_id),
                "barajitas_qty": int(barajitas_qty),
                "monto_bs": float(monto_bs),
                "monto_usd": float(monto_usd),
                "referencia": str(referencia),
                "estado": "pendiente"
            }).execute()

            # 3. Insertar en 'transacciones'
            try:
                supabase_client.table("transacciones").insert({
                    "usuario_id": str(usuario_id),
                    "barajitas_qty": int(barajitas_qty),
                    "monto_bs": float(monto_bs),
                    "referencia": str(referencia),
                    "estado": "pendiente"
                }).execute()
            except Exception as t_err:
                print(f"Advertencia al insertar transaccion: {t_err}")

            db_saved = True
        except Exception as e:
            print(f"ERROR CRÍTICO AL INSERTAR EN SUPABASE DESDE FLASK: {e}")

    # Mensaje formateado en HTML para evitar fallos de parseo
    mensaje = (
        f"🛒 <b>NUEVA SOLICITUD DE COMPRA</b>\n\n"
        f"👤 <b>Usuario:</b> <code>{usuario_id}</code>\n"
        f"🎴 <b>Barajitas:</b> {barajitas_qty}\n"
        f"💰 <b>Monto:</b> Bs. {float(monto_bs):.2f} (${float(monto_usd):.2f})\n"
        f"🔢 <b>Referencia:</b> <code>{referencia}</code>\n"
        f"💾 <b>Guardado en BD:</b> {'SÍ' if db_saved else 'NO (Revisar Supabase)'}"
    )

    sent = send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, mensaje)
    return jsonify({
        "status": "success", 
        "telegram_sent": sent,
        "db_saved": db_saved
    }), 200

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
            tabla_destino = "retiros_premios" if tipo == "hito_parcial" else "retiros"
            supabase_client.table(tabla_destino).insert({
                "usuario_id": str(usuario_id),
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
            f"🔴 <b>SOLICITUD DE LIQUIDACIÓN TOTAL</b>\n\n"
            f"👤 <b>Usuario:</b> <code>{usuario_id}</code>\n"
            f"💰 <b>Monto Total:</b> Bs. {float(monto_bs):.2f} (${float(monto_usd):.2f} USD)\n"
            f"🏦 <b>Pago Móvil:</b> {datos_pago}"
        )
    else:
        mensaje = (
            f"🏆 <b>SOLICITUD DE PREMIO HITO ($200)</b>\n\n"
            f"👤 <b>Usuario:</b> <code>{usuario_id}</code>\n"
            f"🎯 <b>Hito:</b> Barajita #{milestone}\n"
            f"💰 <b>Premio:</b> ${monto_usd} USD (Bs. {float(monto_bs):.2f})\n"
            f"🏦 <b>Pago Móvil:</b> {datos_pago}"
        )

    sent = send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, mensaje)
    return jsonify({"status": "success", "telegram_sent": sent}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
