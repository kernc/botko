
import os
from datetime import datetime

def mkdir_p(path):
    try: os.makedirs(path)
    except OSError:
        if os.path.isdir(path): pass
        else: raise

class logger(object):
    def __init__(self, bot):
        self.bot = bot
        self.files = {}
        self.chans = bot.config('logger/channels')
        self.convs = bot.config('logger/conversations')
        bot.log.info('Logging: {} channels and conversations with {}'.format(self.chans, self.convs))
        self.chans = True if chans.lower() == 'all' else chans.split(',')
        self.convs = True if convs.lower() == 'all' else convs.split(',')
    
    def has_log_targets(self):
        return self.chans or self.convs

    def log(self, bot, nick, target, text):
        if target.startswith(('#', '&', '!')):
            if self.chans == True or target in self.chans:
                self.write(nick, target, text)
        else:
            if self.convs == True or nick in self.convs:
                self.write(nick, nick, text)

    def write(self, nick, target, text):
        if target not in self.files:
            file = '{}/{}/{target}/{date}.txt'.format(
                *bot.config('main/log_dir', 'main/server'),
                target=target,
                date=datetime.isoformat(datetime.now()))
            self.bot.log.debug('Opening new log file: ' + file)
            mkdir_p(os.path.dirname(file))
            self.files[target] = open(file, 'a')
            # TODO: write some kind of header?
        line = '{time} {nick}: {text}'.format(datetime.now(), nick, text)
        self.files[target].write(line)


def on_load(bot, _):
    global logger
    logger = logger(bot)
    if not logger.has_log_targets(): return
    # Monkey-patch bot.privmsg() so it logs self-output
    orig_privmsg = bot.privmsg
    def monkey_privmsg(target, text):
        for t in target.split(','):
            logger.log(bot, bot.nick, t, text)
        orig_privmsg(target, text)
    bot.log.info('Monkey-patching bot.privmsg()')
    bot.privmsg = monkey_privmsg
    # Set on_privmsg handler
    def privmsg(bot, message):
        logger.log(bot, message.nick, message.param[0], message.text)
    global on_privmsg
    on_privmsg = privmsg

