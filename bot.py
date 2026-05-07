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

bot = commands.Bot(
    command_prefix="-",
    intents=intents,
    help_command=None
)

ARQUIVO_DB = "grimorios.json"
ARQUIVO_CONFIG = "config.json"
ARQUIVO_CONFIG_ENTRADA = "config_entrada.json"

invites_cache = {}
scheduler_rodando = False
HORARIO_OFF = False

# ========== DATABASE ==========
if os.path.exists(ARQUIVO_DB):
    with open(ARQUIVO_DB, "r", encoding="utf-8") as f:
        db = json.load(f)
else:
    db = {}

if os.path.exists(ARQUIVO_CONFIG):
    with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)
else:
    config = {"chance_4_trevos": 20}

if os.path.exists(ARQUIVO_CONFIG_ENTRADA):
    with open(ARQUIVO_CONFIG_ENTRADA, "r", encoding="utf-8") as f:
        config_entrada = json.load(f)
else:
    config_entrada = {}

# ========== FUNÇÕES ==========
def salvar_db():
    with open(ARQUIVO_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def salvar_config():
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def salvar_config_entrada():
    with open(ARQUIVO_CONFIG_ENTRADA, "w", encoding="utf-8") as f:
        json.dump(config_entrada, f, indent=4, ensure_ascii=False)

def get_user_data(user_id):
    uid = str(user_id)

    if uid not in db:
        db[uid] = {
            "grimorio": None,
            "roletas": 1
        }

    return db[uid]

async def verificar_horario(ctx):
    if HORARIO_OFF:
        await ctx.send("🌙 O grimório está descansando agora... volte mais tarde.")
        return True
    return False

# ========== AGENDADOR ==========
async def agendador_offline():
    global HORARIO_OFF

    await bot.wait_until_ready()

    fuso = pytz.timezone("America/Sao_Paulo")

    while not bot.is_closed():
        agora = datetime.now(fuso)
        hora = agora.hour

        if 1 <= hora < 8:
            HORARIO_OFF = True
        else:
            HORARIO_OFF = False

        await asyncio.sleep(1800)

# ========== EVENTOS ==========
@bot.event
async def on_ready():
    global scheduler_rodando

    print(f"✅ Bot conectado como {bot.user}")

    for guild in bot.guilds:
        try:
            invites_cache[guild.id] = await guild.invites()
        except:
            invites_cache[guild.id] = []

    if not scheduler_rodando:
        asyncio.create_task(agendador_offline())
        scheduler_rodando = True

@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)

    if guild_id not in config_entrada:
        return

    canal_id = config_entrada[guild_id]
    canal = member.guild.get_channel(canal_id)

    if not canal:
        return

    try:
        convites_antes = invites_cache.get(member.guild.id, [])
        convites_depois = await member.guild.invites()

        invites_cache[member.guild.id] = convites_depois

        convite_usado = None

        for convite in convites_antes:
            convite_novo = discord.utils.get(
                convites_depois,
                code=convite.code
            )

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

            embed.add_field(
                name="Convidado por",
                value=criador.mention,
                inline=True
            )

            embed.add_field(
                name="Código",
                value=f"`{convite_usado.code}`",
                inline=True
            )

            embed.add_field(
                name="Usos",
                value=f"`{convite_usado.uses}`",
                inline=True
            )

            embed.set_thumbnail(url=member.display_avatar.url)

            await canal.send(embed=embed)

        else:
            await canal.send(
                f"👋 {member.mention} entrou no servidor!"
            )

    except:
        await canal.send(
            f"👋 {member.mention} entrou no servidor!"
        )

@bot.event
async def on_invite_create(invite):
    try:
        invites_cache[invite.guild.id] = await invite.guild.invites()
    except:
        pass

@bot.event
async def on_invite_delete(invite):
    try:
        invites_cache[invite.guild.id] = await invite.guild.invites()
    except:
        pass

# ========== COMANDOS ==========

@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)

    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latência atual: `{latency}ms`",
        color=0x2ecc71
    )

    await ctx.send(embed=embed)
    
