
import re
import logging
from collections import namedtuple

# patterns from: https://tools.ietf.org/html/rfc2812#section-2.3.1
_PATTERN_JOIN_PARAMS = '^[#&+!][^ ,\x00\x07\x0D]+(,[#&+!][^ ,\x00\x07\x0D]+)?( *([^ ,\x00\x09-\x0D]+(,[^ ,\x00\x09-\x0D]+)?)?)?$'
_PATTERN_NICKNAME_STRICT = r'[a-zA-Z\[\]^_`{|}\\][-a-zA-Z0-9\[\]^_`{|}\\]*'
_PATTERN_NICKNAME = r'[-\w\[\]^_`{|}\\]+'
_PATTERN_PREFIX = '(:((?P<server>[\w\.-]+)|(?P<nick>' + _PATTERN_NICKNAME + ')((!(?P<user>[^ @\x00\x0D\x0A]+))?@(?P<host>[\w\.:-]+))?) )?'
_PATTERN_PARAMS = '((?P<param>(?: +[^:][^ \x00\x0D\x0A]*)*)(?P<text> :?[^\x00\x0D\x0A]*)?)?'
PATTERN_IRC_MESSAGE = _PATTERN_PREFIX + '((?P<code>[0-9]+)|(?P<command>[A-Za-z]+))' + _PATTERN_PARAMS

Message = namedtuple('Message', 'server nick user host code command param token text line')  # see parse_line()

class _MetaNull(type): pass
class Null(type):
    """Null object design pattern.
    
    This class traps and ignores everything. Instances of it always and
    reliably do nothing, or return 0, '', False, or other logical,
    contextually-appropriate emptiness or negation.
    
    >>> Null()(1, kwarg=2)()[3]['4'] is Null
    True
    >>> Null.method().attr is Null
    True
    >>> Null * 1 / 2 + 3 == Null
    <Null>
    >>> bool(Null), str(Null), repr(Null), int(Null), len(Null)
    (False, '', '<Null>', 0, 0)
    >>> [i for i in Null]
    []

    Roughly, the goal with Null objects is to provide an 'intelligent'
    replacement for the often used primitive data type None in Python
    or Null (or Null pointers) in other languages. These are used for
    many purposes including the important case where one member of some
    group of otherwise similar elements is special for whatever reason.
    Most often this results in conditional statements to distinguish
    between ordinary elements and the primitive Null value.

    Among the advantages of using Null objects are the following:

      * Superfluous conditional statements can be avoided 
        by providing a first class object alternative for 
        the primitive value None.

      * Code readability is improved.

      * Null objects can act as a placeholder for objects 
        with behaviour that is not yet implemented.

      * Null objects can be replaced for any other class.

      * Null objects are very predictable at what they do.

    To cope with the disadvantage of creating large numbers of passive 
    objects that do nothing but occupy memory space Null objects are 
    often combined with the Singleton pattern.

    For more information use any internet search engine and look for 
    combinations of these words: Null, object, design and pattern.

    Dinu C. Gherman,
    August 2001
    """
    __metaclass__ = _MetaNull
    __hash__ = type.__hash__
    __slots__ = ()
    def __next__(_): raise StopIteration
    next = __next__  # Python 2 compatibility
    __dir__ = lambda _: []
    __str__ =   lambda _: ''
    __repr__ =  lambda _: '<Null>'
    __bytes__ = lambda _: b''
    __int__ =   \
    __len__ =   \
    __index__ = \
    __round__ = \
    __complex__ = lambda *_: 0
    __float__ =   lambda *_: 0.
    __eq__ = \
    __ge__ = \
    __gt__ = \
    __le__ = \
    __lt__ = \
    __ne__ = \
    __or__ = \
    __and__ = \
    __del__ = \
    __get__ = \
    __set__ = \
    __abs__ = \
    __add__ = \
    __mod__ = \
    __mul__ = \
    __new__ = \
    __neg__ = \
    __pos__ = \
    __pow__ = \
    __ror__ = \
    __sub__ = \
    __xor__ = \
    __call__ = \
    __exit__ = \
    __init__ = \
    __iter__ = \
    __radd__ = \
    __rand__ = \
    __rmod__ = \
    __rmul__ = \
    __rpow__ = \
    __rsub__ = \
    __rxor__ = \
    __enter__ =  \
    __delete__ = \
    __divmod__ = \
    __invert__ = \
    __lshift__ = \
    __rshift__ = \
    __delattr__ = \
    __delitem__ = \
    __getattr__ = \
    __getitem__ = \
    __rdivmod__ = \
    __rlshift__ = \
    __rrshift__ = \
    __setattr__ = \
    __setitem__ = \
    __truediv__ = \
    __floordiv__ = \
    __rtruediv__ = \
    __rfloordiv__ = \
    __getattribute__ = lambda self, *_, **__: self
Null.__class__ = Null

