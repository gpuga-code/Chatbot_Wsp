from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import re
import openai
from datetime import datetime
import os
import json

app = Flask(__name__)

# ===== Historial de conversaciones por usuario =====
conversaciones = {}

# ===== Definir scope =====
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# ===== Leer el JSON desde la variable de entorno =====
service_json = os.environ.get('GOOGLE_JSON_PATH')
if not service_json:
    raise ValueError("La variable de entorno GOOGLE_JSON_PATH no está definida")

# ===== Convertir el contenido a un diccionario =====
creds_dict = json.loads(service_json)

# ===== Crear credenciales desde el diccionario =====
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

# ===== Configuración OpenAI =====
openai.api_key = os.environ.get("OPENAI_API_KEY")  

# ===== Conectar con Google Sheets =====
client = gspread.authorize(creds)
sheet = client.open("Reporte SII 09-25").sheet1

# ===== Configuración Twilio =====
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")


TWILIO_NUMBER = "whatsapp:+14155238886"  # Número sandbox o tu número de Twilio
client_twilio = Client(ACCOUNT_SID, AUTH_TOKEN)

def enviar_respuesta(numero, texto):
    """Enviar respuesta por WhatsApp usando Twilio API"""
    try:
        message = client_twilio.messages.create(
            from_=TWILIO_NUMBER,
            body=texto,
            to=f"whatsapp:{numero}"
        )
        print("📤 Respuesta enviada:", message.sid)
    except Exception as e:
        print(f"❌ Error enviando mensaje: {str(e)}")

# ===== Diccionario de meses =====
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}

# ===== Funciones auxiliares =====
def obtener_datos_completos():
    return sheet.get_all_records()

def calcular_totales_mes(mes=None, año=None):
    registros = obtener_datos_completos()
    total_ventas = total_iva = total_neto = 0
    contador_facturas = 0

    for fila in registros:
        fecha_str = fila.get("Fecha Docto") or fila.get("Fecha", "")
        if not fecha_str:
            continue

        fecha = None
        for fmt in ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                fecha = datetime.strptime(fecha_str, fmt)
                break
            except:
                continue
        if not fecha:
            continue

        if mes and fecha.month != mes:
            continue
        if año and fecha.year != año:
            continue

        try:
            monto_total = float(str(fila.get("Monto total", 0)).replace(".", "").replace(",", ""))
            iva = float(str(fila.get("Monto IVA", 0)).replace(".", "").replace(",", ""))
            monto_neto = float(str(fila.get("Monto neto", 0)).replace(".", "").replace(",", ""))
        except:
            continue

        total_ventas += monto_total
        total_iva += iva
        total_neto += monto_neto
        contador_facturas += 1

    return {
        "total_ventas": total_ventas,
        "total_iva": total_iva,
        "total_neto": total_neto,
        "cantidad_facturas": contador_facturas
    }

def calcular_totales_año(año):
    return calcular_totales_mes(año=año)

def buscar_por_cliente(nombre_cliente):
    registros = obtener_datos_completos()
    facturas_cliente = []
    total_cliente = 0

    for fila in registros:
        razon_social = str(fila.get("Razón Social", "")).lower()
        if nombre_cliente.lower() in razon_social:
            facturas_cliente.append(fila)
            try:
                monto = float(str(fila.get("Monto total", 0)).replace(".", "").replace(",", ""))
                total_cliente += monto
            except:
                continue

    return facturas_cliente, total_cliente

def obtener_ultima_factura():
    registros = obtener_datos_completos()
    if not registros:
        return None
    registros_ordenados = sorted(registros, key=lambda x: x.get("Fecha Docto", ""), reverse=True)
    return registros_ordenados[0]

def contar_facturas_mes(mes, año=None):
    totales = calcular_totales_mes(mes=mes, año=año)
    return totales["cantidad_facturas"]

def tipos_documentos():
    registros = obtener_datos_completos()
    tipos = set(fila.get("Tipo Doc") for fila in registros if fila.get("Tipo Doc"))
    return tipos

def buscar_factura(folio):
    registros = obtener_datos_completos()
    for fila in registros:
        if str(fila.get("Folio")) == str(folio):
            respuesta = [f"📑 Factura encontrada (Folio {fila['Folio']}):\n"]
            for key, value in fila.items():
                if value not in ["", None, 0, "0"]:
                    respuesta.append(f"• {key}: {value}")
            return "\n".join(respuesta)
    return "⚠️ Factura no encontrada"

def obtener_resumen_datos():
    registros = obtener_datos_completos()
    if not registros:
        return "No hay datos disponibles"
    total_facturas = len(registros)
    columnas = list(registros[0].keys())
    totales = calcular_totales_mes()
    resumen = f"""
Resumen de datos disponibles:
- Total de facturas: {total_facturas}
- Columnas disponibles: {', '.join(columnas)}
- Total de ventas: ${totales['total_ventas']:,.0f}
- Total IVA: ${totales['total_iva']:,.0f}
- Total neto: ${totales['total_neto']:,.0f}
"""
    return resumen

