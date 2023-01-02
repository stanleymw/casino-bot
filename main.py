from typing import Optional
import time
import discord
import random
import asyncio
import logging
import datetime
from discord import app_commands
from discord.ext import tasks
import json

LOG_HANDLER = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

casinoTokens = {}
lastWorked = {}
lastInvested = {}

STARTER_TOKENS = 1000
WORKCOOLDOWN =90# -> 5 minutes
TOKEN = open("token.txt").read().strip()

MY_GUILD = discord.Object(id=910728368641679400)  # replace with your guild id


def saveDict(d, filename):
    js = json.dumps(d)
    f = open(f"savedata/{filename}.json","w")
    f.write(js)
    f.close()
    print(f"{filename} data saved!")

def loadDict(filename):
    f = open(f"savedata/{filename}.json")
    dat = {int(i):v for i,v in json.load(f).items()}
    print(filename,"data loaded!")
    f.close()
    return dat

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        # A CommandTree is a special type that holds all the application command
        # state required to make it work. This is a separate class because it
        # allows all the extra state to be opt-in.
        # Whenever you want to work with application commands, your tree is used
        # to store and work with them.
        # Note: When using commands.Bot instead of discord.Client, the bot will
        # maintain its own tree instead.
        self.tree = app_commands.CommandTree(self)

    def loadSaveData(self):
        #f = open("savedata/tokens.json")
        global casinoTokens
        casinoTokens = loadDict("tokens")
        global lastInvested
        lastInvested = loadDict("investments")
        return


    # In this basic example, we just synchronize the app commands to one guild.
    # Instead of specifying a guild to every command, we copy over our global commands instead.
    # By doing so, we don't have to wait up to an hour until they are shown to the end-user.
    async def setup_hook(self):
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
        self.loadSaveData()
        self.saveValues.start()



    @tasks.loop(seconds=30) 
    async def saveValues(self):
        # js = json.dumps(casinoTokens)
        # f = open("savedata/tokens.json","w")
        # f.write(js)
        # f.close()
        # print("Token Data Saved!")
        saveDict(casinoTokens, "tokens")
        saveDict(lastInvested, "investments")
        
    @saveValues.before_loop
    async def beforeTokenSave(self):
        await self.wait_until_ready()  # wait until the bot logs in

