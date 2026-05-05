# Niight né vida?
import discord
from discord.ext import commands
import random
import json
import os
import asyncio
from datetime import datetime
import pytz
import time

# ========== CONFIGURAÇÃO INICIAL ==========
intents = discord.Intents.default()
intents.members = True
intents.invites = True
intents.message_content = True
bot = commands.Bot(command_prefix="-", intents=intents)

ARQUIVO_DB = "grimorios.json"
ARQUIVO_CONFIG = "config.json"
ARQUIVO_CONFIG_ENTRADA = "config_entrada.json"

# Cache e DBs
invites_cache = {}

# DB dos grimórios: { "user_id": {"grimorio": "4 Trevos", "roletas": 0} }
if os.path.exists(ARQUIVO_DB):
    with open(ARQUIVO_DB, "r") as f:
        db = json.load(f)
else:
    db = {}

# Config da roleta: chances
if os.path.exists(ARQUIVO_CONFIG):
    with open(ARQUIVO_CONFIG, "r") as f:
        config = json.load(f)
else:
    config = {"chance_4_trevos": 20}

# Config do canal de entrada: { "guild_id": channel_id }
if os.path.exists(ARQUIVO_CONFIG_ENTRADA):
    with open(ARQUIVO_CONFIG_ENTRADA, "r") as f:
        config_entrada = json.load(f)
else:
    config_entrada = {}

def salvar_db():
    with open(ARQUIVO_DB, "w") as f:
        json.dump(db, f, indent=4)

def salvar_config():
    with open(ARQUIVO_CONFIG, "w") as f:
        json.dump(config, f, indent=4)

def salvar_config_entrada():
    with open(ARQUIVO_CONFIG_ENTRADA, "w") as f:
        json.dump(config_entrada, f, indent=4)

def get_user_data(user_id):
    uid = str(user_id)
    if uid not in db:
        db[uid] = {"grimorio": None, "roletas": 1} # 1 roleta grátis
    return db[uid]

# ========== AGENDADOR PRA ECONOMIZAR HORAS DO RAILWAY ==========
async def agendador_offline():
    await bot.wait_until_ready()
    fuso = pytz.timezone('America/Sao_Paulo')

    while not bot.is_closed():
        agora = datetime.now(fuso)
        hora = agora.hour

        # Desliga entre 1h e 8h da manhã BRT
        if 1 <= hora < 8:
            print(f"[{agora.strftime('%H:%M')}] Horário de descanso. Desligando bot pra economizar horas...")
            await bot.close() # Desliga o bot. Railway vai reiniciar, mas ele cai de novo até dar 7h
        else:
            await asyncio.sleep(1800) # Checa de 30 em 30 minutos

# ========== EVENTOS ==========
@bot.event
async def on_ready():
    for guild in bot.guilds:
        invites_cache[guild.id] = await guild.invites()
    print(f'Bot {bot.user} online!')
    bot.loop.create_task(agendador_offline()) # Inicia o agendador

