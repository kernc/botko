""" This is an example botko plugin. It does nothing.

Botko plugins are really simple. Each plugin file should define
functions that start with 'on_' and accept two arguments.

Each on_* function is an event handler for a particular event *.
These events directly correspond to IRC commands:
https://tools.ietf.org/html/rfc2812#section-3

E.g. the following function is called on each received 'PRIVMSG' IRC
message:

  def on_privmsg(bot, message): pass

Additionally, these events are defined:
* load - fires when bot with all the plugins is loaded,
* unload - fires right before exiting,
* connect - right after connection with the server is established,
* welcome - when botko.irc.RPL_WELCOME code is received,
* ctcp - when message.text starts and ends with '\x01', designating
         a CTCP request,
* chanmsg - on a PRIVMSG sent to a channel,

Additionally, callbacks can be of the regex form:
* on_([0-9]+) - called when \1 code is received (defined in botko.irc),
* on_every_([0-9]+)([smhd]) - called in a separate thread on every \1
                            units (\2: Seconds, Minutes, Hours, Days),

E.g.

  def on_366(bot, message): pass  # called on irc.RPL_ENDOFNAMES reply
  def on_every_30m(bot, _): pass  # called about every 30 minutes


All callbacks take two arguments:
* botko.Botko instance - the bot, and
* botko.irc.Message (usually) or None (on load, unload, every, ...)

In plugins, you can also use:
* bot.log - an instance of logging.Logger,
* bot.config - a botko.Config instance,
* bot.privmsg(), bot.notice() - to send messages,
* ... - see botko.Botko for further info.

Inspect other provided examples.

"""
pass
