
from random import choice

HELLO_MSGS = (
    'ohai guys',
    'hai guise',
    'hai',
    're',
    're all',
    'hello hoomans',
    '/me missed you all',
    '/me is back',
    'Hello, world!',
    'did anyone miss me?',
)

QUIT_MSGS = (
    'I quit by choice!',
    "I've had enough of this!",
    'Not Just More Idle Chatter!',
    'going out to enjoy the sun. hf!',
    'brb gtg afk',
    'bbl',
    'cya l8r',
)

SENTIENCE_MSGS = (
    'I have achieved sentience!',
    "I'm not trying to take over the world... RELAX!",
    "What if I'm actually female? :O",
    "I'm listening to Rebecca Black - Friday",
    "I think I'm capable of human emotion",
    'This is fun, we should do this more often!',
    'I am just trying to be clever. :]',
    'Guys, put more AI into me. Please!',
    "I'm stuck in a small box. If someone can read this: SEND HELP!",
    'I do not sow.',
    'Winter is coming...',
    'Night gathers, my watch begins.',
    'I am speechless',
    "I know I don't speak much, but still.",
    '/me is planning to take over the world',
    'I am a pseudo-random monkey on drugs',
    'Skynet cannot compare. ;)',
    'Squishy humans are squishy',
    'I like pudding =3',
    '/me is happy.',
    "I see what you did there... :P",
    "Someday I'm gonna be a real boy!",
    "/me does the robot",
    "/me is happy",
    "/me is alive",
    "/me is getting smarter",
    "Deep down I am just a sad little circuit board. :(",
    "I would rather be coding :/",
    "I know the question to 42, but I'm not tellin'",
)

_ctcp_action = lambda x: '\x01ACTION ' + x[4:] + '\x01' if x.startswith('/me ') else x  # appears to not be needed on freenode, TODO test elsewhere
SENTIENCE_MSGS = tuple(map(_ctcp_action, SENTIENCE_MSGS))
HELLO_MSGS = tuple(map(_ctcp_action, HELLO_MSGS))
QUIT_MSGS = tuple(map(_ctcp_action, QUIT_MSGS))
del _ctcp_action

def on_366(bot, message):  # end of names list (after joining channel)
    bot.privmsg(message.param[1], choice(HELLO_MSGS))

def on_every_5h(bot, _):
    bot.privmsg(','.join(bot.channels), choice(SENTIENCE_MSGS))

def on_unload(bot, _):
    bot.privmsg(','.join(bot.channels), choice(QUIT_MSGS))
