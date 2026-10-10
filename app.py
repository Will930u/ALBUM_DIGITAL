import os
import requests
import threading
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
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        return res.json() if res.ok else None
    except Exception as e:
        print(f"Error enviando notificación a Telegram: {e}")
        return None

def procesar_aprobacion_compra(referencia, usuario_id, qty, monto_bs):
    if not supabase_client:
        return False
    try:
        user_net = float(monto_bs) * 0.70
        qty_int = int(qty)
        
        supabase_client.table("transacciones").update({"estado": "aprobado"}).eq("referencia", str(referencia)).execute()
        u_res = supabase_client.table("usuarios").select("cantidad_barajitas, saldo_bs").eq("id", str(usuario_id)).execute()
        
        if u_res.data and len(u_res.data) > 0:
            current_data = u_res.data[0]
            curr_qty = int(current_data.get("cantidad_barajitas") or 0)
            curr_bal = float(current_data.get("saldo_bs") or 0.0)
            
            nuevas_barajitas = curr_qty + qty_int
            nuevo_saldo = curr_bal + user_net

            supabase_client.table("usuarios").update({
                "cantidad_barajitas": nuevas_barajitas,
                "saldo_bs": nuevo_saldo
            }).eq("id", str(usuario_id)).execute()
            return True
    except Exception as e:
        print(f"Error crítico procesando aprobación: {e}")
    return False

def procesar_rechazo_compra(referencia):
    if not supabase_client:
        return False
    try:
        supabase_client.table("transacciones").update({"estado": "rechazado"}).eq("referencia", str(referencia)).execute()
        return True
    except Exception as e:
        print(f"Error procesando rechazo: {e}")
    return False

def TareaSecundariaTelegram(callback_id, chat_id, message_id, callback_data, original_text):
    """Procesa la BD y edita el mensaje de Telegram en segundo plano sin bloquear a Telegram."""
    action_parts = callback_data.split(":")
    action = action_parts[0]
    nuevo_texto = original_text

    if action == "aprob_compra" and len(action_parts) >= 5:
        ref = action_parts[1]
        u_id = action_parts[2]
        qty = int(action_parts[3])
        monto_bs = float(action_parts[4])

        ok = procesar_aprobacion_compra(ref, u_id, qty, monto_bs)
        if ok:
            nuevo_texto += "\n\n✅ <b>COMPRA APROBADA Y ABONADA DESDE TELEGRAM</b>"
        else:
            nuevo_texto += "\n\n⚠️ <b>COMPRA PROCESADA CON ADVERTENCIA</b>"

    elif action == "rech_compra" and len(action_parts) >= 2:
        ref = action_parts[1]
        procesar_rechazo_compra(ref)
        nuevo_texto += "\n\n🔴 <b>COMPRA RECHAZADA DESDE TELEGRAM</b>"

    # Editar el mensaje final removiendo los botones de acción
    nuevo_markup = {
        "inline_keyboard": [
            [{"text": "⚙️ ABRIR PANEL DE ADMINISTRACIÓN", "url": ADMIN_PANEL_URL}]
        ]
    }

    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": nuevo_texto,
            "parse_mode": "HTML",
            "reply_markup": nuevo_markup
        }, timeout=5)
    except Exception as e:
        print(f"Error editando mensaje en Telegram: {e}")

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "online", "service": "Backend Asíncrono"}), 200

