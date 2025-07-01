import os
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (ApplicationBuilder, CommandHandler,
                          CallbackQueryHandler, MessageHandler,
                          ConversationHandler, ContextTypes, filters)


# ✅ Variáveis de ambiente com fallback
TOKEN = os.environ.get("TOKEN",
                       "7333842067:AAEynLOdFTnJeMRw-fhYhfU-UT0PFXoTduE")
CHAVE_PIX = os.environ.get("CHAVE_PIX", "pattywatanabe@outlook.com")
URL_WHATSAPP = os.environ.get("URL_WHATSAPP", "https://wa.me/818030734889")
URL_FORMULARIO = os.environ.get("URL_FORMULARIO",
                                "https://forms.gle/SBV9vUrenLN7VELi6")
VALOR_IENE_REAL = float(os.environ.get("VALOR_IENE_REAL",
                                       0.039))  # ¥1 = R$0,039
TAXA_SERVICO = float(os.environ.get("TAXA_SERVICO", 0.20))  #20% de taxa
TAXA_PIX = float(os.environ.get("TAXA_PIX", 0.0099))  # 0.99% de taxa do Pix
BOT_USERNAME = os.environ.get("BOT_USERNAME", "@Enviamosjpbot")
GROUP_USERNAME = os.environ.get("GROUP_USERNAME", "@enviamos_jp")
ADMIN_IDS = [7968066840]

app = ApplicationBuilder().token(TOKEN).build()

ARQUIVO_PRODUTOS = "produtos.json"


def salvar_produtos():
    with open(ARQUIVO_PRODUTOS, "w", encoding="utf-8") as f:
        json.dump(produtos, f, ensure_ascii=False, indent=2)


