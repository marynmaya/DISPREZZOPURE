import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Configurazione token e prezzi
TELEGRAM_BOT_TOKEN = "8886071836:AAEaF6UX8MhYIaoVzBYnu-ununozQBNE-0E"
CRYPTO_PAY_TOKEN = "632313:AAEKqdS9oAxDjFLiglSxMRrcYUiagu9rj2P"
PRICE_USDT_TON = 0.5  # Prezzo impostato a 0.5

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

INSULTI = [
    "Hai la stessa utilità di un posacenere su una moto da cross.",
    "Se la mediocrità avesse una capitale, tu saresti il sindaco onorario.",
    "Il tuo cervello viaggia così in ritardo che quando arrivano le idee sono già scadute.",
    "Sei la prova vivente che l'evoluzione a volte si prende una pausa sabbatica.",
    "Hai il QI di un ferro da stiro, ma con molta meno personalità."
]

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
    import random
    
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
                    insulto_scelto = random.choice(INSULTI)
                    await callback.message.answer(f"Pagamento verificato! Ecco il tuo insulto:\n\n_{insulto_scelto}_", parse_mode="Markdown")
                else:
                    await callback.message.answer("Risultato: pagamento non ancora completato o non trovato. Completa il pagamento tramite il link sopra e riprova.")
            else:
                await callback.message.answer("Errore nella verifica del pagamento. Riprova più tardi.")
                
    await callback.answer()

# Generazione basata sull'indice univoco calcolato dal testo dell'utente
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_any_text(message: types.Message):
    user_text = message.text.strip()
    
    if len(user_text) > 40:
        short_text = user_text[:37] + "..."
    else:
        short_text = user_text

    # Usiamo la somma dei codici dei caratteri del testo per variare sempre la scelta
    seed = sum(ord(c) for c in user_text)
    
    frase_uno = [
        f"Mi vieni a raccontare che '{short_text}' come se a qualcuno potesse importare qualcosa.",
        f"Pretendi di venirmi a dire '{short_text}' ignorando totalmente quanto la tua opinione sia irrilevante.",
        f"Te ne esci dicendo '{short_text}' e pretendi pure di non fare ridere i polli.",
        f"L'idea fissa secondo cui '{short_text}' la dice lunga sul vuoto che hai dentro.",
        f"Vieni qui a scrivermi '{short_text}' dimostrando una coerenza pari a zero.",
        f"Sostenere che '{short_text}' è il modo migliore per certificare la tua totale assenza di idee."
    ]
    
    frase_due = [
        "Elimina l'account e risparmiaci altra aria sprecata.",
        "Torna a dormire, che forse è l'unica cosa che ti riesce decentemente nella vita.",
        "La prossima volta evita di condividere il vuoto spinto che ti abita in testa.",
        "Certe banalità farebbero spegnere il cervello pure a un bradipo in coma.",
        "Risparmiaci queste uscite da bar dello sport di periferia.",
        "Il mondo girerebbe decisamente meglio se evitassi di digitare cose a caso."
    ]

    idx1 = seed % len(frase_uno)
    idx2 = (seed // 3) % len(frase_due)

    risposta = f"{frase_uno[idx1]} {frase_due[idx2]}"
    await message.answer(risposta)

# --- BLOCCO PER RENDER (Tiene aperta la porta HTTP) ---
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

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
    
    import asyncio
    asyncio.run(dp.start_polling(bot))