@app.route("/api/bcv", methods=["GET"])
def get_bcv_rate():
    try:
        res = requests.get("https://ve.dolarapi.com/v1/dolares/oficial", timeout=5)
        if res.ok:
            return jsonify({"status": "success", "promedio": res.json().get("promedio", 0)}), 200
        return jsonify({"status": "error", "message": "Error al consultar BCV"}), 502
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
        return jsonify({"status": "error", "message": "Campos requeridos"}), 400

    user_id = f"USR-{username.upper()}"

    if supabase_client:
        try:
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
            return jsonify({"status": "error", "message": "Error registrando usuario", "details": str(e)}), 400

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
            return jsonify({"status": "error", "message": "Usuario o clave incorrectos"}), 401
        except Exception as e:
            return jsonify({"status": "error", "details": str(e)}), 500

    return jsonify({"status": "error", "message": "BD no disponible"}), 500

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

    tg_response = send_telegram_inline_keyboard(TELEGRAM_ADMIN_CHAT_ID, text, reply_markup)
    msg_id = str(tg_response["result"]["message_id"]) if (tg_response and tg_response.get("ok")) else None

    if supabase_client:
        try:
            supabase_client.table("transacciones").insert({
                "usuario_id": str(usuario_id),
                "barajitas_qty": int(barajitas_qty),
                "monto_bs": float(monto_bs),
                "monto_usd": float(monto_usd),
                "referencia": str(referencia),
                "banco_emisor": str(banco_emisor),
                "telefono_emisor": str(telefono_emisor),
                "estado": "pendiente",
                "telegram_chat_id": str(TELEGRAM_ADMIN_CHAT_ID),
                "telegram_message_id": msg_id
            }).execute()
        except Exception as e:
            print(f"Error insertando transacción: {e}")

    return jsonify({"status": "success"}), 200

@app.route("/webhook/telegram", methods=["POST"])
def webhook_telegram():
    data = request.get_json(silent=True) or {}

    if "callback_query" in data:
        callback = data["callback_query"]
        callback_id = callback["id"]
        callback_data = callback["data"]
        message = callback["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]
        original_text = message.get("text", "")

        # 1. Responder de inmediato a Telegram (0.01 segundos)
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", 
                json={"callback_query_id": callback_id, "text": "⚡ Procesando..."},
                timeout=2
            )
        except Exception as e:
            print(f"Aviso answerCallbackQuery: {e}")

        # 2. Ejecutar la lógica pesada de Supabase en un Hilo Secundario Asíncrono
        hilo = threading.Thread(
            target=TareaSecundariaTelegram,
            args=(callback_id, chat_id, message_id, callback_data, original_text)
        )
        hilo.start()

        # 3. Retornar OK inmediatamente a Telegram
        return jsonify({"status": "ok"}), 200

    return jsonify({"status": "ok"}), 200

@app.route("/api/admin/procesar-compra", methods=["POST"])
def admin_procesar_compra():
    data = request.get_json(silent=True) or {}
    referencia = str(data.get("referencia", "")).strip()
    usuario_id = data.get("usuario_id")
    barajitas_qty = data.get("barajitas_qty", 0)
    monto_bs = data.get("monto_bs", 0.0)
    estado = str(data.get("estado", "")).lower()

    if not referencia or estado not in ["aprobado", "rechazado"]:
        return jsonify({"status": "error", "message": "Datos faltantes"}), 400

    tx_data = {}
    if supabase_client:
        try:
            tx_res = supabase_client.table("transacciones").select("*").eq("referencia", referencia).execute()
            if tx_res.data:
                tx_data = tx_res.data[0]
        except Exception as e:
            print(f"Error consultando transacción: {e}")

    chat_id = tx_data.get("telegram_chat_id") or TELEGRAM_ADMIN_CHAT_ID
    msg_id = tx_data.get("telegram_message_id")

    if estado == "aprobado":
        ok = procesar_aprobacion_compra(referencia, usuario_id, barajitas_qty, monto_bs)
    else:
        ok = procesar_rechazo_compra(referencia)

    if msg_id and chat_id:
        estado_texto = "✅ <b>COMPRA APROBADA DESDE EL PANEL ADMIN</b>" if estado == "aprobado" else "🔴 <b>COMPRA RECHAZADA DESDE EL PANEL ADMIN</b>"
        texto_actualizado = f"🛒 <b>SOLICITUD PROCESADA</b>\n\n👤 <b>Usuario ID:</b> <code>{usuario_id}</code>\n🔢 <b>Referencia:</b> <code>{referencia}</code>\n\n{estado_texto}"

        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", json={
                "chat_id": chat_id,
                "message_id": int(msg_id),
                "text": texto_actualizado,
                "parse_mode": "HTML",
                "reply_markup": {"inline_keyboard": [[{"text": "⚙️ ABRIR PANEL DE ADMINISTRACIÓN", "url": ADMIN_PANEL_URL}]]}
            }, timeout=4)
        except Exception as e:
            print(f"Error editando mensaje: {e}")

    if ok:
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