def carregar_produtos():
    if os.path.exists(ARQUIVO_PRODUTOS):
        with open(ARQUIVO_PRODUTOS, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


ARQUIVO_CARRINHOS = "carrinhos.json"


def salvar_carrinhos():
    with open(ARQUIVO_CARRINHOS, "w", encoding="utf-8") as f:
        json.dump(carrinhos, f, ensure_ascii=False, indent=2)


def carregar_carrinhos():
    if os.path.exists(ARQUIVO_CARRINHOS):
        with open(ARQUIVO_CARRINHOS, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# Estruturas em memória
produtos = carregar_produtos()
carrinhos = carregar_carrinhos()
cadastro_temp = {}
imagens_pedido = {}

# Etapas do cadastro
NOME, DESCRICAO, PRECO, FOTO = range(4)


# Comando de início
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    # Adiciona 1 unidade do produto se vier do botão do grupo
    if args:
        produto_id = args[0]
        if produto_id in produtos:
            carrinho = carrinhos.get(user_id, {})
            carrinho[produto_id] = carrinho.get(produto_id, 0) + 1
            carrinhos[user_id] = carrinho
            salvar_carrinhos()

    carrinho = carrinhos.get(user_id)
    if not carrinho:
        await update.message.reply_text("🛒 Seu carrinho está vazio.")
        return

    botoes = []
    texto = "🛒 *Seu carrinho:*\n\n"
    total_iene = 0

    for id_produto, qtd in carrinho.items():
        produto = produtos[id_produto]
        subtotal = produto["preco"] * qtd
        total_iene += subtotal
        subtotal_real = subtotal * VALOR_IENE_REAL
        texto += f" {qtd} × {produto['nome']} = ¥{(subtotal):,}".replace(
            ",", ".") + f" | R$ {subtotal_real:.2f}\n"

        botoes.append([
            InlineKeyboardButton("+1", callback_data=f"mais:{id_produto}"),
            InlineKeyboardButton("-1", callback_data=f"menos:{id_produto}"),
            InlineKeyboardButton("❌ Cancelar item",
                                 callback_data=f"cancelar:{id_produto}")
        ])

    total_servico = total_iene * TAXA_SERVICO
    total_pix = (total_iene + total_servico) * TAXA_PIX
    total_final = total_iene + total_servico + total_pix
    total_real = total_final * VALOR_IENE_REAL

    texto += f"\nSubtotal: ¥{total_iene:,}".replace(
        ",", ".") + f" | R$ {total_iene * VALOR_IENE_REAL:.2f}"
    texto += f"\nTaxa de serviço (20%): ¥{int(total_servico):,}".replace(
        ",", ".") + f" | R$ {total_servico * VALOR_IENE_REAL:.2f}"
    texto += f"\nTaxa Pix (0.99%): ¥{int(total_pix):,}".replace(
        ",", ".") + f" | R$ {total_pix * VALOR_IENE_REAL:.2f}"
    texto += f"\n\n*Total: ¥{int(total_final):,}".replace(
        ",", ".") + f" | R$ {total_real:.2f}*"

    botoes.append(
        [InlineKeyboardButton("✅ Confirmar", callback_data="confirmar")])

    markup = InlineKeyboardMarkup(botoes)
    await update.message.reply_text(texto,
                                    parse_mode="Markdown",
                                    reply_markup=markup)


# Início do cadastro de produto
async def cadastrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text("📝 Qual o nome do produto?")
    return NOME


async def receber_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nome"] = update.message.text
    await update.message.reply_text("✏️ Agora envie a descrição do produto.")
    return DESCRICAO


async def receber_descricao(update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
    context.user_data["descricao"] = update.message.text
    await update.message.reply_text("💴 Qual o preço em ienes?")
    return PRECO


async def receber_preco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        preco = int(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Envie um valor numérico.")
        return PRECO

    context.user_data["preco"] = preco
    valor_real = preco * VALOR_IENE_REAL

    await update.message.reply_text(f"📸 Agora envie a foto do produto.\n"
                                    f" Preço: ¥{(preco):,}".replace(",", ".") +
                                    f" | R$ {valor_real:.2f}")
    return FOTO


async def receber_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    foto = update.message.photo[-1].file_id
    nome = context.user_data["nome"]
    descricao = context.user_data["descricao"]
    preco = context.user_data["preco"]
    preco_real = preco * VALOR_IENE_REAL

    id_produto = str(len(produtos) + 1)
    produtos[id_produto] = {
        "nome": nome,
        "descricao": descricao,
        "preco": preco,
        "foto": foto
    }
    salvar_produtos()

    link = f"https://t.me/Enviamosjpbot?start={id_produto}"
    botao = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🛒 Comprar", url=link)]])

    await context.bot.send_photo(chat_id=GROUP_USERNAME,
                                 photo=foto,
                                 caption=(f"*{nome}*\n\n"
                                          f"_{descricao}_\n\n"
                                          f"🇯🇵¥{(preco):,}".replace(",", ".") +
                                          f" | 🇧🇷R${preco_real:.2f}"),
                                 parse_mode="Markdown",
                                 reply_markup=botao)

    await update.message.reply_text(
        "✅ Produto cadastrado e enviado para o grupo!")
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cadastro cancelado.")
    return ConversationHandler.END


# Carrinho e compra
async def botao_comprar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, id_produto = query.data.split(":")
    user_id = query.from_user.id
    carrinho = carrinhos.get(user_id, {})
    carrinho[id_produto] = carrinho.get(id_produto, 0) + 1
    carrinhos[user_id] = carrinho
    await query.message.reply_text(
        "✅ Produto adicionado ao carrinho. Use /carrinho para ver.")


async def ver_carrinho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    carrinho = carrinhos.get(user_id)

    if not carrinho:
        # Se for via comando /carrinho
        if update.message:
            await update.message.reply_text(
                "\U0001F6D2 Seu carrinho está vazio.")
        # Se for via botão
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                "\U0001F6D2 Seu carrinho está vazio.")
        return

    botoes = []
    texto = "\U0001F6D2 *Seu carrinho:*\n\n"
    total_iene = 0

    for id_produto, qtd in carrinho.items():
        prod = produtos[id_produto]
        subtotal = prod["preco"] * qtd
        total_iene += subtotal
        subtotal_real = subtotal * VALOR_IENE_REAL
        texto += f"🛍️ *{qtd}* - {prod['nome']}\n\n"

        botoes.append([
            InlineKeyboardButton("+1", callback_data=f"mais:{id_produto}"),
            InlineKeyboardButton("-1", callback_data=f"menos:{id_produto}"),
        ])
        botoes.append([
            InlineKeyboardButton("\u274c Cancelar item",
                                 callback_data=f"cancelar:{id_produto}")
        ])

    total_servico = total_iene * TAXA_SERVICO
    total_pix = (total_iene + total_servico) * TAXA_PIX
    total_final = total_iene + total_servico + total_pix
    total_real = total_final * VALOR_IENE_REAL

    texto += "──────────────\n"
    texto += f"\n🧾*Subtotal:* ¥{total_iene:,}".replace(
        ",", ".") + f" | R$ {total_iene * VALOR_IENE_REAL:.2f}"
    texto += f"\n💼*Taxa de serviço (20%):* ¥{int(total_servico):,}".replace(
        ",", ".") + f" | R$ {total_servico * VALOR_IENE_REAL:.2f}"
    texto += f"\n💸*Taxa Pix (0.99%):* ¥{int(total_pix):,}".replace(
        ",", ".") + f" | R$ {total_pix * VALOR_IENE_REAL:.2f}"
    texto += f"\n\n✅*Total: ¥{int(total_final):,}".replace(
        ",", ".") + f" | R$ {total_real:.2f}*\n\n"
    texto += "──────────────"

    # Mensagem de ação
    mensagem_finalizar = ("      🛍️  *Deseja finalizar sua compra?*\n\n")

    # Teclado Finalizar
    teclado_finalizar = [[
        InlineKeyboardButton("✅ Finalizar compra",
                             callback_data="finalizar_compra"),
        InlineKeyboardButton("❌ Cancelar pedido",
                             callback_data="cancelar_pedido")
    ]]

    # Teclado de quantidade
    markup_quantidade = InlineKeyboardMarkup(botoes)

    if update.message:
        # 1) Resumo do carrinho
        await update.message.reply_text(texto, parse_mode="Markdown")

        # 2) Botões +1/-1/Cancelar item
        await update.message.reply_text(
            "Ajuste a quantidade ou cancele o item:",
            reply_markup=markup_quantidade)

        # 3) Mensagem de Finalizar compra
        await update.message.reply_text(
            mensagem_finalizar,
            reply_markup=InlineKeyboardMarkup(teclado_finalizar),
            parse_mode="Markdown")

    else:
        try:
            # Atualiza a mensagem principal
            await update.callback_query.edit_message_text(
                texto, parse_mode="Markdown")

            # 2) Botões +1/-1/Cancelar item
            await update.callback_query.message.reply_text(
                "Ajuste a quantidade ou cancele o item:",
                reply_markup=markup_quantidade)

            # 3) Mensagem de Finalizar compra
            await update.callback_query.message.reply_text(
                mensagem_finalizar,
                reply_markup=InlineKeyboardMarkup(teclado_finalizar),
                parse_mode="Markdown")

        except telegram.error.BadRequest as e:
            print(e)


    # Botões do carrinho
async def carrinho_callback(update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if user_id not in carrinhos:
        carrinhos[user_id] = {}

    if data.startswith("mais:"):
        id_produto = data.split(":")[1]
        carrinho = carrinhos.get(user_id, {})
        carrinho[id_produto] = carrinho.get(id_produto, 0) + 1
        carrinhos[user_id] = carrinho
        salvar_carrinhos()

    elif data.startswith("menos:"):
        id_produto = data.split(":")[1]
        carrinho = carrinhos.get(user_id, {})
        if carrinho.get(id_produto, 0) > 1:
            carrinho[id_produto] -= 1
            carrinhos[user_id] = carrinho
            salvar_carrinhos()

    elif data.startswith("cancelar:"):
        id_produto = data.split(":")[1]
        if id_produto in carrinhos[user_id]:
            del carrinhos[user_id][id_produto]
            salvar_carrinhos()
        if not carrinhos[user_id]:
            await query.edit_message_text("🛒 Seu carrinho está vazio.")
            return ConversationHandler.END

    elif data == "finalizar_compra":
        await query.message.reply_text(
            "📝 Nome completo.\n\n"
            "📍*Ainda não tem suíte? Cadastre aqui:*\n"
            "https://forms.gle/SBV9vUrenLN7VELi6",
            parse_mode="Markdown")
        return 1  # Inicia a coleta dos dados do cliente

    elif data == "cancelar_pedido":
        await query.answer()
        await query.edit_message_text(
            "❌ Pedido cancelado. Seu carrinho foi esvaziado.")
        # Se quiser, limpe o carrinho salvo aqui:
        carrinhos[user_id] = {}
        salvar_carrinhos()  # Se tiver essa função para persistir

        return ConversationHandler.END


async def adicionar_ao_carrinho(update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    produto_id = query.data.replace("add_", "")
    produto = produtos.get(produto_id)

    if not produto:
        await query.edit_message_text("❌ Produto não encontrado.")
        return

    user_id = query.from_user.id
    carrinho = carrinhos.get(user_id, {})
    carrinho[produto_id] = carrinho.get(produto_id, 0) + 1
    carrinhos[user_id] = carrinho

    await query.edit_message_caption(
        caption=
        f"✅ *{produto['nome']}* adicionado ao carrinho!\nUse /carrinho para ver seus itens.",
        parse_mode="Markdown")


    # Coleta de dados do cliente
async def receber_nome_cliente(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    cadastro_temp[update.effective_user.id] = {"nome": update.message.text}
    await update.message.reply_text(" Informe sua suíte")
    return 2


async def receber_suite_cliente(update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
    cadastro_temp[update.effective_user.id]["suite"] = update.message.text
    await update.message.reply_text("📱 Qual seu telefone com DDD?")
    return 3


async def receber_telefone_cliente(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE):
    cadastro_temp[update.effective_user.id]["telefone"] = update.message.text
    await update.message.reply_text("📧 Agora envie seu e-mail")
    return 4


async def receber_email_cliente(update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
    cadastro_temp[update.effective_user.id]["email"] = update.message.text
    await update.message.reply_text(
        "💳 *Pagamento via Pix*\n"
        "🔑 *Chave:* `pattywatanabe@outlook.com`\n\n"
        "📸 *Após o pagamento, envie o comprovante aqui mesmo no chat* para darmos continuidade ao processo.\n\n"
        "💳 *Quer parcelar no cartão?*\n"
        "Entre em contato para receber o link de pagamento com opções de parcelamento.\n"
        "_(Taxa de 4,99% será adicionada)_\n\n"
        "❓ *Dúvidas?* Chame no WhatsApp: [Clique aqui](https://wa.me/818030734889)",
        parse_mode="Markdown")
    return 5


async def receber_comprovante(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    comprovante = update.message.photo[-1].file_id
    carrinho = carrinhos.get(user_id, {})
    cadastro = cadastro_temp.get(user_id, {})
    imagens_pedido[user_id] = []

    texto = "📦 *Novo pedido recebido!*\n\n"
    total_iene = 0

    for id_produto, qtd in carrinho.items():
        produto = produtos[id_produto]
        subtotal = produto["preco"] * qtd
        total_iene += subtotal
        subtotal_real = subtotal * VALOR_IENE_REAL
        texto += f" {qtd} × {produto['nome']} = ¥{(subtotal):,}".replace(
            ",", ".") + f" | R$ {subtotal_real:.2f}\n"
        imagens_pedido[user_id].append(produto["foto"])

    total_servico = total_iene * TAXA_SERVICO
    total_pix = (total_iene + total_servico) * TAXA_PIX
    total_final = total_iene + total_servico + total_pix
    total_real = total_final * VALOR_IENE_REAL

    texto += "\n🧾 *Resumo do pedido:*"
    texto += f"\nSubtotal: ¥{(total_iene):,}".replace(
        ",", ".") + f" | R$ {total_iene * VALOR_IENE_REAL:.2f}"
    texto += f"\nTaxa de serviço (20%): ¥{(int(total_servico)):,}".replace(
        ",", ".") + f" | R$ {total_servico * VALOR_IENE_REAL:.2f}"
    texto += f"\nTaxa Pix (0.99%): ¥{(int(total_pix)):,}".replace(
        ",", ".") + f" | R$ {total_pix * VALOR_IENE_REAL:.2f}"
    texto += f"\n\n*💰 Total: ¥{(int(total_final)):,}".replace(
        ",", ".") + f" | R$ {total_real:.2f}*\n"

    texto += "\n👤 *Dados do cliente:*"
    texto += f"\n📛 Nome: {cadastro.get('nome')}"
    texto += f"\n📦 Suíte: {cadastro.get('suite')}"
    texto += f"\n📞 Telefone: {cadastro.get('telefone')}"
    texto += f"\n📧 E-mail: {cadastro.get('email')}"

    for admin_id in ADMIN_IDS:
        await context.bot.send_message(chat_id=admin_id,
                                       text=texto,
                                       parse_mode="Markdown")
        await context.bot.send_photo(chat_id=admin_id, photo=comprovante)
        for foto in imagens_pedido[user_id]:
            await context.bot.send_photo(chat_id=admin_id, photo=foto)

    await update.message.reply_text(
        "✅ Pedido enviado com sucesso! Obrigada pela compra.")

    # Limpa dados
    carrinhos[user_id] = {}
    cadastro_temp[user_id] = {}
    imagens_pedido[user_id] = {}
    salvar_carrinhos()

    return ConversationHandler.END


# Conversa completa
carrinho_conversa = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            carrinho_callback,
    pattern="^mais:|menos:|cancelar:.+|^finalizar_compra$|^cancelar_pedido$")
    ],
    states={
        1: [MessageHandler(filters.TEXT & ~filters.COMMAND,receber_nome_cliente)],
        2: [MessageHandler(filters.TEXT & ~filters.COMMAND,
receber_suite_cliente)],
        3: [MessageHandler(filters.TEXT & ~filters.COMMAND,
receber_telefone_cliente)],
        4: [MessageHandler(filters.TEXT & ~filters.COMMAND,
receber_email_cliente)],
        5: [MessageHandler(filters.PHOTO, receber_comprovante)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar)],

    per_message=True
)

# Conversa para cadastrar produto
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("cadastrar", cadastrar)],
    states={
        NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_nome)],
        DESCRICAO:
        [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_descricao)],
        PRECO:
        [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_preco)],
        FOTO: [MessageHandler(filters.PHOTO, receber_foto)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar)],
)


# Função principal assíncrona
async def main():
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("carrinho", ver_carrinho))
    app.add_handler(carrinho_conversa)
    app.add_handler(conv_handler)
    app.add_handler(
        CallbackQueryHandler(adicionar_ao_carrinho, pattern="^add_"))

    await app.run_polling()


# Execução
if __name__ == "__main__":
    asyncio.run(main())