@bot.command(name="roleta")
async def roletar_grimorio(ctx):

    if await verificar_horario(ctx):
        return

    alvo = ctx.author
    user_data = get_user_data(alvo.id)

    if user_data["roletas"] <= 0:
        await ctx.send(
            f"{alvo.mention} não tem roletas disponíveis!"
        )
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
            description=(
                f"**Roletado para:** {alvo.mention}\n\n"
                "> Um grimório comum, mas com potencial infinito."
            ),
            color=0x95a5a6
        )

        embed.set_thumbnail(
            url="https://i.redd.it/j8z3k8rx42h31.png"
        )

        embed.set_footer(
            text=f"Chance: {chance_3}% | Restantes: {user_data['roletas']}"
        )

    else:

        embed = discord.Embed(
            title="🍀🍀 GRIMÓRIO DE 4 TREVOS! 🍀🍀",
            description=(
                f"**Roletado para:** {alvo.mention}\n\n"
                "> **LENDÁRIO!** Você foi escolhido pelo destino!"
            ),
            color=0xFFD700
        )

        embed.set_thumbnail(
            url="https://media.giphy.com/media/xT9IgzvnOyNDYnxeHS/giphy.gif"
        )

        embed.set_image(
            url="https://th.bing.com/th/id/OIP.ZLl9fnj-DfJdCFMqIPQFSAHaEG?r=0&o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3"
        )

        embed.set_footer(
            text=f"Chance: {chance_4}% | Restantes: {user_data['roletas']}"
        )

    embed.set_author(
        name="Sorteio de Grimórios",
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )

    await ctx.send(embed=embed)

@bot.command(name="grimorio")
async def ver_grimorio(ctx, membro: discord.Member = None):
    alvo = membro or ctx.author
    user_data = get_user_data(alvo.id)

    if user_data["grimorio"]:
        await ctx.send(
            f"🍀 Grimório de {alvo.mention}: "
            f"**{user_data['grimorio']}**\n"
            f"🎲 Roletas: **{user_data['roletas']}**"
        )
    else:
        await ctx.send(
            f"{alvo.mention} ainda não roletou.\n"
            f"🎲 Roletas: **{user_data['roletas']}**"
        )

@bot.command(name="rank")
async def rank_4_trevos(ctx):

    lendarios = [
        (uid, data["grimorio"])
        for uid, data in db.items()
        if data["grimorio"] == "4 Trevos"
    ]

    embed = discord.Embed(
        title="🏆 RANK DOS 4 TREVOS 🏆",
        color=0xFFD700
    )

    if not lendarios:
        embed.description = "Ninguém tirou 4 Trevos ainda 😢"
        await ctx.send(embed=embed)
        return

    texto_rank = ""

    for i, (user_id, _) in enumerate(lendarios[:10], 1):

        try:
            user = await bot.fetch_user(int(user_id))

            medalha = ""

            if i == 1:
                medalha = "🥇"
            elif i == 2:
                medalha = "🥈"
            elif i == 3:
                medalha = "🥉"

            texto_rank += f"{medalha} **{i}.** {user.mention}\n"

        except:
            texto_rank += f"**{i}.** Usuário desconhecido\n"

    embed.add_field(
        name="Escolhidos",
        value=texto_rank,
        inline=False
    )

    embed.set_footer(
        text=f"Total: {len(lendarios)} lendários"
    )

    await ctx.send(embed=embed)

@bot.command(name="chances")
async def ver_chances(ctx):

    chance_4 = config["chance_4_trevos"]
    chance_3 = 100 - chance_4

    embed = discord.Embed(
        title="📊 Chances Atuais",
        color=0x9b59b6
    )

    embed.add_field(
        name="🍀 4 Trevos",
        value=f"`{chance_4}%`",
        inline=True
    )

    embed.add_field(
        name="🍀 3 Trevos",
        value=f"`{chance_3}%`",
        inline=True
    )

    await ctx.send(embed=embed)

# ========== ADMIN ==========
@bot.command(name="setarchance")
@commands.has_permissions(administrator=True)
async def setar_chance(ctx, nova_chance: int):

    if nova_chance < 0 or nova_chance > 100:
        await ctx.send("Chance deve ser entre 0 e 100.")
        return

    config["chance_4_trevos"] = nova_chance

    salvar_config()

    await ctx.send(
        f"✅ Nova chance de 4 Trevos: **{nova_chance}%**"
    )

