import random
import re
import json
import datetime

import discord
from apiclient.discovery import build
from apiclient.errors import HttpError

# going to start storing various config options in a separate file, so they don't clog up the main file here.
import botconfig

print('Welcome to SolarPy discord bot.')

print('Checking for existing discord bot token...')
try:
    # try-except-finally statements are python's way of catching exceptions instead of crashing.
    with open('token') as f: # here I'm trying to open a file called 'token'.
        TOKEN = f.read() # if the file opens, we read the token from it.
except FileNotFoundError: # if the file doesn't exist, trying to open it will raise the FileNotFoundError exception.
    # so we catch it, and 'handle' it as it is known in the industry.
    # if the file doesn't exist, we don't have a token saved yet, so we take it from the user directly.
    TOKEN = input('Please enter bot token for authentication:\n')
    save = input('Would you like to save token for later use? (y/n)\n') # we also ask if the user wants to save it.
    save = str.lower(save) # this makes sure whatever the response to the question was, is in lowercase.
    if save == 'y': # if the user accepted...
        with open('token', 'w') as f: # here we open the file in write mode, which creates a new file if it isn't there
            f.write(TOKEN) # then we write the token to it

# here I do the same thing but for the Google API key.
print('Checking for existing Google API key...')
try:
    with open('gcp_api_key') as f:
        GCP_API_KEY = f.read()
except FileNotFoundError:
    GCP_API_KEY = input('Please enter Google API key for authentication:\n')
    save = input('Would you like to save API key for later use? (y/n)\n')
    save = str.lower(save)
    if save == 'y':
        with open('gcp_api_key', 'w') as f:
            f.write(GCP_API_KEY)

# here I'm storing the name of the API and the version of it - those can change in time, so they're configurable.
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
# here i build the service object as per instructions from the API documentation
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=GCP_API_KEY)


