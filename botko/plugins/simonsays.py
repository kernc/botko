
def on_load(bot, _):
    global owners
    owners = bot.config('main/owners').split(',')

def on_privmsg(bot, message):
    if not message.param[0] == self.nick: return
    if message.nick in owners and message.text.startswith('simon says:'):
        command = message.text[len('simon says:'):].strip()
        log.info('Executing command by {nick}: {cmd}'.format(nick=message.nick, cmd=command)
        bot._write(command)
