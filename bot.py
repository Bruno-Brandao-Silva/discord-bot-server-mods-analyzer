import os
import csv
import requests
import discord
from discord.ext import commands
from discord.ext.commands.context import Context
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
API_TOKEN = os.getenv('API_TOKEN')
API_URL = os.getenv('API_URL')
API_SERVER_ID = os.getenv('API_SERVER_ID')

nome_arquivo = "mods.csv"

headers = {
    'Accept': 'application/json',
    'Authorization': 'Bearer '+API_TOKEN
}
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


def get_mods():
    response = requests.get(
        API_URL+API_SERVER_ID+'/files/list?directory=%2Fmods', headers=headers)
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


@bot.command()
async def ajuda(ctx):
    await ctx.send('!mods - Lista os mods atuais\n!dif - Lista os mods adicionados e removidos desde a última vez que o comando foi executado')


@bot.command()
async def mods(ctx: Context):
    await foreach_send(ctx, mods_to_string(get_mods()))


@bot.command()
async def dif(ctx: Context):
    mods = get_mods()
    try:
        with open(nome_arquivo, "r") as arquivo:
            reader = csv.reader(arquivo)
            mods_antigos: list[str] = []
            for row in reader:
                mods_antigos.append(row[0])
            removidos: list[str] = []
            for mod in mods_antigos:
                if mod not in mods:
                    removidos.append(mod)
            adicionados: list[str] = []
            for mod in mods:
                if mod not in mods_antigos:
                    adicionados.append(mod)
            if len(removidos) > 0:
                await ctx.send(f'Mods removidos:\n')
                await foreach_send(ctx, mods_to_string(removidos))
            if len(adicionados) > 0:
                await ctx.send(f'Mods adicionados:\n')
                await foreach_send(ctx, mods_to_string(adicionados))
    except FileNotFoundError:
        with open(nome_arquivo, "w", newline="") as arquivo:
            writer = csv.writer(arquivo)
            for mod in mods:
                writer.writerow([mod])


@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user.name}')

bot.run(DISCORD_TOKEN)
