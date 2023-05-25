import os
import csv
import requests
import discord
from discord.ext import commands, tasks
from discord.ext.commands.context import Context
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
API_TOKEN = os.getenv('API_TOKEN')
API_URL = os.getenv('API_URL')
API_SERVER_ID = os.getenv('API_SERVER_ID')

mods_csv = "mods.csv"
channels_ids = []
headers = {
    'Accept': 'application/json',
    'Authorization': 'Bearer '+API_TOKEN
}
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


def get_mods():
    response = requests.get(API_URL+API_SERVER_ID +
                            '/files/list?directory=%2Fmods', headers=headers)
    mods_atuais = response.json()['data']
    mods = []
    for mod in mods_atuais:
        name = mod.get('attributes').get('name')
        if name:
            mods.append(name)
    return sorted(mods, key=str.lower)


def mods_to_string(mods):
    response = ['']
    for mod in mods:
        if len(response[-1]) + len(mod) + 1 < 2000:
            response[-1] += mod + '\n'
        else:
            response.append(mod + '\n')
    return response


async def foreach_send(ctx: Context, response):
    for res in response:
        if res and len(res) > 0:
            await ctx.send(res)


def get_diff():
    mods = get_mods()
    try:
        dic = dict()
        mods_antigos: list[str] = []
        with open(mods_csv, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                mods_antigos.append(row[0])
            removed: list[str] = []
            for mod in mods_antigos:
                if mod not in mods:
                    removed.append(mod)
            added: list[str] = []
            for mod in mods:
                if mod not in mods_antigos:
                    added.append(mod)
            dic['removed'] = removed
            dic['added'] = added
        with open(mods_csv, "w", newline="") as file:
            writer = csv.writer(file)
            for mod in mods:
                writer.writerow([mod])
        return dic
    except FileNotFoundError:
        with open(mods_csv, "w", newline="") as file:
            writer = csv.writer(file)
            for mod in mods:
                writer.writerow([mod])


async def send_diff(ctx: Context, dif, command=True):
    if dif is not None:
        removed = dif.get('removed')
        added = dif.get('added')
        if len(removed) > 0 or len(added):
            if len(removed) > 0:
                await ctx.send(f'Mods removidos:\n')
                await foreach_send(ctx, mods_to_string(removed))
            if len(added) > 0:
                await ctx.send(f'Mods adicionados:\n')
                await foreach_send(ctx, mods_to_string(added))
        else:
            if command:
                await ctx.send("Não houve diferença desde a última execução do comando")
    else:
        if command:
            await ctx.send("Primeira execução do comando, não há comparativo")


@bot.command()
async def mods(ctx: Context):
    await foreach_send(ctx, mods_to_string(get_mods()))


@bot.command()
async def diff(ctx: Context):
    await send_diff(ctx, get_diff())


@tasks.loop(seconds=60)
async def verificar_mods():
    dif = get_diff()
    for channel_id in channels_ids:
        channel = bot.get_channel(channel_id)
        await send_diff(channel, dif)

bot.remove_command('help')


@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="Comandos Bot None",  color=discord.Color.blue())
    embed.add_field(
        name="!mods", value="Lista os mods do servidor.", inline=False)
    embed.add_field(name="!diff", value="Exibe a diferença de mods desde a última execução do comando.",
                    inline=False)
    embed.add_field(name="!add_channel", value="Adiciona o canal atual para receber as notificações de diferença de mods.",
                    inline=False)
    embed.add_field(name="!remove_channel", value="Remove o canal atual para receber as notificações de diferença de mods.",
                    inline=False)
    embed.add_field(
        name="!help", value="Exibe a lista de comandos disponíveis.", inline=False)
    await ctx.send(embed=embed)


@bot.command()
async def add_channel(ctx: Context):
    if ctx.channel.id not in channels_ids:
        channels_ids.append(ctx.channel.id)
        await ctx.send('Canal adicionado')
    else:
        await ctx.send('Canal já adicionado')


@bot.command()
async def remove_channel(ctx: Context):
    if ctx.channel.id in channels_ids:
        channels_ids.remove(ctx.channel.id)
        await ctx.send('Canal removido')
    else:
        await ctx.send('Canal não adicionado')


@bot.event
async def on_ready():
    verificar_mods.start()
    print(f'Bot conectado como {bot.user.name}')

bot.run(DISCORD_TOKEN)
