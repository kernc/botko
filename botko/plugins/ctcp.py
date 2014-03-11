from datetime import datetime

def time_since_last_action_more_than(on_channel, seconds):
    now = datetime.now()
    last_time = time_since_last_action_more_than.times.get(on_channel)
    if not last_time or (now - last_time).total_seconds() > seconds:
        time_since_last_action_more_than.times[on_channel] = now
        return True
    return False
    
time_since_last_action_more_than.times = {}
        
action_verb_map = {
    'is':'is',
    'has':'has',
    'did':'did',
    'will':'will',
    'slaps':'does',
    'could':'could',
    'should':'should',
}

def on_ctcp(bot, message):
    """Reply to CTCP requests"""
    if not message.text.startswith('\x01'):
        return
    request = message.token[0].lower().strip('\x01')
    if 'action' == request:
        if not message.param[0].startswith('#'): return
        if time_since_last_action_more_than(message.param[0], 60*60*2):
            orig = message.text[1]
            verb = action_verb_map.get(orig)
            if not verb and orig.endswith('s'):
                verb = 'does'
            if verb:
                bot.privmsg(channels.join(','), '\x01ACTION ' + verb + ' too.\x01')
    elif 'version' == request:
        bot.notice(message.nick, '\x01VERSION mIRC v6.31 Khaled Mardam-Bey\x01')
        bot.privmsg(message.nick, '\x01VERSION\x01')  # version them back for the logs
    elif 'source' == request:
        bot.notice(message.nick, '\x01SOURCE https://github.com/kernc/botko\x01')