intents = discord.Intents.default()
intents.message_content = True
client = MyClient(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')

# To make an argument optional, you can either give it a supported default argument
# or you can mark it as Optional from the typing standard library. This example does both.
@client.tree.command()
@app_commands.describe(member='The member you want to get the joined date from; defaults to the user who uses the command')
async def joined(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    """Says when a member joined."""
    # If no member is explicitly provided then we use the command user here
    member = member or interaction.user

    # The format_dt function formats the date time into a human readable representation in the official client
    await interaction.response.send_message(f'{member} joined {discord.utils.format_dt(member.joined_at)}')

async def sendMsg(interaction: discord.Interaction,msg):
    await interaction.reponse.send_message(msg)
@client.tree.command()
@app_commands.describe(bet='Amount of tokens to bet.')
async def coinflip(interaction: discord.Interaction, bet: int):
    """Gamble your tokens in a coin flip."""
    uid = interaction.user.id 
    if uid not in casinoTokens:
        casinoTokens[uid] = STARTER_TOKENS
    if bet > casinoTokens[uid]:
        await interaction.response.send_message(f'You only have {casinoTokens[uid]} tokens! You cannot bet this much.')
        return
    if bet <= 0:
        await interaction.response.send_message("You must bet more than 0 tokens.")
        return
    oldTokens = casinoTokens[uid]
    casinoTokens[uid] -= bet
    await interaction.response.send_message(f"Flipping coin... ({bet} tokens)")
    roll = random.uniform(0.0, 100.0)	

    res = discord.Embed(color=discord.Colour.red(), title="coinflip", description="descriptoin")
    res.set_author(name=interaction.user)
    # time.sleep(3)
    await asyncio.sleep(3)
    if roll >= 50:
        casinoTokens[uid] += 2 * bet
        res.title = "You Win!" 
        res.color = discord.Colour.green()
    else:
        res.title = "You Lose!"
    res.description = f"You now have {casinoTokens[uid]} tokens!\n{oldTokens} -> {casinoTokens[uid]} ({casinoTokens[uid] - oldTokens})"
    res.set_footer(text=f"Roll: {roll}")
    await interaction.edit_original_response(embed=res)

@client.tree.command()
async def tokens(interaction: discord.Interaction):
    """See how many tokens you have."""
    # If no member is explicitly provided then we use the command user here

    uid = interaction.user.id 

    if uid not in casinoTokens:
        casinoTokens[uid] = STARTER_TOKENS
    # The format_dt function formats the date time into a human readable representation in the official client
    await interaction.response.send_message(f"You have {casinoTokens[uid]} tokens.")

@client.tree.command()
@app_commands.describe(member='User to donate to', amount='Amount of tokens to donate')
async def donate(interaction: discord.Interaction, member: discord.Member, amount: int):
    """Transfer tokens to another user"""
    donorUid = interaction.user.id 
    recUid = member.id
    if donorUid not in casinoTokens:
        casinoTokens[donorUid] = STARTER_TOKENS
    if recUid not in casinoTokens:
        casinoTokens[recUid] = STARTER_TOKENS
    if amount > casinoTokens[donorUid]:
        interaction.response.send_message(f"You cannot donate {amount} tokens, you only have {casinoTokens[donorUid]} tokens!")
        return
    if amount <= 0:
        interaction.response.send_message("You must donate more than 0 tokens")
        return

    casinoTokens[donorUid] -= amount
    casinoTokens[recUid] += amount
    
    
    await interaction.response.send_message(f"You have donated {amount} tokens to {member}! You now have {casinoTokens[donorUid]} tokens.")



@client.tree.command()
async def leaderboard(interaction: discord.Interaction):
    """View a list of the users with the most tokens."""

    res = discord.Embed(color=discord.Colour.blue(), title="Points Leaderboard")
    desc = ""
    lb = sorted(casinoTokens.items(), key=lambda x: x[1], reverse=True)

    #print(lb)
    for i in range(min(len(lb), 10)):
        desc += f"{i+1}. <@{lb[i][0]}> -> {lb[i][1]} Tokens\n"
    
    res.description = desc
    if desc == "":
        res.description = "Empty!"
    
    await interaction.response.send_message(embed=res)


@client.tree.command()
@app_commands.describe(bet='Amount of tokens to bet.', multiplier='The amount your money will be multiplied, your chance of winning will be calculated off of this.')
async def customflip(interaction: discord.Interaction, bet: int, multiplier: int):
    """Coin flip, but with custom odds. Lower chance = higher multiplier."""
    uid = interaction.user.id 
    if uid not in casinoTokens:
        casinoTokens[uid] = STARTER_TOKENS
    if bet > casinoTokens[uid]:
        await interaction.response.send_message(f'You only have {casinoTokens[uid]} tokens! You cannot bet this much.')
        return
    if bet <= 0:
        await interaction.response.send_message("You must bet more than 0 tokens.")
        return
    if multiplier <= 1:
        await interaction.response.send_message("Your multiplier must be more than 1x")
    oldTokens = casinoTokens[uid]
    casinoTokens[uid] -= bet
    await interaction.response.send_message(f"Flipping coin... ({bet} tokens)")
    roll = random.uniform(0.0, 100.0)	
    winchance = 100/multiplier
    res = discord.Embed(color=discord.Colour.red(), title="coinflip", description="descriptoin")
    res.set_author(name=interaction.user)
    # time.sleep(3)
    await asyncio.sleep(3)
    if roll <= winchance:
        casinoTokens[uid] += multiplier * bet
        res.title = f"You Win! ({multiplier}x Multiplier)" 
        res.color = discord.Colour.green()
    else:
        res.title = "You Lose!"
    res.description = f"You now have {casinoTokens[uid]} tokens!\n{oldTokens} -> {casinoTokens[uid]} ({casinoTokens[uid] - oldTokens})"
    res.set_footer(text=f"Roll: {roll} | Roll Required: < {winchance}")
    await interaction.edit_original_response(embed=res)


@client.tree.command()
@app_commands.describe(bet='Amount of tokens to bet.', players='How many players are in the battle.')
async def battle(interaction: discord.Interaction, bet: int, players: Optional[int] = 2):
    """Create a multiplayer coinflip."""
    uid = interaction.user.id 
    if uid not in casinoTokens:
        casinoTokens[uid] = STARTER_TOKENS
    if bet > casinoTokens[uid]:
        await interaction.response.send_message(f'You only have {casinoTokens[uid]} tokens! You cannot bet this much.')
        return
    if bet <= 0:
        await interaction.response.send_message("You must bet more than 0 tokens.")
        return
    oldTokens = casinoTokens[uid]
    casinoTokens[uid] -= bet
    numPlayersRequired = players
    players = [interaction.user]

    joinbtn = discord.ui.Button(style=discord.ButtonStyle.green, label="Join Battle")
    cancelbtn = discord.ui.Button(style=discord.ButtonStyle.red, label="Cancel Battle")
    res = discord.Embed(color=discord.Colour.blue(), title=f"Coinflip Battle ({numPlayersRequired} players)", description=f"Wager: {bet} tokens")
    
    async def onButtonPress(i: discord.Interaction):
        if (len(players) >= numPlayersRequired):
            await i.response.send_message(f'{i.user}, this battle is full.', ephemeral=True)
            return
        joiner = i.user.id
        if joiner not in casinoTokens:
            casinoTokens[joiner] = STARTER_TOKENS
        if bet > casinoTokens[joiner]:
            await i.response.send_message(f'{i.user}, you do not have enough tokens to join this battle.', ephemeral=True)
            return
        if i.user in players:
            await i.response.send_message(f'{i.user}, you have already joined this battle.', ephemeral=True)
            return
        casinoTokens[joiner] -= bet
        players.append(i.user)
        await i.response.send_message(f'{i.user} has joined this battle!')

        res.set_field_at(0, name=f"Players ({len(players)}/{numPlayersRequired})", value=("\n".join([i.name for i in players]))) 
        await interaction.edit_original_response(embed=res)

    battleCanceled = False
    async def cancelButtonPressed(i: discord.Interaction):
        joiner = i.user.id
        if joiner != uid:
            await i.response.send_message(f'{i.user}, only the creator of this battle ({interaction.user.name}) can cancel this battle.', ephemeral=True)
            return
        if len(players) >= numPlayersRequired:
            await i.response.send_message("You cannot cancel a battle that has started")
            return
        battleCanceled = True 
        for player in players:
            casinoTokens[player.id] += bet
            # refund everyones money
        await interaction.edit_original_response(content="", embed=discord.Embed(color=discord.Colour.red(), title="Battle Canceled"), view=discord.ui.View())
    
    joinbtn.callback = onButtonPress
    cancelbtn.callback = cancelButtonPressed
    v = discord.ui.View()
    v.add_item(joinbtn)
    v.add_item(cancelbtn)

    res.add_field(name=f"Players ({len(players)}/{numPlayersRequired})", value=("\n".join([i.name for i in players])))
    
    await interaction.response.send_message(f"Waiting for players...", view = v, embed=res)

    while (len(players) < numPlayersRequired):
        if (battleCanceled):
            print("BATTLE STOPPED.")
            return "ASD"
        await asyncio.sleep(1)

    await interaction.edit_original_response(content="Battle Started! Flipping Coin...", view=discord.ui.View(), embed=res)
    #roll = random.uniform(0.0, 100.0)	
    #(0 -> 33.33, 1-> 66.666, 2-> 100)
    #sepAmount = 100/numPlayersRequired
    #winner = None
    # #for i,v in enumerate(players):
    #     if ((i) * sepAmount <= roll) and (roll < (i+1) * sepAmount):
    #         winner = v
    #         break
    # if winner == None:
    #     winner = players[0]
    await asyncio.sleep(3)
    winner = random.choice(players)
    res.add_field(name="Winner",value=f"{winner.name}")
    casinoTokens[winner.id] += numPlayersRequired * bet
    res.description = f"<@{winner.id}> has won {numPlayersRequired*bet} tokens!"
    await interaction.edit_original_response(content=f"{winner.name} has won!",embed=res)
    # roll = random.uniform(0.0, 100.0)	
    # winchance = 100/multiplier
    # res = discord.Embed(color=discord.Colour.red(), title="coinflip", description="descriptoin")
    # res.set_author(name=interaction.user)
    # time.sleep(3)
    # if roll <= winchance:
    #     casinoTokens[uid] += multiplier * bet
    #     res.title = f"You Win! ({multiplier}x Multiplier)" 
    #     res.color = discord.Colour.green()
    # else:
    #     res.title = "You Lose!"
    # res.description = f"You now have {casinoTokens[uid]} tokens!\n{oldTokens} -> {casinoTokens[uid]} ({casinoTokens[uid] - oldTokens})"
    # res.set_footer(text=f"Roll: {roll} | Roll Required: < {winchance}")
    # await interaction.edit_original_response(embed=res)



@client.tree.command()
async def work(interaction: discord.Interaction):
    """Do some work for tokens."""

    uid = interaction.user.id
    if uid not in casinoTokens:
        casinoTokens[uid] = STARTER_TOKENS
    if uid not in lastWorked:
        lastWorked[uid] = 0

    if (time.time() - lastWorked[uid] < WORKCOOLDOWN):
        nextAvailableAt = datetime.datetime.fromtimestamp(lastWorked[uid]+WORKCOOLDOWN)
        secondsRemaining = (lastWorked[uid] + WORKCOOLDOWN) - time.time()
        await interaction.response.send_message(f"{interaction.user}, you cannot work so fast. You can work next at {discord.utils.format_dt(nextAvailableAt)} ({secondsRemaining:.1f} seconds left)")
        return
    lastWorked[uid] = time.time()
    num1 = random.randint(2, 20)
    num2 = random.randint(2, 20)
    ans = num1*num2

    def check(msg):
        return msg.author.id == uid and msg.channel == interaction.channel
    
    await interaction.response.send_message(f"What is the value of {num1} * {num2}?")

    startTime = time.time()
    numTries = 0
    # 1500 - numTries * 100
    # 2000 - 3**numTries
    while True:
        if (numTries > 5):
            await msg.channel.send("You have taken too many tries. Better luck next time.")
            break
        msg = await client.wait_for("message", check=check)
        if not (msg.content.isnumeric()):
            await msg.channel.send(content="That is not a number!")
        elif int(msg.content) != ans:
            numTries += 1
            await msg.channel.send(f"Incorrect Answer! You have made {numTries} attempts.")
        elif int(msg.content) == ans:
            timeTaken = time.time() - startTime
            amountEarned = (2000 - (2.7 ** timeTaken)) * (0.5**numTries)
            amountEarned = max(0, amountEarned)
            amountEarned = int(amountEarned)
            casinoTokens[uid] += amountEarned
            await msg.channel.send(f"Correct! You have solved the problem in {numTries} attempts in {timeTaken:.1f} seconds. You have earned: {amountEarned} tokens!")
            break



@client.tree.command()
@app_commands.describe(bet='Amount of tokens to bet.', multiplier='The multiplier that you want to cash out at.')
async def crash(interaction: discord.Interaction, bet: int, multiplier: float):
    """Select a multiplier to multiply your bet by. The bot will generate a random multiplier, and if your multiplier is lower then you get the money. Your multiplier will round to 2 decimal places."""
    uid = interaction.user.id
    if uid not in casinoTokens:
        casinoTokens[uid] = STARTER_TOKENS
    if bet > casinoTokens[uid]:
        await interaction.response.send_message(f'You only have {casinoTokens[uid]} tokens! You cannot bet this much.')
        return
    if bet <= 0:
        await interaction.response.send_message("You must bet more than 0 tokens.")
        return
    if multiplier <= 1:
        await interaction.response.send_message("Your multiplier must be more than 1x")
        return

    multiplier = round(multiplier, 2)
    oldTokens = casinoTokens[uid]
    casinoTokens[uid] -= bet

    await interaction.response.send_message(f"Selecting Crash Value... (Your Multiplier: {multiplier}) (Bet: {bet})")
    roll = random.uniform(0, 1)
    if roll == 0:
        roll = 1
    selectedMultiplier = 1/roll
    selectedMultiplier = round(selectedMultiplier, 2)
    res = discord.Embed(color=discord.Colour.red(), title="Crash", description="descriptoin")
    res.set_author(name=interaction.user)
    await asyncio.sleep(3)
    if multiplier <= selectedMultiplier:
        casinoTokens[uid] += int(multiplier * bet)
        res.title = f"You Win! ({multiplier}x Multiplier)" 
        res.color = discord.Colour.green()
    else:
        res.title = "You Lose!"
    res.description = f"Generated Multiplier -> {selectedMultiplier}\nYou now have {casinoTokens[uid]} tokens!\n{oldTokens} -> {casinoTokens[uid]} ({casinoTokens[uid] - oldTokens})"
    res.set_footer(text=f"Roll: {roll} | Generated Mult: {selectedMultiplier}")
    await interaction.edit_original_response(embed=res)



client.run(TOKEN, log_handler=LOG_HANDLER, log_level=logging.DEBUG)