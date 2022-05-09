from riotwatcher import LolWatcher
import os
import discord
from discord.ext import commands
from champions import get_champions_name
from datetime import datetime
from dateutil import tz
import asyncio

#replace "os.environ['KEY']" with your own riot api key
api_key = os.environ['KEY']

watcher = LolWatcher(api_key)
my_region = "na1"


class Stats():
		def get_stats(username):

				#gets base summoner data
				me = watcher.summoner.by_name(my_region, username)

				#gets ranked playlist data
				stats = watcher.league.by_summoner(my_region, me['id'])

				embed = discord.Embed(title="{}".format(me['name']),
															url="https://na.op.gg/summoners/na/{}".format(
																	me['name'].replace(' ', '%20')), color = discord.Color.blurple())

				# building embed fields
				for i in range(len(stats)):
						data = stats[i]
						rank = data['tier'] + " " + data['rank']
						lp = data['leaguePoints']
						wins = data['wins']
						losses = data['losses']
						wr = (int(wins) / (int(wins) + int(losses))) * 100
						if data['queueType'] == 'RANKED_SOLO_5x5':
								playlist = 'Solo/Duo: '
								wr_name = 'Solo Duo W/L'

						else:
								playlist = 'Flex: '
								wr_name = 'Flex W/L: '

						embed.add_field(name=playlist,
														value=f"```{rank} {lp}LP```",
														inline=True)
						embed.add_field(name=wr_name,
														value="```{}/{} ({:.1f}%)```".format(wins, losses, wr),
														inline=False)

				return embed

		# Returns top 5 champs by mastery
		def get_mastery(username):
				me = watcher.summoner.by_name(my_region, username)
				mastery = watcher.champion_mastery.by_summoner(my_region, me['id'])
				champs = []
				names = []

				embed = discord.Embed(
						title="{}'s Top Champions".format(me['name']),
						url="https://na.op.gg/summoners/na/{}/champions".format(
								me['name'].replace(' ', '%20')))

				#Change the range for how many champs are displayed
				for i in range(5):
						champs.append(mastery[i])

				for i in champs:
						ID = i['championId']
						names.append(get_champions_name(ID))

				for i in range(len(champs)):
						embed.add_field(name=names[i],
														value="```css\nLevel: {}\nMastery Score: {:,}\n```".format(
																champs[i]['championLevel'],
																champs[i]['championPoints']),
														inline=False)

				return embed

		# Returns upcoming clash dates
		def get_clash():
				date_list = []
				clash = watcher.clash.tournaments(my_region)
				embed = discord.Embed(
						title='Upcoming Clash Tournaments',
						url=
						"https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-2022-clash-schedule/"
				)
				to_zone = tz.gettz('America/New_York')

				for i in clash:
						registration = i['schedule'][0]
						start_time = int(registration['startTime']) / 1000
						date = datetime.fromtimestamp(start_time, to_zone)
						date_string = date.strftime('%m-%d-%Y')
						date_list.append(date_string)

				date_list.sort()
				list_to_string = ''
				for days, i in enumerate(date_list):
						if days % 2 == 1:
								pass
						else:
								list_to_string += 'Weekend of {}\n'.format(i)

				embed.add_field(name='Tournaments by Date: ',
												value=f'```css\n{list_to_string}\n```',
												inline=False)

				return embed


class Commands(commands.Cog):
		def __init__(self, bot: commands.Bot):
				self.bot = bot
				self.voice_states = {}

		async def cog_command_error(self, ctx: commands.Context,
																error: commands.CommandError):
				await ctx.send('An error occurred: {}'.format(str(error)))

		@commands.command(name='stats')
		async def __getStats(self, ctx, *, arg):
				"""Get Summoner Stats"""
				username = arg

				await ctx.send(embed=Stats.get_stats(username))

		@commands.command(name='mastery')
		async def __getMastery(self, ctx, *, arg):
				"""Get Champion Mastery of Summoner"""
				username = arg

				await ctx.send(embed=Stats.get_mastery(username))

		@commands.command(name='clash')
		async def __getClash(self, ctx):
				"""Get Upcoming Clash Tournament Dates"""
				await ctx.send(embed=Stats.get_clash())

		@commands.command(name='challenger')
		async def __getChallenger(self, ctx):
				"""Get Top Challenger Players"""
				challenger_stats = watcher.league.challenger_by_queue(
						my_region, 'RANKED_SOLO_5x5')
				player_stats = {}
				for i in challenger_stats['entries']:
						name = i['summonerName']
						lp = i['leaguePoints']
						player_stats[name] = lp
				ordered_players = dict(
						sorted(player_stats.items(),
									 key=lambda item: item[1],
									 reverse=True))

				string = ''
				pages = []
				for rank, (player, lp) in enumerate(ordered_players.items(), 1):
						string += '{}. \"{}\" is at {} LP\n'.format(rank, player, lp)
					
						if rank % 10 == 0:
								pages.append(
										discord.Embed(
												title='Top Solo/Duo Players:',
												url=
												"https://www.leagueofgraphs.com/rankings/summoners/na",
												description=f'{string}'))
								string = ''
								
				# skip to start, left, right, skip to end
				buttons = [u"\u23EA", u"\u2B05", u"\u27A1", u"\u23E9"]
				current = 0
				msg = await ctx.send(embed=pages[current])

				for button in buttons:
						await msg.add_reaction(button)

				while True:
						try:
								reaction, user = await bot.wait_for(
										"reaction_add",
										check=lambda reaction, user: user == ctx.author and
										reaction.emoji in buttons,
										timeout=60.0)

						except asyncio.TimeoutError:
								pass

						else:
								previous_page = current
								if reaction.emoji == u"\u23EA":
										current = 0

								elif reaction.emoji == u"\u2B05":
										if current > 0:
												current -= 1

								elif reaction.emoji == u"\u27A1":
										if current < len(pages) - 1:
												current += 1

								elif reaction.emoji == u"\u23E9":
										current = len(pages) - 1

								for button in buttons:
										await msg.remove_reaction(reaction.emoji, ctx.author)

								if current != previous_page:
										await msg.edit(embed=pages[current])


bot = commands.Bot(command_prefix='$', intents=discord.Intents.all())
bot.add_cog(Commands(bot))


@bot.event
async def on_ready():

		# set bot status to online and game it is playing
		await bot.change_presence(status=discord.Status.online,
															activity=discord.Activity(
																	type=discord.ActivityType.playing,
																	name="League of Legends"))
		print(
				'Logged in as:\n{0.user.name}\n{0.user.id}\n*Not affiliated with Riot*'
				.format(bot))


bot.run(os.getenv('TOKEN'))