class Bot(discord.Client):
    # here we define the Bot class. It's derived from the Client class which comes with the discord.py API.
    # might refactor this class to sit in its own file, so it's cleaner.

    async def on_ready(self):
        # this function gets called if and when the bot successfully connects itself to discord
        # it'll print to the console the name the bot is logged in as, and the user object's ID.
        print("Logged in as")
        print(self.user.name)
        print(self.user.id)
        print("--------")

        # I'm also adding some bot-specific initialization here;
        # usually you would do that in a constructor that calls the initializer of the base class,
        # but a) I'm lazy and b) the constructor is a bit weird and I don't know how to call it correctly
        # if none of these terms mean much to you, don't worry... in simple terms, this is where i initialize the bot's brain.

        # there are only a few files so i will store them in advance
        # (note that the files aren't included in the repo!)
        self.horo_happy = discord.File('gifs/horo_happy.gif')
        self.tearful_smile = discord.File('gifs/tearful_smile.gif')

        # some regex patterns for commands and some replies
        self.pattern_hug = re.compile(r"^("+self.user.name + r"|" + self.user.mention + r"),? give (.+) a hug", re.I | re.M)
        self.pattern_daygreet = re.compile(r"^good (day|morning|afternoon|evening|night),? ("+self.user.name + r"|" + self.user.mention + r")", re.I)
        self.pattern_youtube = re.compile(r"^("+self.user.name + r"|" + self.user.mention + r"),? look for (.+) on (youtube|yt)", re.I)
        self.pattern_slowclap = re.compile(r"^("+self.user.name + r"|" + self.user.mention + r"),? slow clap", re.I)
        self.pattern_opinion = re.compile(r"^("+self.user.name + r"|" + self.user.mention + r"),? do you (like|love|dislike|hate) (.+)\??", re.I)
        self.pattern_whatis = re.compile(r"it's( a)? (.+)", re.I)
        self.pattern_loveyou = re.compile(r"^("+self.user.name + r"|" + self.user.mention + r"),? I love you", re.I)
        self.pattern_muh = re.compile(r"mu+h+", re.I)
        self.pattern_op = re.compile(r"(\w+) is too (?:\w+)", re.I)

        self.me_to_same_counter = 0 # counter for 'me to same's
        self.yeah_counter = 0 # counts 'yeah' messages
        self.prev_msg_author = 0 # keeps track of the ID of the person who wrote the last message
        self.namedrop_responses = ["Huh?", "Yo.", "Sup.", "Salut."]
        self.owo_responses = ["What's this?", "*Notices your message*"]
        self.like_it_responses = ["You kiddin' me?", "Hell naw.", "Nah.", "Meh.", "Heh, yeah.", "Dude, that isn't even a question."]

    async def on_message(self, message):
        # this function will get called when the bot sees a message in ANY context, which I believe includes DMs.
        if message.author.id == self.user.id:
            # if the message's author is the bot itself, we ignore it immediately.
            return

        # if we have commands, i'll put them here.
        if await self.command(message):
            return

        # if not a command, bot will choose if and how to reply
        await self.reply(message)

        # at the very end, we log the message's author
        self.prev_msg_author = message.author

    async def search_youtube(self, query, message):
        # here i will handle youtube searches.
        # the function takes in a query, which is just whatever we're searching, and the message the query came in.
        # TODO: only take in the channel, the message itself isn't relevant

        # here we build a query using the service object, and then we call execute() to perform the query.
        # query changes on april fools :)
        date = datetime.date.today()
        if date.month == 4 and date.day == 1:
            # april fools!
            await message.channel.send("Top result:\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ")
            return
        response = youtube.search().list(
            q=query, # we put the string to search here
            part="id", # this just tells the API what part of the result we want;
                       # we don't need a lot of data, just the video ID.
            maxResults=1, # we only need one result, which is the same as saying only the top result
            type="video" # and we only want to get video results, no channels and no playlists.
        ).execute()

        # extract the video id from the response
        video = response["items"][0]["id"]["videoId"]

        # TODO: lots of unnecessary steps, can be shortened
        link = "https://www.youtube.com/watch?v=" # store the URL string
        reply = "Top result:\n" # start building a reply
        reply = reply + link + video + "\n" # concatenate the link with the video ID

        await message.channel.send(reply) # send the reply

    async def command(self, message):
        match = re.match(self.pattern_hug, message.content)
        if match:
            target = match.group(2)
            if not message.channel.guild:
                await message.channel.send("Can't hug in DMs.")
                return True
            member = message.channel.guild.get_member_named(target)
            if not member:
                await message.channel.send("Can't find {0}, would you like me to hug someone else {1.author.mention}? (check spelling)".format(target, message))
                return True
            await message.channel.send("{0.author.mention} gives {1.mention} a hug! :hugging: OwO".format(message, member))
            return True
        match = re.match(self.pattern_daygreet, message.content)
        if match:
            period = match.group(1)
            await message.channel.send("Good {0}, {1.author.mention}! ^_^".format(period, message))
            return True
        match = re.match(self.pattern_slowclap, message.content)
        if match:
            await message.channel.send("http://gph.is/XH7nxi")
            return True
        match = re.match(self.pattern_youtube, message.content)
        if match:
            query = match.group(2)
            await self.search_youtube(query, message)
            return True
        match = re.match(self.pattern_opinion, message.content)
        if match:
            subject = str.lower(message.content).split()[4:]
            if subject[0] == "me" or subject[0] == "me?":
                if "love" in message.content:
                    await message.channel.send("B-BAKA! Like I'd have any f-feelings for you... *blush*")
            else:
                await message.channel.send(random.choice(self.like_it_responses))
            return True
        match = re.match(self.pattern_loveyou, message.content)
        if match:
            await message.channel.send(file=self.tearful_smile)
            return True
        return False

    async def reply(self, message):
        # random chance
        chance = random.random()
        # this function is responsible for coming up with funny answer

        # section for responses with bot's name in the message
        if str.lower(self.user.name) in str.lower(message.content) or self.user.mention in str.lower(message.content):
            await message.channel.send(random.choice(self.namedrop_responses))

        else:
            # this section handles me to sames
            if str.lower(message.content).startswith("me to same"):
                if message.author != self.prev_msg_author:
                    self.me_to_same_counter += 1
            else:
                self.me_to_same_counter = 0

            if self.me_to_same_counter >= 2 and chance <= botconfig.BOT_GENERIC_REPLY_CHANCE:
                await message.channel.send("me to same")
                self.me_to_same_counter = 0

            # this section handles yeahs
            if str.lower(message.content) == "yeah":
                if message.author != self.prev_msg_author:
                    self.yeah_counter += 1
                if self.yeah_counter > 2:
                    if chance <= botconfig.BOT_YEAH_REPLY_CHANCE:
                        self.yeah_counter = 0
                        await message.channel.send("me to same")
            else:
                self.yeah_counter = 0

            # this section for global reply chance messages
            if "thank you" in str.lower(message.content):
                await message.channel.send(file=self.horo_happy)
            elif chance <= botconfig.BOT_GENERIC_REPLY_CHANCE:
                match = re.match(self.pattern_whatis, message.content)
                if match:
                    await message.channel.send("What's {0}?".format(match.group(2)))
                    return

                match = re.match(self.pattern_muh, message.content)
                if match:
                    muh_length = random.randint(1, 10)
                    msg = "M"
                    msg += "U"*muh_length
                    msg += "H"
                    await message.channel.send(msg)
                    return

                match = re.match(self.pattern_op, message.content)
                if match:
                    await message.channel.send("{0} too op, pls nerf".format(match.group(1)))
                    return

                if "through" in str.lower(message.content):
                    adjusted = message.content.replace("through", "TROUGH")
                    await message.channel.send(adjusted)
                elif str.lower(message.content) == "oopsie":
                    await message.channel.send("woopsie!")

                elif "OWO" in message.content or "UWU" in message.content:
                    await message.channel.send(random.choice(self.owo_responses))

                elif "love" in str.lower(message.content):
                    await message.channel.send("OWO")

                elif "oops" in str.lower(message.content):
                    await message.channel.send("OOPSIE WOOPSIE!")

                elif "capsicum" in str.lower(message.content):
                    await message.channel.send("CAPSICUM? Don't forget to add the AIL and then MIXWELL")

bot = Bot() # we instantiate the Bot class.
bot.run(TOKEN) # the 'run' method is how you start the bot's main loop, and we start it here and pass it the OAuth2 token.
