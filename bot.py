import os
import csv
import time
import requests
import discord
from discord import app_commands, Interaction, TextChannel
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
API_TOKEN = os.getenv('API_TOKEN')
API_URL = os.getenv('API_URL')
API_SERVER_ID = os.getenv('API_SERVER_ID')

link_mods = "https://drive.google.com/drive/folders/1V4LsGFEDsSyoVcu-Xa7WvYfhWHmXbUyA"
mods_csv = "mods.csv"
channels_csv = "channels.csv"
channels_ids = []
headers = {
    'Accept': 'application/json',
    'Authorization': 'Bearer '+API_TOKEN
}
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

try:
    with open(channels_csv, newline='') as file:
        reader = csv.reader(file)
        for row in reader:
            channels_ids.append(int(row[0]))
except FileNotFoundError:
    with open(channels_csv, "w", newline="") as file:
        pass


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
    for i in range(len(mods)):
        if len(response[-1]) + len(mods[i]) + 1 < 1024:
            response[-1] += f"{i+1}# {mods[i]}\n"
        else:
            response.append(f"{i+1}# {mods[i]}\n")
    return response


def embed_res(embed: discord.Embed, response):
    for res in response:
        embed.add_field(name=f"", value=res, inline=False)


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


async def send_diff(interaction: Interaction | TextChannel, dif, command=True):
    if dif is not None:
        removed = dif.get('removed')
        added = dif.get('added')
        if len(removed) > 0 or len(added) > 0:
            embeds = []
            if len(added) > 0:
                embed_add = discord.Embed(
                    title="Mods adicionados", color=discord.Color.green())
                embed_res(embed_add, mods_to_string(added))
                embeds.append(embed_add)
            if len(removed) > 0:
                embed_rem = discord.Embed(
                    title="Mods removidos", color=discord.Color.red())
                embed_res(embed_rem, mods_to_string(removed))
                embeds.append(embed_rem)
            embeds.append(discord.Embed(
                title="Pasta mods atuliaza disponível em:",
                description=link_mods,
                color=discord.Color.blue()
            ))
            if type(interaction) is Interaction:
                await interaction.response.send_message(embeds=embeds)
            else:
                await interaction.send(embeds=embeds)
        else:
            if command:
                await interaction.response.send_message("Não houve diferença desde a última execução do comando")
    else:
        if command:
            await interaction.response.send_message("Primeira execução do comando, não há comparativo")


@tree.command(name="help", description="Exibe a lista de comandos disponíveis.")
async def help(interaction: Interaction):
    embed = discord.Embed(
        title="Comandos Bot None",  color=discord.Color.blue())
    embed.add_field(
        name="/mods", value="Lista os mods do servidor.", inline=False)
    embed.add_field(name="/diff", value="Exibe a diferença de mods desde a última execução do comando.",
                    inline=False)
    embed.add_field(name="/add_channel", value="Adiciona o canal atual para receber as notificações de diferença de mods.",
                    inline=False)
    embed.add_field(name="/remove_channel", value="Remove o canal atual para receber as notificações de diferença de mods.",
                    inline=False)
    embed.add_field(
        name="/help", value="Exibe a lista de comandos disponíveis.", inline=False)
    await interaction.response.send_message(embed=embed)


@tree.command(name="mods", description="Lista os mods do servidor.")
async def mods(interaction: Interaction):
    mods = get_mods()
    embed = discord.Embed(title="Mods", color=discord.Color.blue())
    embed.add_field(name=f"Quantidade: {len(mods)}", value="", inline=False)
    embed_res(embed, mods_to_string(mods))
    await interaction.response.send_message(embeds=[embed, discord.Embed(
        title="Pasta mods atuliaza disponível em:",
        description=link_mods,
        color=discord.Color.blue()
    )])


@tree.command(name="diff", description="Exibe a diferença de mods desde a última execução do comando.")
async def diff(interaction: Interaction):
    await send_diff(interaction, get_diff())


@tree.command(name="add_channel", description="Adiciona o canal atual para receber as notificações de diferença de mods.")
async def add_channel(interaction: Interaction):
    channel = client.get_channel(interaction.channel.id)
    if channel is None:
        await interaction.response.send_message('Canal inválido')
    else:
        if interaction.channel.id not in channels_ids:
            channels_ids.append(interaction.channel.id)
            with open(channels_csv, "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([interaction.channel.id])
            await interaction.response.send_message('Canal adicionado')
        else:
            await interaction.response.send_message('Canal já adicionado')


@tree.command(name="remove_channel", description="Remove o canal atual para receber as notificações de diferença de mods.")
async def remove_channel(interaction: Interaction):
    if interaction.channel.id in channels_ids:
        channels_ids.remove(interaction.channel.id)
        # remove from csv
        with open(channels_csv, "w", newline="") as file:
            writer = csv.writer(file)
            for channel_id in channels_ids:
                writer.writerow([channel_id])
        await interaction.response.send_message('Canal removido')
    else:
        await interaction.response.send_message('Canal não adicionado')

dif = None
dif2 = None


@tasks.loop(seconds=10)
async def verficar_dif_continuos():
    global dif
    global dif2
    if dif is None:
        dif = get_diff()
    elif len(dif.get('added')) > 0 or len(dif.get('removed')) > 0:
        dif2 = get_diff()
        if len(dif2.get('added')) > 0 or len(dif2.get('removed')) > 0:
            dif['added'] = dif['added'] + dif2['added']
            dif['removed'] = dif['removed'] + dif2['removed']
            dif2 = None
        else:
            for channel_id in channels_ids:
                channel = client.get_channel(channel_id)
                if channel is not None:
                    await send_diff(channel, dif, False)
            dif = None
            dif2 = None
            verficar_dif_continuos.stop()
    else:
        dif = None
        dif2 = None
        verficar_dif_continuos.stop()


@tasks.loop(seconds=60)
async def verificar_dif():
    if not verficar_dif_continuos.is_running():
        verficar_dif_continuos.start()


@client.event
async def on_ready():
    await tree.sync()
    verificar_dif.start()

client.run(DISCORD_TOKEN)
