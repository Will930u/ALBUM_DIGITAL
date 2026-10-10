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
    """Auxiliar para enviar mensajes a Telegram devolviendo el objeto JSON de respuesta."""
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
        res = requests.post(url, json=payload, timeout=10)
        return res.json() if res.ok else None
    except Exception as e:
        print(f"Error enviando notificación a Telegram: {e}")
        return None

def procesar_aprobacion_compra(referencia, usuario_id, qty, monto_bs):
    """Lógica unificada y segura para abonar el 70% neto en saldo Bs y barajitas al usuario."""
    if not supabase_client:
        return False
    try:
        user_net = float(monto_bs) * 0.70
        qty_int = int(qty)
        
        # 1. Cambiar estado de la transacción a aprobado
        supabase_client.table("transacciones").update({"estado": "aprobado"}).eq("referencia", str(referencia)).execute()
        
        # 2. Consultar usuario actual para obtener sus valores previos reales
        u_res = supabase_client.table("usuarios").select("cantidad_barajitas, saldo_bs").eq("id", str(usuario_id)).execute()
        
        if u_res.data and len(u_res.data) > 0:
            current_data = u_res.data[0]
            curr_qty = int(current_data.get("cantidad_barajitas") or 0)
            curr_bal = float(current_data.get("saldo_bs") or 0.0)
            
            nuevas_barajitas = curr_qty + qty_int
            nuevo_saldo = curr_bal + user_net

            # 3. Actualizar con los valores sumados
            supabase_client.table("usuarios").update({
                "cantidad_barajitas": nuevas_barajitas,
                "saldo_bs": nuevo_saldo
            }).eq("id", str(usuario_id)).execute()
            return True
        else:
            print(f"Usuario {usuario_id} no encontrado en la tabla public.usuarios")
    except Exception as e:
        print(f"Error crítico al procesar aprobación de compra: {e}")
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

    # Enviar a Telegram y obtener ID de mensaje
    tg_response = send_telegram_inline_keyboard(TELEGRAM_ADMIN_CHAT_ID, text, reply_markup)
    msg_id = None
    if tg_response and tg_response.get("ok"):
        msg_id = str(tg_response["result"]["message_id"])

    tx_id = None
    if supabase_client:
        try:
            res = supabase_client.table("transacciones").insert({
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
            if res.data:
                tx_id = res.data[0]["id"]
        except Exception as e:
            print(f"Error insertando transacción: {e}")

    return jsonify({"status": "success", "telegram_sent": bool(msg_id), "tx_id": tx_id}), 200

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
    return jsonify({"status": "success", "telegram_sent": bool(sent)}), 200

@app.route("/webhook/telegram", methods=["POST"])
def webhook_telegram():
    data = request.get_json(silent=True) or {}

    # 1. Procesar comando /admin
    if "message" in data:
        msg = data["message"]
        text_received = msg.get("text", "")
        chat_id = msg["chat"]["id"]

        if text_received == "/admin":
            admin_msg = (
                "🔐 <b>ACCESO AL PANEL ADMINISTRATIVO</b>\n\n"
                "Presiona el botón de abajo para gestionar compras, retiros de premios, "
                "datos de Pago Móvil, logo y carga masiva de barajitas."
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

    # 2. Procesar Clics en Botones (Callback Queries) de forma ultrarrápida
    if "callback_query" in data:
        callback = data["callback_query"]
        callback_id = callback["id"]
        callback_data = callback["data"]
        message = callback["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]

        # === PASO CRÍTICO: Responder DE INMEDIATO a Telegram para matar el Timeout ===
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", 
                json={"callback_query_id": callback_id, "text": "⚡ Procesando solicitud..."},
                timeout=1
            )
        except Exception as e:
            print(f"Aviso answerCallbackQuery: {e}")

        # Continuar con el procesamiento en segundo plano
        action_parts = callback_data.split(":")
        action = action_parts[0]
        nuevo_texto = message.get("text", "")

        if action == "aprob_compra" and len(action_parts) >= 5:
            ref = action_parts[1]
            u_id = action_parts[2]
            qty = int(action_parts[3])
            monto_bs = float(action_parts[4])

            ok = procesar_aprobacion_compra(ref, u_id, qty, monto_bs)
            if ok:
                nuevo_texto += "\n\n✅ <b>COMPRA APROBADA Y ABONADA DESDE TELEGRAM</b>"
            else:
                nuevo_texto += "\n\n⚠️ <b>COMPRA PROCESADA (VERIFICAR EN BD)</b>"

        elif action == "rech_compra" and len(action_parts) >= 2:
            ref = action_parts[1]
            procesar_rechazo_compra(ref)
            nuevo_texto += "\n\n🔴 <b>COMPRA RECHAZADA DESDE TELEGRAM</b>"

        elif action == "aprob_retiro" and len(action_parts) >= 2:
            ret_id = action_parts[1]
            if supabase_client and ret_id:
                supabase_client.table("retiros_premios").update({"estado": "aprobado"}).eq("id", ret_id).execute()
            nuevo_texto += "\n\n✅ <b>RETIRO MARCADO COMO PAGADO CON ÉXITO</b>"

        elif action == "rech_retiro" and len(action_parts) >= 2:
            ret_id = action_parts[1]
            if supabase_client and ret_id:
                supabase_client.table("retiros_premios").update({"estado": "rechazado"}).eq("id", ret_id).execute()
            nuevo_texto += "\n\n🔴 <b>RETIRO RECHAZADO DESDE TELEGRAM</b>"

        # Remover los botones de 'Aprobar/Rechazar' y dejar solo el enlace al Admin Web
        nuevo_markup = {
            "inline_keyboard": [
                [
                    {"text": "⚙️ ABRIR PANEL DE ADMINISTRACIÓN", "url": ADMIN_PANEL_URL}
                ]
            ]
        }

        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": nuevo_texto,
                "parse_mode": "HTML",
                "reply_markup": nuevo_markup
            }, timeout=4)
        except Exception as e:
            print(f"Error editando mensaje en Telegram: {e}")

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
        return jsonify({"status": "error", "message": "Datos faltantes o inválidos"}), 400

    # 1. Obtener la transacción previa para rescatar message_id y chat_id de Telegram
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

    # 2. Procesar aprobación o rechazo en la BD
    if estado == "aprobado":
        ok = procesar_aprobacion_compra(referencia, usuario_id, barajitas_qty, monto_bs)
    else:
        ok = procesar_rechazo_compra(referencia)

    # 3. Editar mensaje en Telegram para notificar la aprobación/rechazo efectuada desde el panel
    if msg_id and chat_id:
        estado_texto = "✅ <b>COMPRA APROBADA Y ABONADA DESDE EL PANEL ADMIN</b>" if estado == "aprobado" else "🔴 <b>COMPRA RECHAZADA DESDE EL PANEL ADMIN</b>"
        
        texto_actualizado = (
            f"🛒 <b>SOLICITUD DE COMPRA PROCESADA</b>\n\n"
            f"👤 <b>Usuario ID:</b> <code>{usuario_id}</code>\n"
            f"🔢 <b>Referencia:</b> <code>{referencia}</code>\n"
            f"📦 <b>Barajitas:</b> {barajitas_qty}\n"
            f"💰 <b>Monto:</b> Bs. {float(monto_bs):.2f}\n\n"
            f"{estado_texto}"
        )

        markup_sin_botones = {
            "inline_keyboard": [
                [{"text": "⚙️ ABRIR PANEL DE ADMINISTRACIÓN", "url": ADMIN_PANEL_URL}]
            ]
        }

        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", json={
                "chat_id": chat_id,
                "message_id": int(msg_id),
                "text": texto_actualizado,
                "parse_mode": "HTML",
                "reply_markup": markup_sin_botones
            }, timeout=4)
        except Exception as e:
            print(f"Error actualizando Telegram desde Admin Web: {e}")

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
