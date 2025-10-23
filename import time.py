import time
from pathlib import Path
import json
import telebot
from telebot import types

# ----------------- CONFIGURAÇÕES -----------------
BOT_TOKEN = "8110292010:AAEDNBuw4wyJfpOVOcxTSItT27nXt4LixEE"
ADMIN_GROUP_ID = -1003188512001  # ID do grupo de admins

# Links das imagens
IMG_INICIAL = "https://i.postimg.cc/gJS3kCWm/01do-Delay-Bot2.jpg"
IMG_PIX = "https://i.postimg.cc/HkDXx0f6/Planos.jpg"

PIX_INFO = (
    "💳 *PIX (Chave)*: 01doDelay@gmail.com\n"
    "💰 *Valor:* Referente ao Plano\n\n"

)

DATA_DIR = Path("bot_data")
ORDERS_FILE = DATA_DIR / "orders.json"
COMPROVANTES_DIR = DATA_DIR / "comprovantes"

DATA_DIR.mkdir(exist_ok=True)
COMPROVANTES_DIR.mkdir(exist_ok=True)
if not ORDERS_FILE.exists():
    ORDERS_FILE.write_text("[]", encoding="utf-8")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="MARKDOWN")

# ----------------- FUNÇÕES -----------------
def load_orders():
    return json.loads(ORDERS_FILE.read_text(encoding="utf-8"))

def save_orders(orders):
    ORDERS_FILE.write_text(json.dumps(orders, ensure_ascii=False, indent=2), encoding="utf-8")

def add_order(order):
    orders = load_orders()
    orders.append(order)
    save_orders(orders)

# ----------------- TECLADOS -----------------
def main_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💸 Ver PIX / pagar", callback_data="show_pix"))
    kb.add(types.InlineKeyboardButton("❓ Ajuda", callback_data="help"))
    return kb

def back_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 Voltar ao menu inicial", callback_data="go_home"))
    return kb

def admin_action_keyboard(order_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Aprovar", callback_data=f"approve|{order_id}"))
    kb.add(types.InlineKeyboardButton("❌ Recusar", callback_data=f"reject|{order_id}"))
    return kb

# ----------------- COMANDOS -----------------
@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    text = (
        f"Olá, {message.from_user.first_name}! 👋\n\n"
        "Bem-vindo 01 Do Delay.\n\n"
        "O melhor servidor de delay esportivo do Brasil!.\n"
        "Escolha uma opção abaixo:"
    )
    bot.send_photo(
        message.chat.id,
        IMG_INICIAL,
        caption=text,
        reply_markup=main_keyboard()
    )

# ----------------- MOSTRAR PIX -----------------
@bot.callback_query_handler(func=lambda cq: cq.data == "show_pix")
def cq_show_pix(cq):
    bot.answer_callback_query(cq.id)
    bot.send_photo(
        cq.from_user.id,
        IMG_PIX,
        caption=f"{PIX_INFO}\n\n📸 Assim que fizer o pagamento, envie o comprovante aqui.",
        reply_markup=back_keyboard()
    )

# ----------------- AJUDA -----------------
@bot.callback_query_handler(func=lambda cq: cq.data == "help")
def cq_help(cq):
    bot.answer_callback_query(cq.id)
    bot.send_message(
        cq.from_user.id,
        "🆘 *Precisa de ajuda?*\nEntre em contato com um administrador do grupo para suporte manual.",
        reply_markup=back_keyboard()
    )

# ----------------- VOLTAR AO MENU -----------------
@bot.callback_query_handler(func=lambda cq: cq.data == "go_home")
def cq_go_home(cq):
    bot.answer_callback_query(cq.id)
    text = (
        "🏠 *Menu principal*\n\n"
        "Escolha uma das opções abaixo:"
    )
    bot.send_photo(
        cq.from_user.id,
        IMG_INICIAL,
        caption=text,
        reply_markup=main_keyboard()
    )

# ----------------- RECEBER COMPROVANTE -----------------
@bot.message_handler(content_types=["photo", "document"])
def handle_proof(message):
    # Ignora mensagens que não sejam no chat privado (1:1 com o bot)
    if message.chat.type != "private":
        return
    
    user = message.from_user
    timestamp = int(time.time())
    order_id = f"{user.id}-{timestamp}"
    saved_filename = None

    try:
        if message.content_type == "photo":
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            ext = ".jpg"
            saved_filename = COMPROVANTES_DIR / f"{order_id}{ext}"
            downloaded = bot.download_file(file_info.file_path)
            with open(saved_filename, "wb") as f:
                f.write(downloaded)
        else:
            file_id = message.document.file_id
            file_info = bot.get_file(file_id)
            ext = Path(message.document.file_name).suffix or ".bin"
            saved_filename = COMPROVANTES_DIR / f"{order_id}{ext}"
            downloaded = bot.download_file(file_info.file_path)
            with open(saved_filename, "wb") as f:
                f.write(downloaded)
    except Exception as e:
        bot.reply_to(message, "⚠️ Erro ao processar o arquivo. Tente novamente.")
        print("Erro:", e)
        return

    note = message.caption or ""
    order = {
        "order_id": order_id,
        "user_id": user.id,
        "username": f"@{user.username}" if user.username else user.full_name,
        "timestamp": timestamp,
        "status": "pending",
        "note": note,
        "file_path": str(saved_filename),
    }
    add_order(order)

    bot.send_message(user.id, "✅ Comprovante recebido! Um administrador irá verificar em breve. Caso demore mais de 1 hora, contate um Admnistrador do grupo")

    caption_for_admin = (
        f"📩 *Novo comprovante recebido!*\n\n"
        f"*Pedido:* `{order_id}`\n"
        f"*Usuário:* [{user.full_name}](tg://user?id={user.id}) {order['username']}\n"
        f"*Observação:* {note or '-'}"
    )

    try:
        with open(saved_filename, "rb") as f:
            if message.content_type == "photo":
                bot.send_photo(ADMIN_GROUP_ID, f, caption=caption_for_admin, reply_markup=admin_action_keyboard(order_id))
            else:
                bot.send_document(ADMIN_GROUP_ID, f, caption=caption_for_admin, reply_markup=admin_action_keyboard(order_id))
        print(f"✅ Comprovante enviado para o grupo ({ADMIN_GROUP_ID})")
    except Exception as e:
        print(f"⚠️ Erro ao enviar comprovante para o grupo: {e}")

# ----------------- AÇÕES DOS ADMINS -----------------
@bot.callback_query_handler(func=lambda cq: cq.data.startswith("approve|") or cq.data.startswith("reject|"))
def cq_admin_action(cq):
    action, order_id = cq.data.split("|", 1)
    orders = load_orders()
    target = next((o for o in orders if o["order_id"] == order_id), None)
    if not target:
        bot.answer_callback_query(cq.id, "Pedido não encontrado.", show_alert=True)
        return

    user_id = target["user_id"]

    if action == "approve":
        target["status"] = "approved"
        bot.send_message(user_id, "✅ Pagamento aprovado! Obrigado, seu comprovante foi validado. Aguarde que um Admin te mandará o link em instantes! Obrigado por comprar o melhor delay esportivo do Brasil!")
    else:
        target["status"] = "rejected"
        bot.send_message(user_id, "❌ Comprovante recusado. Por favor, envie novamente ou contate um admin.")

    save_orders(orders)
    bot.answer_callback_query(cq.id, f"Pedido {order_id} atualizado.")

# ----------------- INICIAR -----------------
if __name__ == "__main__":
    print("🤖 Bot rodando...")
    bot.polling(none_stop=True, interval=0, timeout=20)

