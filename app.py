import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Variables de entorno en Render
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")

# URL del Panel Administrador Independiente en GitHub Pages
ADMIN_PANEL_URL = "https://will930u.github.io/ALBUM_DIGITAL/admin.html"

# Cliente Supabase
supabase_client: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error al inicializar Supabase: {e}")

def send_telegram_inline_keyboard(chat_id: str, text: str, reply_markup: dict):
    """Auxiliar para enviar mensajes a Telegram con botones interactivos."""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.ok
    except Exception as e:
        print(f"Error enviando notificación a Telegram: {e}")
        return False

def procesar_aprobacion_compra(referencia, usuario_id, qty, monto_bs):
    """Lógica unificada para abonar el 70% neto en saldo Bs y barajitas al usuario."""
    if not supabase_client:
        return False
    try:
        user_net = float(monto_bs) * 0.70
        # 1. Cambiar estado de la transacción a aprobado
        supabase_client.table("transacciones").update({"estado": "aprobado"}).eq("referencia", str(referencia)).execute()
        
        # 2. Consultar usuario y sumar barajitas y saldo neto
        u_res = supabase_client.table("usuarios").select("*").eq("id", str(usuario_id)).execute()
        if u_res.data:
            curr_qty = u_res.data[0].get("cantidad_barajitas", 0) or 0
            curr_bal = u_res.data[0].get("saldo_bs", 0.0) or 0.0
            supabase_client.table("usuarios").update({
                "cantidad_barajitas": int(curr_qty) + int(qty),
                "saldo_bs": float(curr_bal) + user_net
            }).eq("id", str(usuario_id)).execute()
            return True
    except Exception as e:
        print(f"Error al procesar aprobación de compra: {e}")
    return False

def procesar_rechazo_compra(referencia):
    """Lógica unificada para marcar compra como rechazada."""
    if not supabase_client:
        return False
    try:
        supabase_client.table("transacciones").update({"estado": "rechazado"}).eq("referencia", str(referencia)).execute()
        return True
    except Exception as e:
        print(f"Error al procesar rechazo de compra: {e}")
    return False

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "online", "service": "Backend Álbum Digital Sincronizado", "version": "3.0.0"}), 200

@app.route("/api/bcv", methods=["GET"])
def get_bcv_rate():
    try:
        res = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=5)
        if res.ok:
            data = res.json()
            return jsonify({"status": "success", "promedio": data.get("promedio", 0)}), 200
        return jsonify({"status": "error", "message": "Error al consultar tasa BCV"}), 502
    except Exception as e:
        return jsonify({"status": "error", "details": str(e)}), 500

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    gmail = data.get("gmail")
    banco = data.get("banco")
    cedula = data.get("cedula")
    telefono = data.get("telefono")

    if not all([username, password, gmail, banco, cedula, telefono]):
        return jsonify({"status": "error", "message": "Todos los campos son requeridos"}), 400

    user_id = f"USR-{username.upper()}"

    if supabase_client:
        try:
            try:
                supabase_client.auth.admin.create_user({
                    "email": gmail,
                    "password": password,
                    "email_confirm": True
                })
            except Exception as auth_admin_err:
                print(f"Aviso en Admin Auth: {auth_admin_err}")

            res = supabase_client.table("usuarios").insert({
                "id": user_id,
                "nombre": username,
                "username": username,
                "password_hash": password,
                "gmail": gmail,
                "banco": banco,
                "cedula": cedula,
                "telefono": telefono,
                "saldo_usd": 0.0,
                "cantidad_barajitas": 0,
                "saldo_bs": 0.0
            }).execute()

            user_data = res.data[0] if res.data else {"id": user_id, "username": username}
            return jsonify({"status": "success", "user": user_data}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": "El usuario o datos ya existen", "details": str(e)}), 400

    return jsonify({"status": "error", "message": "Base de datos no disponible"}), 500

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"status": "error", "message": "Faltan credenciales"}), 400

    if supabase_client:
        try:
            res = supabase_client.table("usuarios").select("*").eq("username", username).eq("password_hash", password).execute()
            if res.data and len(res.data) > 0:
                return jsonify({"status": "success", "user": res.data[0]}), 200
            return jsonify({"status": "error", "message": "Usuario o contraseña incorrectos"}), 401
        except Exception as e:
            return jsonify({"status": "error", "details": str(e)}), 500

    return jsonify({"status": "error", "message": "Base de datos no disponible"}), 500

