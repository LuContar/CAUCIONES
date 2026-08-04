import datetime
import os
import pytz
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8928763343:AAG744-qe2fMhDqVw4wXEUEHf9QBgE5dIQo"
CHAT_ID = 1239937569
ZONA_HORARIA = pytz.timezone('America/Argentina/Buenos_Aires')

class HealthCheck(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def start_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheck)
    server.serve_forever()

async def enviar_alerta_13(context: ContextTypes.DEFAULT_TYPE):
    context.bot_data['caucionado_hoy'] = False

    keyboard = [[
        InlineKeyboardButton("Sí, ya hice 👍", callback_data='si'),
        InlineKeyboardButton("No todavía ❌", callback_data='no')
    ]]
    
    mensaje = "🚨 **Recordatorio de Cauciones (13:00 hs)**\n\n¿Vas a caucionar hoy?"
    await context.bot.send_message(
        chat_id=CHAT_ID, 
        text=mensaje, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

async def enviar_alerta_16(context: ContextTypes.DEFAULT_TYPE):
    if context.bot_data.get('caucionado_hoy', False):
        return

    keyboard = [[
        InlineKeyboardButton("Sí, ya hice 👍", callback_data='si'),
        InlineKeyboardButton("No ❌", callback_data='no')
    ]]
    
    mensaje = "🔔 **Segundo aviso de Cauciones (16:00 hs)**\n\nQueda poco para el cierre de mercado. ¿Hiciste la caución?"
    await context.bot.send_message(
        chat_id=CHAT_ID, 
        text=mensaje, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

async def probar_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("Sí, ya hice 👍", callback_data='si'),
        InlineKeyboardButton("No todavía ❌", callback_data='no')
    ]]
    mensaje = "🧪 **Prueba de alerta de Cauciones**\n\n¿Vas a caucionar hoy?"
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