@bot.command(name="setroleta")
@commands.has_permissions(administrator=True)
async def set_roleta(ctx, alvo, quantidade: int):

    if quantidade < 0:
        await ctx.send("Não pode número negativo.")
        return

    # ===== CASO: TODO MUNDO =====
    if alvo.lower() == "all":

        membros_afetados = 0

        for membro in ctx.guild.members:
            if membro.bot:
                continue

            user_data = get_user_data(membro.id)
            user_data["roletas"] = quantidade
            membros_afetados += 1

        salvar_db()

        await ctx.send(
            content="@everyone",
            embed=discord.Embed(
                title="🎲 ROLETAS GLOBAL",
                description=(
                    f"Todos os membros receberam **{quantidade} roletas!**\n\n"
                    f"👥 Total afetados: {membros_afetados}"
                ),
                color=0x2ecc71
            )
        )

        return

    # ===== CASO: UM USUÁRIO =====
    membro = ctx.guild.get_member(
        int(alvo.replace("<@", "").replace(">", ""))
    )

    if not membro:
        await ctx.send("Usuário inválido ou não encontrado.")
        return

    user_data = get_user_data(membro.id)
    user_data["roletas"] = quantidade

    salvar_db()

    await ctx.send(
        embed=discord.Embed(
            title="🎲 Roletas Atualizadas",
            description=(
                f"{membro.mention} agora possui "
                f"**{quantidade}** roleta(s)!"
            ),
            color=0x2ecc71
        )
    )


@bot.command(name="tirar")
@commands.has_permissions(administrator=True)
async def tirar_grimorio(ctx, alvo):

    # ===== TODOS =====
    if alvo.lower() == "all":

        removidos = 0

        for membro in ctx.guild.members:

            if membro.bot:
                continue

            user_data = get_user_data(membro.id)

            if user_data["grimorio"] is not None:
                user_data["grimorio"] = None
                removidos += 1

        salvar_db()

        embed = discord.Embed(
            title="🗑️ Grimórios Removidos",
            description=(
                f"Todos os grimórios foram removidos.\n\n"
                f"👥 Total afetados: {removidos}"
            ),
            color=0xe74c3c
        )

        await ctx.send(
            content="@everyone",
            embed=embed
        )

        return

    # ===== USUÁRIO =====
    membro = ctx.guild.get_member(
        int(alvo.replace("<@", "").replace(">", ""))
    )

    if not membro:
        await ctx.send("Usuário inválido.")
        return

    user_data = get_user_data(membro.id)

    user_data["grimorio"] = None

    salvar_db()

    embed = discord.Embed(
        title="🗑️ Grimório Removido",
        description=(
            f"O grimório de {membro.mention} foi removido."
        ),
        color=0xe74c3c
    )

    await ctx.send(embed=embed)
    
@bot.command(name="setcanalentrada")
@commands.has_permissions(administrator=True)
async def set_canal_entrada(
    ctx,
    canal: discord.TextChannel
):

    config_entrada[str(ctx.guild.id)] = canal.id

    salvar_config_entrada()

    await ctx.send(
        f"✅ Canal de entrada definido para {canal.mention}"
    )

@bot.command(name="helpgrimorio")
async def help_grimorio(ctx):

    embed = discord.Embed(
        title="📜 Comandos do Bot",
        color=0x9b59b6
    )

    embed.add_field(
        name="🎮 Usuários",
        value=(
            "`-roleta`\n"
            "`-grimorio`\n"
            "`-rank`\n"
            "`-chances`\n"
            "`-ping`\n"
            "`-brabo`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️ Admin",
        value=(
            "`-setarchance 30`\n"
            "`-setroleta @user 3`\n"
            "`-setcanalentrada #canal`"
            "`-tirar @user`/"
        ),
        inline=False
    )

    embed.set_footer(
        text="🍀 Sistema de Grimórios"
    )

    await ctx.send(embed=embed)

@bot.command(name="brabo")
async def brabo(ctx, membro: discord.Member = None):

    if membro:

        if membro.id == ctx.author.id:
            await ctx.send(
                f"😎 {ctx.author.mention} mandou um salve!"
            )

        else:
            await ctx.send(
                f"🔥 O niight é melhor que você, "
                f"{membro.mention} 😂☠️"
            )

    else:
        await ctx.send(
            f"😎 {ctx.author.mention} mandou um salve!"
        )

# ========== ERROS ==========
@setar_chance.error
@set_roleta.error
@set_canal_entrada.error
@tirar.error
async def admin_error(ctx, error):

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Só administradores podem usar isso."
        )

# ========== INICIAR BOT ==========
TOKEN = os.getenv("DISCORD_TOKEN")

bot.run(TOKEN)