@app.route("/api/notificar-compra", methods=["POST"])
def notificar_compra():
    data = request.get_json(silent=True) or {}
    usuario_id = data.get("usuario_id")
    barajitas_qty = data.get("barajitas_qty")
    monto_bs = data.get("monto_bs")
    monto_usd = data.get("monto_usd", 0.0)
    banco_emisor = data.get("banco_emisor", "N/A")
    telefono_emisor = data.get("telefono_emisor", "N/A")
    referencia = data.get("referencia")

    if not all([usuario_id, barajitas_qty, monto_bs, referencia]):
        return jsonify({"status": "error", "message": "Campos incompletos"}), 400

    tx_id = None
    if supabase_client:
        try:
            res = supabase_client.table("transacciones").insert({
                "usuario_id": str(usuario_id),
                "barajitas_qty": int(barajitas_qty),
                "monto_bs": float(monto_bs),
                "monto_usd": float(monto_usd),
                "referencia": str(referencia),
                "estado": "pendiente"
            }).execute()
            if res.data:
                tx_id = res.data[0]["id"]
        except Exception as e:
            print(f"Error insertando transacción: {e}")

    text = (
        f"🛒 <b>NUEVA SOLICITUD DE COMPRA</b>\n\n"
        f"👤 <b>Usuario ID:</b> <code>{usuario_id}</code>\n"
        f"📦 <b>Barajitas:</b> {barajitas_qty}\n"
        f"💰 <b>Monto:</b> Bs. {float(monto_bs):.2f} (${float(monto_usd):.2f})\n"
        f"🏦 <b>Banco Emisor:</b> {banco_emisor}\n"
        f"📱 <b>Teléfono Emisor:</b> {telefono_emisor}\n"
        f"🔢 <b>Referencia:</b> <code>{referencia}</code>\n"
        f"📌 <b>Estado:</b> PENDIENTE DE APROBACIÓN"
    )

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "🟢 APROBAR COMPRA", "callback_data": f"aprob_compra:{referencia}:{usuario_id}:{barajitas_qty}:{monto_bs}"},
                {"text": "🔴 RECHAZAR", "callback_data": f"rech_compra:{referencia}"}
            ],
            [
                {"text": "⚙️ ABRIR PANEL DE ADMINISTRACIÓN", "url": ADMIN_PANEL_URL}
            ]
        ]
    }

    sent = send_telegram_inline_keyboard(TELEGRAM_ADMIN_CHAT_ID, text, reply_markup)
    return jsonify({"status": "success", "telegram_sent": sent, "tx_id": tx_id}), 200

@app.route("/api/notificar-retiro", methods=["POST"])
def notificar_retiro():
    data = request.get_json(silent=True) or {}
    usuario_id = data.get("usuario_id")
    milestone = data.get("milestone", 0)
    monto_bs = data.get("monto_bs")
    monto_usd = data.get("monto_usd")
    datos_pago = data.get("datos_pago")

    if not all([usuario_id, monto_bs, monto_usd, datos_pago]):
        return jsonify({"status": "error", "message": "Campos incompletos"}), 400

    retiro_id = None
    if supabase_client:
        try:
            res = supabase_client.table("retiros_premios").insert({
                "usuario_id": str(usuario_id),
                "milestone": int(milestone),
                "monto_bs": float(monto_bs),
                "monto_usd": float(monto_usd),
                "datos_pago": str(datos_pago),
                "estado": "pendiente"
            }).execute()
            if res.data:
                retiro_id = res.data[0]["id"]
        except Exception as e:
            print(f"Error registrando retiro: {e}")

    text = (
        f"🎁 <b>SOLICITUD DE RETIRO / PREMIO</b>\n\n"
        f"👤 <b>Usuario ID:</b> <code>{usuario_id}</code>\n"
        f"🎯 <b>Hito:</b> Barajita #{milestone}\n"
        f"💰 <b>Premio:</b> ${monto_usd} USD (Bs. {float(monto_bs):.2f})\n"
        f"🏦 <b>Pago Móvil:</b> {datos_pago}\n"
        f"📌 <b>Estado:</b> PENDIENTE DE VERIFICACIÓN"
    )

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "🟢 CONFIRMAR PAGO REALIZADO", "callback_data": f"aprob_retiro:{retiro_id}"},
                {"text": "🔴 RECHAZAR", "callback_data": f"rech_retiro:{retiro_id}"}
            ],
            [
                {"text": "⚙️ ABRIR PANEL DE ADMINISTRACIÓN", "url": ADMIN_PANEL_URL}
            ]
        ]
    }

    sent = send_telegram_inline_keyboard(TELEGRAM_ADMIN_CHAT_ID, text, reply_markup)
    return jsonify({"status": "success", "telegram_sent": sent}), 200

