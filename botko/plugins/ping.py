
def on_ping(bot, message):
    """Just reply PONG with whatever params we got"""
    param, text = '', ''
    if message.param:
        param = ' ' + ' '.join(message.param)
    if message.text:
        text = ' :' + message.text
    bot._write('PONG{}{}'.format(param, text))
