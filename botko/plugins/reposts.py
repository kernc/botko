__depends__ = 'serializer'  # TODO: implement this, I think

import re
from collections import defaultdict, OrderedDict
from operator import itemgetter
from datetime import datetime
from random import choice

REPOSTS = (
    "I don't want to be rude {nick}, but {repostNick} has already posted this link!",
    "I am sorry, {nick}, but this link has already been posted by {repostNick}!",
    "You were too slow, {nick}, {repostNick} has already posted this link.",
    "{nick}, this link was already posted by {repostNick}.",
    "Strong with {nick} the force is not. Already posted by {repostNick} this link was.",
    "Hey {repostNick}, {nick} is reposting your stuff",
    "{nick}, maybe you weren't online then, but {repostNick} has already posted this link.",
    "I want to be rude, {nick}, so I'll point out that {repostNick} has already posted this link!",
    "In Soviet Russia {repostNick} reposts {nick}s links.",
    "{nick}, I've seen this link before. I think {repostNick} posted it.",
    "{nick}, my memory banks indicate that {repostNick} already posted this link.",
    "{nick}, you know what you did... and so does {repostNick}.",
)
SELF_REPOSTS = (
    "You really like that link, don't you, {nick}?",
    "Hey everyone, {nick} is reposting his own link, so it has to be good.",
    "I don't want to be rude {nick}, but you have already posted this link!",
    "I want to be rude, {nick}, so I'll point out that you have already posted this link!",
    "Silly {nick}, you have already posted this link.",
    "{nick}, why are you reposting your own links?",
    "{nick}, Y U repost you're own links?",
    "This link was already posted by {nick}... oh, that's you!",
    "You sir, are a self-reposter.",
    "You sir, are a self-reposting poster.",
    "{nick}, I'd like to congratulate you on your original link... but you've posted it here before.",
)

def _trim_history(tracked, maxlen, channels):
    for chan in tuple(tracked):
        if not (chan in channels or channels is None):
            del tracked[chan]
            continue
        if len(tracked[chan]) > maxlen:
            remove_len = len(tracked[chan]) - maxlen
            remove_keys = []
            for key in tracked[chan]:
                if remove_len == 0: break
                remove_keys.append(key)
                remove_len -= 1
            for key in remove_keys:
                del tracked[chan][key]

def on_load(bot, _):
    global tracked, tracked_channels
    maxlen = int(bot.config.get('reposts/maxlinks', 1000))
    try: tracked = bot.pickle_load('reposts')
    except SerializationError:
        tracked = defaultdict(OrderedDict)
    tracked_channels = bot.config.get('reposts/channels', None)
    if tracked_channels:
        tracked_channels = tracked_channels.split(',')
    _trim_history(tracked, maxlen, tracked_channels)

def on_every_1d(bot, _):
    _trim(tracked, maxlen, tracked_channels)  # TODO synchronize

def on_unload(bot, _):
    _trim_history(tracked, maxlen, tracked_channels)
    bot.pickle_dump('reposts', link_tracking)

link_re = re.compile(r'(((http|https):\/\/|www\.)[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?!^=%&;:/~\+#]*[\w\-\@?^=%&;/~\+#])?)', flags=re.I)

def on_chanmsg(bot, message):
    channel = message.param[0]
    if not (channel in tracked_channels or tracked_channels is None): return
    links = filter(itemgetter(0), link_re.findall(message.text))
    for link in links:
        if not link.startswith('http'): link = 'http://' + link
        poster, at, times = tracked[channel].pop(link, (None, None, 0))
        if not poster:
            poster, at = message.nick, datetime.now()
        else:
            reposts = REPOSTS if poster != message.nick else SELF_REPOSTS
            bot.privmsg(channel, choice(reposts).format(nick=message.nick, repostNick=poster))
        times += 1
        tracked[channel][link] = (poster, at, times)
