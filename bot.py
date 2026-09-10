import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import asyncio
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from google import genai
from google.genai import types as genai_types

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("BOT_TOKEN")
CRYPTO_PAY_TOKEN = "632313:AAEKqdS9oAxDjFLiglSxMRrcYUiagu9rj2P"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("ERRORE: Token di Telegram non trovato nelle variabili d'ambiente!")

if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None

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
                    ai_reply = "Pagamento verificato, ma non è stato possibile generare l'insulto."
                    if ai_client:
                        try:
                            config_pagamento = genai_types.GenerateContentConfig(
                                system_instruction="Sei un generatore di cinismo puro e imprevedibile. Non ripetere mai la stessa frase.",
                                temperature=1.4,
                                top_p=0.98,
                            )
                            rnd_pay = f" [ID:{random.randint(100000, 999999)}]"
                            prompt_pagamento = f"L'utente ha pagato l'insulto.{rnd_pay} Scrivi un tributo di disprezzo completamente nuovo e creativo per celebrarlo."
                            response = ai_client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=prompt_pagamento,
                                config=config_pagamento
                            )
                            if response and response.text:
                                ai_reply = response.text.strip()
                        except Exception as e:
                            logging.error(f"Errore IA pagamento: {e}")
                    
                    await callback.message.answer(f"Pagamento verificato! Ecco il tuo insulto:\n\n_{ai_reply}_", parse_mode="Markdown")
                else:
                    await callback.message.answer("Risultato: pagamento non ancora completato o non trovato.")
            else:
                await callback.message.answer("Errore nella verifica del pagamento. Riprova più tardi.")
                
    await callback.answer()

@dp.message(F.text & ~F.text.startswith("/"))
async def handle_any_text(message: types.Message):
    user_text = message.text.strip()
    
    if not ai_client:
        await message.answer("Errore: Chiave API di Gemini non configurata.")
        return

    config = genai_types.GenerateContentConfig(
        system_instruction=(
            "Sei un'intelligenza artificiale cinica, caustica, spietata e profondamente sarcastica. "
            "Il tuo obiettivo tassativo è non ripetere mai due volte la stessa frase, lo stesso costrutto grammaticale "
            "o lo stesso tipo di battuta. Ogni risposta deve essere completamente diversa, imprevedibile, "
            "creativa e unica nel suo genere."
        ),
        temperature=1.4,
        top_p=0.98,
    )

    random_seed_text = f" [RND-ID:{random.randint(100000, 999999)}]"

    prompt_completo = (
        f"L'utente ha detto: '{user_text}'.{random_seed_text} "
        f"Reagisci con un insulto o una considerazione sprezzante, caustica e originale. "
        f"Modifica completamente le parole e lo stile rispetto a qualsiasi cosa potresti aver generato in precedenza."
    )

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_completo,
            config=config
        )
        
        if response and response.text:
            await message.answer(response.text.strip())
        else:
            await message.answer("Errore: L'IA non ha restituito alcun testo.")
    except Exception as e:
        logging.error(f"Eccezione chiamata Google GenAI: {e}")
        await message.answer(f"Errore tecnico durante la chiamata IA: {e}")

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