@app.route("/webhook/telegram", methods=["POST"])
def webhook_telegram():
    data = request.get_json(silent=True) or {}

    if "message" in data:
        msg = data["message"]
        text_received = msg.get("text", "")
        chat_id = msg["chat"]["id"]

        if text_received == "/admin":
            admin_msg = (
                "🔐 <b>ACCESO AL PANEL ADMINISTRATIVO</b>\n\n"
                "Presiona el botón de abajo para gestionar compras, retiros de premios, "
                "datos de Pago Móvil, logo de la app y carga masiva de barajitas."
            )
            admin_markup = {
                "inline_keyboard": [
                    [
                        {"text": "⚙️ ABRIR PANEL ADMIN", "url": ADMIN_PANEL_URL}
                    ]
                ]
            }
            send_telegram_inline_keyboard(chat_id, admin_msg, admin_markup)
            return jsonify({"status": "ok"}), 200

    if "callback_query" in data:
        callback = data["callback_query"]
        callback_id = callback["id"]
        callback_data = callback["data"]
        message = callback["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]

        action_parts = callback_data.split(":")
        action = action_parts[0]

        nuevo_texto = message.get("text", "")

        if action == "aprob_compra":
            ref = action_parts[1]
            u_id = action_parts[2]
            qty = int(action_parts[3])
            monto_bs = float(action_parts[4])

            procesar_aprobacion_compra(ref, u_id, qty, monto_bs)
            nuevo_texto += "\n\n✅ <b>COMPRA APROBADA Y ABONADA CON ÉXITO</b>"

        elif action == "rech_compra":
            ref = action_parts[1]
            procesar_rechazo_compra(ref)
            nuevo_texto += "\n\n🔴 <b>COMPRA RECHAZADA</b>"

        elif action == "aprob_retiro":
            ret_id = action_parts[1]
            if supabase_client and ret_id:
                supabase_client.table("retiros_premios").update({"estado": "aprobado"}).eq("id", ret_id).execute()
            nuevo_texto += "\n\n✅ <b>RETIRO MARCADO COMO PAGADO CON ÉXITO</b>"

        elif action == "rech_retiro":
            ret_id = action_parts[1]
            if supabase_client and ret_id:
                supabase_client.table("retiros_premios").update({"estado": "rechazado"}).eq("id", ret_id).execute()
            nuevo_texto += "\n\n🔴 <b>RETIRO RECHAZADO</b>"

        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": callback_id})

        nuevo_markup = {
            "inline_keyboard": [
                [
                    {"text": "⚙️ ABRIR PANEL DE ADMINISTRACIÓN", "url": ADMIN_PANEL_URL}
                ]
            ]
        }

        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": nuevo_texto,
            "parse_mode": "HTML",
            "reply_markup": nuevo_markup
        })

    return jsonify({"status": "ok"}), 200

@app.route("/api/admin/procesar-compra", methods=["POST"])
def admin_procesar_compra():
    data = request.get_json(silent=True) or {}
    referencia = data.get("referencia")
    usuario_id = data.get("usuario_id")
    barajitas_qty = data.get("barajitas_qty", 0)
    monto_bs = data.get("monto_bs", 0.0)
    estado = data.get("estado")

    if not referencia or not estado:
        return jsonify({"status": "error", "message": "Datos faltantes"}), 400

    if estado == "aprobado":
        ok = procesar_aprobacion_compra(referencia, usuario_id, barajitas_qty, monto_bs)
    else:
        ok = procesar_rechazo_compra(referencia)

    if ok:
        return jsonify({"status": "success", "message": f"Compra {estado} correctamente"}), 200
    return jsonify({"status": "error", "message": "Error al actualizar la base de datos"}), 500

@app.route("/api/update-password", methods=["POST"])
def update_password():
    data = request.get_json(silent=True) or {}
    gmail = data.get("gmail")
    new_password = data.get("new_password")

    if not gmail or not new_password:
        return jsonify({"status": "error", "message": "Datos incompletos"}), 400

    if supabase_client:
        try:
            supabase_client.table("usuarios").update({
                "password_hash": new_password
            }).eq("gmail", gmail).execute()
            return jsonify({"status": "success", "message": "Contraseña actualizada en la tabla usuarios"}), 200
        except Exception as e:
            return jsonify({"status": "error", "details": str(e)}), 500

    return jsonify({"status": "error", "message": "Base de datos no disponible"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