class nulltuple(tuple):
    """
    Behaves exactly like tuple, but when queried by index, it
    returns Null object if index is out of range.
    """
    def __getitem__(self, key):
        return tuple.__getitem__(self, key) if key < len(self) else Null

def parse_line(line):
    """ Parses IRC message line into Message namedtuple.
    Message.text is already split into a nulltuple of words.
    
    >>> parse_line(':HairyFodder!~Xatic@isp.example.com PRIVMSG #python :some1 speak python here?')
    Message(server='', nick='HairyFodder', user='~Xatic', host='isp.example.com', code=0, command='privmsg', param=('#python',), token=('some1', 'speak', 'python', 'here?'), text='some1 speak python here?', line=':HairyFodder!~Xatic@isp.example.com PRIVMSG #python :some1 speak python here?')
    >>> parse_line(':pool.freenode.net 005 NiCk EXTBAN=$,arxz WHOX CLIENTVER=3.0 :are supported by this server')
    Message(server='pool.freenode.net', nick='', user='', host='', code=5, command=5, param=('NiCk', 'EXTBAN=$,arxz', 'WHOX', 'CLIENTVER=3.0'), token=('are', 'supported', 'by', 'this', 'server'), text='are supported by this server', line=':pool.freenode.net 005 NiCk EXTBAN=$,arxz WHOX CLIENTVER=3.0 :are supported by this server')
    >>> parse_line('JOIN #foobar')
    Message(server='', nick='', user='', host='', code=0, command='join', param=('#foobar',), token=(), text='', line='JOIN #foobar')
    """
    m = parse_line.regex.match(line)
    if not m:
        return logging.error('provided line does not match IRC specification: ' + line)
    (server, nick, user, host,
     code, command, param, text) = map(lambda i: i or '',
                                        m.group('server', 'nick', 'user', 'host',
                                                'code', 'command', 'param', 'text'))
    command = command.lower()
    param = nulltuple(param[1:].split())  # strip leading SP
    text = text[2:]  # strip leading SP:
    token = nulltuple(text.split())
    try: code, command = int(code), int(code)
    except ValueError: code = 0
    return Message(server=server, nick=nick, user=user, host=host,
                   code=code, command=command, param=param,
                   token=token, text=text, line=line)
parse_line.regex = re.compile('^{}$'.format(PATTERN_IRC_MESSAGE))


