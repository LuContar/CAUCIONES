import datetime
import os
import pytz
import threading
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8928763343:AAG744-qe2fMhDqVw4wXEUEHf9QBgE5dIQo"
CHAT_ID = 1239937569
ZONA_HORARIA = pytz.timezone('America/Argentina/Buenos_Aires')

# Servidor web para mantener vivo el servicio en Render Free
class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheck)
    server.serve_forever()

# Obtener TNA pública de cauciones a 1 día en ARS vía API JSON
def obtener_tasa_publica():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = "https://criptoya.com/api/cauciones"
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            tna = data.get('ars', {}).get('1', {}).get('tna')
            if tna:
                return f"{round(tna, 2)}% TNA"
        return None
    except Exception as e:
        print(f"Error al obtener tasa pública: {e}")
        return None

async def enviar_alerta_13(context: ContextTypes.DEFAULT_TYPE):
    context.bot_data['caucionado_hoy'] = False

    tasa_str = obtener_tasa_publica()
    info_tasa = f"\n📈 **Tasa de mercado (1D):** `{tasa_str}`" if tasa_str else ""

    keyboard = [[
        InlineKeyboardButton("Sí, ya hice 👍", callback_data='si'),
        InlineKeyboardButton("No todavía ❌", callback_data='no')
    ]]
    
    mensaje = f"🚨 **Recordatorio de Cauciones (13:00 hs)**{info_tasa}\n\n¿Vas a caucionar hoy?"
    await context.bot.send_message(
        chat_id=CHAT_ID, 
        text=mensaje, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

async def enviar_alerta_16(context: ContextTypes.DEFAULT_TYPE):
    if context.bot_data.get('caucionado_hoy', False):
        return

    tasa_str = obtener_tasa_publica()
    info_tasa = f"\n📈 **Tasa de mercado (1D):** `{tasa_str}`" if tasa_str else ""

    keyboard = [[
        InlineKeyboardButton("Sí, ya hice 👍", callback_data='si'),
        InlineKeyboardButton("No ❌", callback_data='no')
    ]]
    
    mensaje = f"🔔 **Segundo aviso de Cauciones (16:00 hs)**{info_tasa}\n\nQueda poco para el cierre de mercado. ¿Hiciste la caución?"
    await context.bot.send_message(
        chat_id=CHAT_ID, 
        text=mensaje, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

async def probar_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasa_str = obtener_tasa_publica()
    info_tasa = f"\n📈 **Tasa de mercado (1D):** `{tasa_str}`" if tasa_str else "\n⚠️ *(No se pudo obtener la tasa pública)*"

    keyboard = [[
        InlineKeyboardButton("Sí, ya hice 👍", callback_data='si'),
        InlineKeyboardButton("No todavía ❌", callback_data='no')
    ]]
    mensaje = f"🧪 **Prueba de alerta de Cauciones**{info_tasa}\n\n¿Vas a caucionar hoy?"
    await update.message.reply_text(
        text=mensaje, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

async def responder_boton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'si':
        context.bot_data['caucionado_hoy'] = True
        await query.edit_message_text("✅ **¡Excelente!** Operación registrada. Hasta mañana.")
    elif query.data == 'no':
        await query.edit_message_text("⏳ **Anotado.** Te vuelvo a avisar a las 16:00 hs antes del cierre.")

def main():
    threading.Thread(target=start_health_check, daemon=True).start()

    # Damos 8 segundos para que Render apague por completo el contenedor viejo
    print("Esperando liberación de sesión anterior...")
    time.sleep(8)

    app = Application.builder().token(TOKEN).build()

    dias_semana = (0, 1, 2, 3, 4)

    app.job_queue.run_daily(
        enviar_alerta_13, 
        time=datetime.time(13, 0, tzinfo=ZONA_HORARIA), 
        days=dias_semana
    )
    
    app.job_queue.run_daily(
        enviar_alerta_16, 
        time=datetime.time(16, 0, tzinfo=ZONA_HORARIA), 
        days=dias_semana
    )

    app.add_handler(CommandHandler("probar", probar_comando))
    app.add_handler(CallbackQueryHandler(responder_boton))

    print("Bot de cauciones ejecutándose...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
