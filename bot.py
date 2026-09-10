import logging
import os
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import google.generativeai as genai

TELEGRAM_BOT_TOKEN = "8886071836:AAEaF6UX8MhYIaoVzBYnu-ununozQBNE-0E"
CRYPTO_PAY_TOKEN = "632313:AAEKqdS9oAxDjFLiglSxMRrcYUiagu9rj2P"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configurazione di Google GenAI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Usiamo il modello flash standard
    generation_model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction="Sei un bot cinico, spietato, sarcastico e disprezzativo. L'utente ti scriverà qualcosa. Tu devi rispondere rigorosamente in massimo due frasi secche e taglienti, prendendo in giro quello che ha detto senza ripeterlo paro paro, demolendo le sue convinzioni."
    )
else:
    generation_model = None

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💀 Compera un Insulto (0.5 USDT/TON)", callback_data="buy_insult")]
    ])
    await message.answer(
        "Benvenuto su **DisprezzoPuroBot**.\n\n"
        "Sei pronto a sprecare denaro per ricevere offese personalizzate di altissimo livello cinico? Clicca sotto.",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "buy_insult")
async def process_buy(callback: types.CallbackQuery):
    import aiohttp
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    payload = {
        "asset": "USDT",
        "amount": "0.5",
        "description": "Acquisto insulto cinico personalizzato da DisprezzoPuroBot",
        "payload": f"user_{callback.from_user.id}"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()
            if data.get("ok"):
                invoice = data["result"]
                pay_url = invoice["bot_invoice_url"]
                
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Paga 0.5 USDT/TON", url=pay_url)],
                    [InlineKeyboardButton(text="🔄 Ho pagato, dammi l'insulto", callback_data="check_payment")]
                ])
                await callback.message.answer(
                    "Fattura generata con successo! Clicca sul pulsante per pagare 0.5 USDT/TON tramite Crypto Pay:",
                    reply_markup=kb
                )
            else:
                await callback.message.answer("Errore nella generazione del pagamento. Riprova più tardi.")
    
    await callback.answer()

@dp.callback_query(F.data == "check_payment")
async def process_check_payment(callback: types.CallbackQuery):
    import aiohttp
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if data.get("ok"):
                invoices = data["result"]["items"]
                user_payload = f"user_{callback.from_user.id}"
                
                paid = False
                for inv in invoices:
                    if inv.get("payload") == user_payload and inv.get("status") == "paid":
                        paid = True
                        break
                
                if paid:
                    # Se ha pagato, usiamo direttamente l'IA anche qui per un insulto epico personalizzato
                    if generation_model:
                        try:
                            response = generation_model.generate_content("L'utente ha pagato regolarmente, dagli un insulto d'élite per celebrarlo.")
                            ai_reply = response.text.strip()
                        except Exception:
                            ai_reply = "Hai pagato, ma il tuo valore resta comunque prossimo allo zero."
                    else:
                        ai_reply = "Pagamento verificato, ma il cervello elettronico è disattivato."
                    
                    await callback.message.answer(f"Pagamento verificato! Ecco il tuo insulto:\n\n_{ai_reply}_", parse_mode="Markdown")
                else:
                    await callback.message.answer("Risultato: pagamento non ancora completato o non trovato. Completa il pagamento tramite il link sopra e riprova.")
            else:
                await callback.message.answer("Errore nella verifica del pagamento. Riprova più tardi.")
                
    await callback.answer()

# Gestione tramite SDK ufficiale Google Gemini
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_any_text(message: types.Message):
    user_text = message.text.strip()
    
    if not generation_model:
        await message.answer("Errore: Chiave API di Gemini non configurata nelle variabili d'ambiente.")
        return

    try:
        # Eseguiamo la generazione in modo asincrono per non bloccare il bot Telegram
        response = await asyncio.to_thread(generation_model.generate_content, user_text)
        if response and response.text:
            await message.answer(response.text.strip())
        else:
            await message.answer("Il mio cervello cinico ha avuto un sussulto vuoto. Riprova tra poco.")
    except Exception as e:
        logging.error(f"Eccezione chiamata IA ufficiale: {e}")
        await message.answer("Anche l'insulto intelligente oggi è in sciopero. Riprova più tardi.")

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    
    asyncio.run(dp.start_polling(bot))