# from: https://tools.ietf.org/html/rfc2812#section-5
RPL_WELCOME = 1
RPL_YOURHOST = 2
RPL_CREATED = 3
RPL_MYINFO = 4
RPL_BOUNCE = 5
RPL_TRACELINK = 200
RPL_TRACECONNECTING = 201
RPL_TRACEHANDSHAKE = 202
RPL_TRACEUNKNOWN = 203
RPL_TRACEOPERATOR = 204
RPL_TRACEUSER = 205
RPL_TRACESERVER = 206
RPL_TRACESERVICE = 207
RPL_TRACENEWTYPE = 208
RPL_TRACECLASS = 209
RPL_TRACERECONNECT = 210
RPL_STATSLINKINFO = 211
RPL_STATSCOMMANDS = 212
RPL_STATSCLINE = 213
RPL_STATSNLINE = 214
RPL_STATSILINE = 215
RPL_STATSKLINE = 216
RPL_STATSQLINE = 217
RPL_STATSYLINE = 218
RPL_ENDOFSTATS = 219
RPL_UMODEIS = 221
RPL_SERVICEINFO = 231
RPL_ENDOFSERVICES = 232
RPL_SERVICE = 233
RPL_SERVLIST = 234
RPL_SERVLISTEND = 235
RPL_STATSVLINE = 240
RPL_STATSLLINE = 241
RPL_STATSUPTIME = 242
RPL_STATSOLINE = 243
RPL_STATSHLINE = 244
RPL_STATSSLINE = 244
RPL_STATSPING = 246
RPL_STATSBLINE = 247
RPL_STATSDLINE = 250
RPL_LUSERCLIENT = 251
RPL_LUSEROP = 252
RPL_LUSERUNKNOWN = 253
RPL_LUSERCHANNELS = 254
RPL_LUSERME = 255
RPL_ADMINME = 256
RPL_ADMINLOC1 = 257
RPL_ADMINLOC2 = 258
RPL_ADMINEMAIL = 259
RPL_TRACELOG = 261
RPL_TRACEEND = 262
RPL_TRYAGAIN = 263
RPL_NONE = 300
RPL_AWAY = 301
RPL_USERHOST = 302
RPL_ISON = 303
RPL_UNAWAY = 305
RPL_NOWAWAY = 306
RPL_WHOISUSER = 311
RPL_WHOISSERVER = 312
RPL_WHOISOPERATOR = 313
RPL_WHOWASUSER = 314
RPL_ENDOFWHO = 315
RPL_WHOISCHANOP = 316
RPL_WHOISIDLE = 317
RPL_ENDOFWHOIS = 318
RPL_WHOISCHANNELS = 319
RPL_LISTSTART = 321
RPL_LIST = 322
RPL_LISTEND = 323
RPL_CHANNELMODEIS = 324
RPL_UNIQOPIS = 325
RPL_NOTOPIC = 331
RPL_TOPIC = 332
RPL_INVITING = 341
RPL_SUMMONING = 342
RPL_INVITELIST = 346
RPL_ENDOFINVITELIST = 347
RPL_EXCEPTLIST = 348
RPL_ENDOFEXCEPTLIST = 349
RPL_VERSION = 351
RPL_WHOREPLY = 352
RPL_NAMREPLY = 353
RPL_KILLDONE = 361
RPL_CLOSING = 362
RPL_CLOSEEND = 363
RPL_LINKS = 364
RPL_ENDOFLINKS = 365
RPL_ENDOFNAMES = 366
RPL_BANLIST = 367
RPL_ENDOFBANLIST = 368
RPL_ENDOFWHOWAS = 369
RPL_INFO = 371
RPL_INFOSTART = 371
RPL_MOTD = 372
RPL_ENDOFINFO = 374
RPL_MOTDSTART = 375
RPL_ENDOFMOTD = 376
RPL_YOUREOPER = 381
RPL_REHASHING = 382
RPL_YOURESERVICE = 383
RPL_MYPORTIS = 384
RPL_TIME = 391
RPL_USERSSTART = 392
RPL_USERS = 393
RPL_ENDOFUSERS = 394
RPL_NOUSERS = 395
ERR_NOSUCHNICK = 401
ERR_NOSUCHSERVER = 402
ERR_NOSUCHCHANNEL = 403
ERR_CANNOTSENDTOCHAN = 404
ERR_TOOMANYCHANNELS = 405
ERR_WASNOSUCHNICK = 406
ERR_TOOMANYTARGETS = 407
ERR_NOSUCHSERVICE = 408
ERR_NOORIGIN = 409
ERR_NORECIPIENT = 411
ERR_NOTEXTTOSEND = 412
ERR_NOTOPLEVEL = 413
ERR_WILDTOPLEVEL = 414
ERR_BADMASK = 415
ERR_UNKNOWNCOMMAND = 421
ERR_NOMOTD = 422
ERR_NOADMININFO = 423
ERR_FILEERROR = 424
ERR_NONICKNAMEGIVEN = 431
ERR_ERRONEUSNICKNAME = 432
ERR_NICKNAMEINUSE = 433
ERR_NICKCOLLISION = 436
ERR_UNAVAILRESOURCE = 437
ERR_USERNOTINCHANNEL = 441
ERR_NOTONCHANNEL = 442
ERR_USERONCHANNEL = 443
ERR_NOLOGIN = 444
ERR_SUMMONDISABLED = 445
ERR_USERSDISABLED = 446
ERR_NOTREGISTERED = 451
ERR_NEEDMOREPARAMS = 461
ERR_ALREADYREGISTRED = 462
ERR_NOPERMFORHOST = 463
ERR_PASSWDMISMATCH = 464
ERR_YOUREBANNEDCREEP = 465
ERR_YOUWILLBEBANNED = 466
ERR_KEYSET = 467
ERR_CHANNELISFULL = 471
ERR_UNKNOWNMODE = 472
ERR_INVITEONLYCHAN = 473
ERR_BANNEDFROMCHAN = 474
ERR_BADCHANNELKEY = 475
ERR_BADCHANMASK = 476
ERR_NOCHANMODES = 477
ERR_BANLISTFULL = 478
ERR_NOPRIVILEGES = 481
ERR_CHANOPRIVSNEEDED = 482
ERR_CANTKILLSERVER = 483
ERR_RESTRICTED = 484
ERR_UNIQOPPRIVSNEEDED = 485
ERR_NOOPERHOST = 491
ERR_NOSERVICEHOST = 492
ERR_UMODEUNKNOWNFLAG = 501
ERR_USERSDONTMATCH = 502

# Response replies certain commands expect
REPLIES_USER = (ERR_NEEDMOREPARAMS, ERR_ALREADYREGISTRED, RPL_WELCOME)
REPLIES_NICK = (ERR_NONICKNAMEGIVEN, ERR_ERRONEUSNICKNAME,
                ERR_UNAVAILRESOURCE, ERR_NICKCOLLISION,
                ERR_NICKNAMEINUSE, ERR_RESTRICTED, RPL_WELCOME)
REPLIES_JOIN = (ERR_NEEDMOREPARAMS, ERR_BANNEDFROMCHAN,
                ERR_INVITEONLYCHAN, ERR_BADCHANNELKEY,
                ERR_CHANNELISFULL, ERR_BADCHANMASK,
                ERR_NOSUCHCHANNEL, ERR_TOOMANYCHANNELS,
                ERR_TOOMANYTARGETS, ERR_UNAVAILRESOURCE,
                RPL_TOPIC, RPL_ENDOFNAMES)
# TODO continue


if __name__ == '__main__':
    import doctest
    doctest.testmod()