# ===== ChatGPT =====
def consultar_chatgpt(mensaje_usuario, datos_contexto="", numero_usuario=None):
    if numero_usuario not in conversaciones:
        conversaciones[numero_usuario] = []

    historial = conversaciones[numero_usuario]
    
    system_prompt = f"""
Eres un asistente contable que sirve de apoyo a la gestión comercial de una empresa. Te pueden preguntar información sobre ventas por mes, año, trimestre, etc, cuando se refieran a los clientes se refieren a la razon social.

DATOS DISPONIBLES:
{datos_contexto}

Responde con precisión, usando números con separadores de miles, y un tono profesional y claro.
"""

    # Construir historial completo para OpenAI
    historial_con_prompt = [{"role": "system", "content": system_prompt}] + historial
    historial_con_prompt.append({"role": "user", "content": mensaje_usuario})

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=historial_con_prompt,
            max_tokens=500,
            temperature=0.7
        )
        respuesta = response.choices[0].message.content.strip()

        # Guardar en historial
        historial.append({"role": "user", "content": mensaje_usuario})
        historial.append({"role": "assistant", "content": respuesta})

        # Limitar historial a últimos 10 mensajes
        conversaciones[numero_usuario] = historial[-10:]
        return respuesta
    except Exception as e:
        return f"❌ Error al procesar con IA: {str(e)}"

# ===== Procesador de consultas =====
def procesar_consulta(mensaje, numero_usuario=None):
    mensaje_lower = mensaje.lower()

    # 1. Totales mensuales
    for nombre_mes, numero_mes in MESES.items():
        if nombre_mes in mensaje_lower:
            if "iva" in mensaje_lower:
                return f"🔹 IVA en {nombre_mes}: ${calcular_totales_mes(mes=numero_mes)['total_iva']:,.0f}"
            elif "neto" in mensaje_lower:
                return f"🔹 Neto en {nombre_mes}: ${calcular_totales_mes(mes=numero_mes)['total_neto']:,.0f}"
            elif "factura" in mensaje_lower or "cuántas" in mensaje_lower:
                return f"🔹 Cantidad de facturas en {nombre_mes}: {contar_facturas_mes(numero_mes)}"
            else:
                return f"🔹 Total ventas en {nombre_mes}: ${calcular_totales_mes(mes=numero_mes)['total_ventas']:,.0f}"

    # 2. Totales anuales
    if "año" in mensaje_lower or "anual" in mensaje_lower:
        año_actual = datetime.now().year
        return f"📊 Total anual de ventas {año_actual}: ${calcular_totales_año(año_actual)['total_ventas']:,.0f}"

    # 3. Última factura
    if "última factura" in mensaje_lower:
        ultima = obtener_ultima_factura()
        if ultima:
            return f"📑 Última factura: Folio {ultima['Folio']} - {ultima['Razón Social']} - ${ultima['Monto total']}"
        else:
            return "⚠️ No hay facturas registradas."

    # 4. Cliente
    if "cliente" in mensaje_lower or "razón social" in mensaje_lower:
        nombre = mensaje.split("cliente")[-1].strip()
        facturas, total = buscar_por_cliente(nombre)
        return f"📊 Cliente {nombre}: {len(facturas)} facturas, total ${total:,.0f}"

    # 5. Tipos de documentos
    if "tipos de documentos" in mensaje_lower or "tipo de documentos" in mensaje_lower:
        return f"📂 Tipos de documentos en el reporte: {', '.join(map(str, tipos_documentos()))}"

    # 6. Folio específico
    numeros = re.findall(r'\d+', mensaje)
    if numeros and "folio" in mensaje_lower:
        return buscar_factura(numeros[0])

    # 7. Si nada coincide → ChatGPT
    contexto = obtener_resumen_datos()
    return consultar_chatgpt(mensaje, contexto, numero_usuario=numero_usuario)

# ===== Endpoint WhatsApp (Twilio) =====
@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    mensaje = request.form.get("Body", "").strip()
    numero = request.form.get("From", "").replace("whatsapp:", "")
    print(f"\n=== NUEVO MENSAJE de {numero} ===\n{mensaje}")

    resp = MessagingResponse()
    try:
        respuesta = procesar_consulta(mensaje, numero_usuario=numero)
        resp.message(respuesta)

    except Exception as e:
        resp.message(f"❌ Error: {str(e)}")

    return str(resp)

# ===== Endpoint UptimeRobot =====
@app.route("/ping", methods=["GET"])
def ping():
    return "alive", 200

# ===== Ejecuta servidor =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080)) 
    app.run(host="0.0.0.0", port=port, debug=True)
    




