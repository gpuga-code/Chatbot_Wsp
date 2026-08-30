# Chatbot WhatsApp - Consultas de Facturas SII

Chatbot de WhatsApp que permite consultar información de facturas de venta (declaradas ante el SII) directamente desde una hoja de Google Sheets, mediante lenguaje natural. Integra Twilio para la mensajería de WhatsApp y OpenAI (GPT-3.5) como respaldo conversacional cuando la consulta no calza con los comandos predefinidos.

## Funcionalidades

- **Totales por mes**: ventas, IVA o neto de un mes específico (ej: *"total de ventas en marzo"*).
- **Cantidad de facturas** emitidas en un mes determinado.
- **Totales anuales** de ventas.
- **Búsqueda por cliente** (razón social) con cantidad de facturas y monto total.
- **Última factura** registrada.
- **Tipos de documentos** presentes en el reporte.
- **Búsqueda por folio** específico, mostrando el detalle completo de la factura.
- **Respaldo con IA (ChatGPT)**: si la consulta no coincide con ningún comando predefinido, se responde usando OpenAI con el contexto de los datos disponibles, manteniendo un historial de conversación por usuario.
- **Endpoint de salud** (`/ping`) para mantener el servicio activo con UptimeRobot u otro servicio de monitoreo.

## Tecnologías

- [Flask](https://flask.palletsprojects.com/) – servidor web
- [Twilio API](https://www.twilio.com/whatsapp) – integración con WhatsApp
- [gspread](https://github.com/burnash/gspread) + [oauth2client](https://github.com/googleapis/oauth2client) – conexión con Google Sheets
- [OpenAI API](https://platform.openai.com/) – respuestas conversacionales

## Requisitos previos

- Python 3.9+
- Una cuenta de servicio de Google Cloud con acceso a Google Sheets API y Google Drive API
- Una cuenta de Twilio con WhatsApp habilitado (sandbox o número propio)
- Una API Key de OpenAI

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/chatbot_WSP.git
   cd chatbot_WSP
   ```

2. Crea un entorno virtual e instala las dependencias:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configura las variables de entorno (ver sección siguiente).

4. Ejecuta el servidor:
   ```bash
   python app.py
   ```

## Variables de entorno

Este proyecto **no incluye ninguna credencial** en el código. Debes configurar las siguientes variables de entorno antes de ejecutar la aplicación:

| Variable | Descripción |
|---|---|
| `GOOGLE_JSON_PATH` | Contenido completo (en formato JSON, como string) del archivo de credenciales de la cuenta de servicio de Google |
| `OPENAI_API_KEY` | API Key de OpenAI |
| `TWILIO_ACCOUNT_SID` | SID de tu cuenta de Twilio |
| `TWILIO_AUTH_TOKEN` | Auth Token de tu cuenta de Twilio |
| `PORT` | (Opcional) Puerto del servidor. Por defecto `8080` |

> ⚠️ **Importante**: nunca subas tus credenciales reales a GitHub. Usa un archivo `.env` local (ya excluido en `.gitignore`) o configura las variables directamente en tu plataforma de despliegue (Railway, Render, Heroku, etc.).

## Estructura esperada de la hoja de Google Sheets

El bot espera que la hoja de cálculo (por defecto llamada `Reporte SII 09-25`) tenga, al menos, las siguientes columnas:

- `Fecha Docto` (o `Fecha`)
- `Folio`
- `Razón Social`
- `Tipo Doc`
- `Monto total`
- `Monto neto`
- `Monto IVA`

## Despliegue

El proyecto está preparado para desplegarse en cualquier plataforma que soporte aplicaciones Flask (Railway, Render, Heroku, etc.), configurando las variables de entorno mencionadas arriba y apuntando el webhook de Twilio a la ruta `/whatsapp` de tu dominio desplegado.

## Licencia

Este proyecto es de uso libre. Ajusta esta sección según lo que prefieras (MIT, uso privado, etc.).