@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)

    if guild_id not in config_entrada:
        return

    canal_id = config_entrada[guild_id]
    canal = member.guild.get_channel(canal_id)
    if not canal:
        return

    convites_antes = invites_cache[member.guild.id]
    convites_depois = await member.guild.invites()
    invites_cache[member.guild.id] = convites_depois

    convite_usado = None
    for convite in convites_antes:
        convite_novo = discord.utils.get(convites_depois, code=convite.code)
        if convite_novo and convite_novo.uses > convite.uses:
            convite_usado = convite_novo
            break

    if convite_usado:
        criador = convite_usado.inviter
        embed = discord.Embed(
            title="👋 Novo membro!",
            description=f"{member.mention} entrou no servidor!",
            color=0x3498db
        )
        embed.add_field(name="Convidado por", value=criador.mention, inline=True)
        embed.add_field(name="Código do convite", value=f"`{convite_usado.code}`", inline=True)
        embed.add_field(name="Usos do convite", value=f"`{convite_usado.uses}`", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await canal.send(embed=embed)
    else:
        await canal.send(f"👋 {member.mention} entrou no servidor! Não deu pra rastrear o convite.")

@bot.event
async def on_invite_create(invite):
    invites_cache[invite.guild.id] = await invite.guild.invites()

@bot.event
async def on_invite_delete(invite):
    invites_cache[invite.guild.id] = await invite.guild.invites()

# ========== COMANDOS DA ROLETA ==========
@bot.command(name="roleta")
async def roletar_grimorio(ctx, membro: discord.Member = None):
    alvo = membro or ctx.author
    user_data = get_user_data(alvo.id)

    if user_data["roletas"] <= 0:
        await ctx.send(f"{alvo.mention} não tem roletas disponíveis! Peça pra um admin usar `-setroleta`.")
        return

    chance_4 = config["chance_4_trevos"]
    chance_3 = 100 - chance_4

    resultado = random.choices(
        population=["3 Trevos", "4 Trevos"],
        weights=[chance_3, chance_4],
        k=1
    )[0]

    user_data["roletas"] -= 1
    user_data["grimorio"] = resultado
    salvar_db()

    if resultado == "3 Trevos":
        embed = discord.Embed(
            title="🍀 Grimório de 3 Trevos",
            description=f"**Roletado para:** {alvo.mention}\n\n> Um grimório comum, mas com potencial infinito.",
            color=0x95a5a6 # Prata/Cinza
        )
        embed.set_thumbnail(url="https://i.redd.it/j8z3k8rx42h31.png") # TROCA AQUI
        embed.set_footer(text=f"Chance: {chance_3}% | Roletas restantes: {user_data['roletas']}")
    else:
        embed = discord.Embed(
            title="🍀🍀 GRIMÓRIO DE 4 TREVOS! 🍀🍀",
            description=f"**Roletado para:** {alvo.mention}\n\n> **LENDÁRIO!** Você foi escolhido pelo destino!",
            color=0xFFD700 # Dourado - barra lateral
        )
        embed.set_thumbnail(url="https://media.giphy.com/media/xT9IgzvnOyNDYnxeHS/giphy.gif") # TROCA AQUI
        embed.set_image(url="https://th.bing.com/th/id/OIP.ZLl9fnj-DfJdCFMqIPQFSAHaEG?r=0&o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3") # OPCIONAL: gif de brilho
        embed.set_footer(text=f"Chance: {chance_4}% | Roletas restantes: {user_data['roletas']}")

    embed.set_author(name="Sorteio de Grimórios", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    await ctx.send(embed=embed)

@bot.command(name="grimorio")
async def ver_grimorio(ctx, membro: discord.Member = None):
    alvo = membro or ctx.author
    user_data = get_user_data(alvo.id)

    if user_data["grimorio"]:
        await ctx.send(f"Grimório de {alvo.mention}: **{user_data['grimorio']}** 🍀\nRoletas disponíveis: **{user_data['roletas']}**")
    else:
        await ctx.send(f"{alvo.mention} ainda não roletou. Roletas disponíveis: **{user_data['roletas']}**. Use `-roleta`")

@bot.command(name="rank")
async def rank_4_trevos(ctx):
    lendarios = [(uid, data["grimorio"]) for uid, data in db.items() if data["grimorio"] == "4 Trevos"]

    if not lendarios:
        embed = discord.Embed(
            title="🏆 Rank dos 4 Trevos",
            description="Ninguém tirou 4 Trevos ainda 😢",
            color=0xFFD700
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="🏆 RANK DOS 4 TREVOS 🏆",
        description="Os escolhidos pelo grimório lendário:",
        color=0xFFD700 # Dourado - barra lateral
    )
    embed.set_thumbnail(url="https://tse2.mm.bing.net/th/id/OIP.Tu6uvm98fJxGlPrOFI9UNgHaHV?r=0&rs=1&pid=ImgDetMain&o=7&rm=3") # TROCA AQUI se quiser

    texto_rank = ""
    for i, (user_id, _) in enumerate(lendarios[:10], 1):
        try:
            user = await bot.fetch_user(int(user_id))
            if i == 1:
                texto_rank += f"🥇 **{i}.** {user.mention}\n"
            elif i == 2:
                texto_rank += f"🥈 **{i}.** {user.mention}\n"
            elif i == 3:
                texto_rank += f"🥉 **{i}.** {user.mention}\n"
            else:
                texto_rank += f"**{i}.** {user.mention}\n"
        except:
            texto_rank += f"**{i}.** Usuário saiu do server\n"

    embed.add_field(name="Top Escolhidos", value=texto_rank, inline=False)
    embed.set_footer(text=f"Total: {len(lendarios)} grimórios de 4 Trevos registrados")
    await ctx.send(embed=embed)

@bot.command(name="chances")
async def ver_chances(ctx):
    chance_4 = config["chance_4_trevos"]
    chance_3 = 100 - chance_4
    embed = discord.Embed(
        title="📊 Chances Atuais",
        color=0x9b59b6
    )
    embed.add_field(name="🍀 4 Trevos", value=f"`{chance_4}%`", inline=True)
    embed.add_field(name="🍀 3 Trevos", value=f"`{chance_3}%`", inline=True)
    await ctx.send(embed=embed)

# ========== COMANDOS DE ADMIN ==========
@bot.command(name="setarchance")
@commands.has_permissions(administrator=True)
async def setar_chance(ctx, nova_chance: int):
    if nova_chance < 0 or nova_chance > 100:
        await ctx.send("Chance tem que ser entre 0 e 100.")
        return
    config["chance_4_trevos"] = nova_chance
    salvar_config()
    await ctx.send(f"Chance de 4 Trevos: **{nova_chance}%**\nChance de 3 Trevos: **{100 - nova_chance}%**")

@bot.command(name="setroleta")
@commands.has_permissions(administrator=True)
async def set_roleta(ctx, membro: discord.Member, quantidade: int):
    if quantidade < 0:
        await ctx.send("Não dá pra setar roletas negativas.")
        return
    user_data = get_user_data(membro.id)
    user_data["roletas"] = quantidade
    salvar_db()
    await ctx.send(f"Setei **{quantidade}** roleta(s) para {membro.mention}. Total agora: **{user_data['roletas']}**")

@bot.command(name="setcanalentrada")
@commands.has_permissions(administrator=True)
async def set_canal_entrada(ctx, canal: discord.TextChannel):
    config_entrada[str(ctx.guild.id)] = canal.id
    salvar_config_entrada()
    await ctx.send(f"Canal de boas-vindas setado para {canal.mention}")

@bot.command(name="helpgrimorio")
async def help_grimorio(ctx):
    embed = discord.Embed(title="📜 Comandos do Bot", color=0x9b59b6)
    embed.add_field(name="Pra todos", value="`-roleta @user`\n`-grimorio @user`\n`-rank`\n`-chances`", inline=False)
    embed.add_field(name="Só Admin", value="`-setarchance 30`\n`-setroleta @user 3`\n`-setcanalentrada #canal`", inline=False)
    embed.set_footer(text="Bot desliga das 1h às 8h BRT pra economizar horas")
    await ctx.send(embed=embed)

@bot.command(name="brabo")
async def brabo(ctx, membro: discord.Member = None):
    if membro:
        if membro.id == ctx.author.id:
            await ctx.send(f'😎 {ctx.author.mention} mandou um salve! Niight tá na área!')
        else:
            await ctx.send(f'🔥 O niight é melhor que você, {membro.mention} 😂☠️ SE CURVA PRO PATRÃO')
    else:
        await ctx.send(f'😎 {ctx.author.mention} mandou um salve! Niight tá na área!')

@setar_chance.error
@set_roleta.error
@set_canal_entrada.error
async def admin_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Só admin pode usar esse comando.")

# ========== MALDIÇÕES ==========
maldicoes_ativas = {}
TIPOS_MALDICAO = {
    "latim": {"nome": "Maldição do Latim", "transformar": lambda txt: txt + "us dominus vobiscum"},
    "caipira": {"nome": "Maldição do Capiau", "transformar": lambda txt: txt + " uai sô"},
    "oposto": {"nome": "Maldição do Contrário", "transformar": lambda txt: txt.replace("sim", "não").replace("bom", "ruim")},
    "sussurro": {"nome": "Maldição do Sussurro", "transformar": lambda txt: f"||{txt}||"},
    "emoji": {"nome": "Maldição do Emoji", "transformar": lambda txt: " ".join([random.choice(["💀","👻","🔮","🐸","💨","🤡"]) for _ in txt.split()])},
    "gago": {"nome": "Maldição do Gago", "transformar": lambda txt: " ".join([w[0] + "-" + w if len(w) > 2 else w for w in txt.split()])},
    "grito": {"nome": "Maldição do Berro", "transformar": lambda txt: txt.upper() + "!!!"},
    "pirata": {"nome": "Maldição do Marujo", "transformar": lambda txt: txt.replace("você", "marujo").replace("sim", "arr") + " YARRR 🏴‍☠️"}
}

@bot.command(name="maldicao")
@commands.has_permissions(manage_messages=True)
async def maldicao(ctx, membro: discord.Member, tipo: str = None):
    if tipo is None or tipo not in TIPOS_MALDICAO:
        tipo = random.choice(list(TIPOS_MALDICAO.keys()))
    maldicoes_ativas[membro.id] = {"tipo": tipo, "expira": time.time() + 3600}
    await ctx.send(f"{membro.mention} foi amaldiçoado com {tipo}!")

@bot.command(name="desfazer")
@commands.has_permissions(manage_messages=True)
async def desfazer(ctx, membro: discord.Member):
    if membro.id in maldicoes_ativas:
        del maldicoes_ativas[membro.id]
        await ctx.send(f"{membro.mention} foi libertado!")
    else:
        await ctx.send("Não tá amaldiçoado.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.author.id in maldicoes_ativas:
        dados = maldicoes_ativas[message.author.id]
        if time.time() > dados["expira"]:
            del maldicoes_ativas[message.author.id]
        else:
            await message.delete()
            tipo = dados["tipo"]
            texto = TIPOS_MALDICAO[tipo]["transformar"](message.content)
            webhook = await message.channel.create_webhook(name=message.author.display_name)
            await webhook.send(texto, username=f"{message.author.display_name} Amaldiçoado", avatar_url=message.author.avatar.url)
            await webhook.delete()
            return
    await bot.process_commands(message)

import os
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
