#!/usr/bin/python -OO

import re
import time
import logging
import asynchat
from os import path
from datetime import datetime
from threading import Thread, Lock
from functools import partial, update_wrapper
from collections import defaultdict, Mapping

import irc

try: bytes('test', 'utf-8')
except TypeError: pass
else: bytes = partial(bytes, encoding='utf-8')  # python 3

try: buffer
except NameError: buffer = memoryview  # python 3

log = logging.getLogger()  # overridden in init_logging() if standalone program

DEFAULT_CONFIG = {
    'main': {
        'nick': 'botko,BOTK0,B0TKO,B0TK0',
        'username': 'botko',
        'realname': 'botko',
        'server': 'chat.freenode.net',
        'port': '6667',
        'data_dir': './data/',  # TODO: allow env var interpolation, e.g. $HOME/... ?
    }
}
LINE_TERMINATOR = b'\r\n'

class Config(dict):
    """A simple config object that allows querying nested dicts
    by lookup strings joined with '/'. E.g.
    
    >>> config = Config({'a':{'b':'B', 'c':'C'}, 'd':'D'})
    >>> config('a') == {'b': 'B', 'c': 'C'}
    True
    >>> config('a/b')
    'B'
    >>> config('a/b', 'a/c', 'd')
    ('B', 'C', 'D')
    >>> config.get('d')
    'D'
    >>> config.get('y', 'Y')
    'Y'
    >>> config.update({'a':{'b':'!'}, 'f':'F'})
    >>> config == {'a': {'b': '!', 'c': 'C'}, 'd': 'D', 'f': 'F'}
    True
    """
    def update(self, other):
        for k in other:
            if k not in self:
                self[k] = other[k]
            else:
                self[k].update(other[k])

    def get(self, key, default=''):
        for key in key.strip('/').split('/'):
            if not isinstance(self, dict):
                return default
            self = dict.get(self, key, default)
        return self

    def __call__(self, *args):
        r = [self.get(arg) for arg in args]
        return r[0] if len(r) == 1 else tuple(r)

    def __str__(self):
        return '<Config {}>'.format(dict.__str__(self))

def decorator(d):
    """Make function d a decorator"""
    def _d(func): return update_wrapper(d(func), func)
    update_wrapper(_d, d)
    return _d

def synchronized(lock):
    """Synchronization decorator.

    Example
    -------
    >>> from threading import Lock
    >>> my_lock = Lock()
    >>> @synchronized(my_lock)
    ... def critical_section(): pass
    """
    @decorator
    def wrapper(f):
        def decorated(*args, **kwargs):
            with lock: return f(*args, **kwargs)
        return decorated
    return wrapper

class PeriodicExecutor(Thread):
    def __init__(self, name, seconds, func, args=(), kwargs={}):
        super(self.__class__, self).__init__(name=name)
        self.func = partial(func, *args, **kwargs)
        self.seconds = seconds
        self.daemon = True
    def __call__(self, *args):
        self.run()
    def run(self):
        while True:
            time.sleep(self.seconds)
            if self.func(): break

class Connection(asynchat.async_chat):
    buffer = []
    def collect_incoming_data(self, data):
        self.buffer.append(data)

    def set_line_handler(self, callback):
        def found_terminator():
            line = self.buffer[0] if len(self.buffer) == 1 else b''.join(self.buffer)
            del self.buffer[:]
            callback(line)
        self.found_terminator = found_terminator

    def handle_error(self):
        excepthook()
    def handle_close(self):  # FIXME: this doesn't get run. problem?
        log.info('Closing...')

expect_lock = Lock()

class ProtocolReplyEventQueue(object):
    queue = defaultdict(set)
    
    @synchronized(expect_lock)
    def expect(self, coroutine, replies):
        """Marks the generator object coroutine as expecting one of the int replies"""
        if isinstance(replies, int): replies = (replies,)
        if any(filter(lambda i: not isinstance(i, int), replies)):
            log.error('expect() expects single numeric or a tuple/set/list of replies')
            sys.exit(1)
        now = datetime.now()
        for reply in replies:
            self.queue[reply].add((now, coroutine))
            self.queue[coroutine].add(reply)

    @synchronized(expect_lock)
    def fulfil(self, reply):
        """Runs the coroutine(s) waiting for reply, and if done, pops it from the queue"""
        now = datetime.now()
        for then, coroutine in self.queue.get(reply, set()).copy():
            assert then < now, 'event should always be fired after scheduling for it'
            done = coroutine.send(reply)
            # If coroutine returned something (other than yielding None), remove it from queue
            if done is not None:
                self.queue[reply].remove((then, coroutine))
                if 0 == len(self.queue[reply]):
                    del self.queue[reply]
                del self.queue[coroutine], coroutine

conn_tx_lock = Lock()

def is_event_handler(event, re=re.compile('^on_(every_[0-9]+[smhd]|[a-z]+|[0-9]+)$')):
    return re.match(event)

class Bot(object):
    _connection = Connection()
    _replies = ProtocolReplyEventQueue()
    plugins = {}
    log = log  # pass logging to plugins

    def __init__(self, config):
        # update config with defaults where missing
        self.config = Config(DEFAULT_CONFIG)
        for section in config:
            if section not in self.config: self.config[section] = {}
            self.config[section].update(config[section])
        if not re.match('^{nick}(,{nick})*$'.format(nick=irc._PATTERN_NICKNAME_STRICT), 
                        self.config('main/nickname')):
            log.warning('Invalid nickname(s) in config')
        if not re.match(irc._PATTERN_JOIN_PARAMS,
                        self.config('main/channels')):
            log.warning('Invalid channels specified in config: ' + self.config('main/channels'))
        log.info('Starting botko with config: ' + str(self.config))

        # import plugins and attach their on_* event handlers
        def plugin_modules():
            import os
            from os.path import dirname, abspath, splitext, basename
            for filename in os.listdir(dirname(abspath(__file__)) + '/plugins/'):
                filename, extension = splitext(basename(filename))
                if not filename.startswith('_') and extension == '.py':
                    yield ('plugins.' + filename, filename)
        def load_plugin(module, plugin_name):
            try: return self.plugins[module] # already loaded
            except KeyError: pass  # else continue loading
            log.info('Loading plugin: ' + plugin_name)
            from importlib import import_module
            plugin = import_module(module)
            self.plugins[plugin_name] = plugin
            for event in plugin.__dict__:
                if not event.startswith('on_'): continue
                handler = getattr(plugin, event)
                if not callable(handler): continue
                if not is_event_handler(event):
                    log.warning('Skipping unrecognized event handler: ' + str(handler))
                    continue
                if event.startswith('on_every_'):
                    _scalar = {'m':60, 'h':60*60, 'd':60*60*24}.get(event[-1], 1)
                    seconds = int(event[len('on_every_'):-1]) * _scalar
                    handler = PeriodicExecutor(plugin_name + '.' + event,
                                               seconds, handler, (self, None))
                    event = 'on_every'
                self.add_handler(event, handler)
            # process dependencies
            try: depends = plugin.__depends__
            except AttributeError: return  # no __depends__ specified
            if isinstance(depends, str):
                load_plugin('plugin.' + depends, depends)
            elif isinstance(depends, Sequence):
                for dependency in depends:
                    load_plugin('plugin.' + depends, depends)
            else:
                log.error('__depends__ must be a str or tuple of str')
                sys.exit(1)
        for module, plugin_name in plugin_modules():
            if self.config(plugin_name + '/disabled'):
                log.info('Skipping disabled plugin: ' + plugin_name)
                continue
            load_plugin(module, plugin_name)

        # execute any on_load hooks
        log.info('Triggering on_load event hooks ...')
        self._trigger_event('load')

        # set up socket connection
        self._connection.set_terminator(LINE_TERMINATOR)
        self._connection.set_line_handler(self._process_line)
        self._connection.handle_connect = self._handle_connect()
        self._connection.create_socket(asynchat.socket.AF_INET,
                                       asynchat.socket.SOCK_STREAM)
        log.info('Connecting to {server}:{port}'.format(**self.config['main']))
        self._connection.connect((self.config('main/server'),
                                  int(self.config('main/port'))))
        log.info('Starting event loop')

    def run(self):
        asynchat.asyncore.loop()

    def _trigger_event(self, event, message=None):
        assert not event.startswith('on_')
        event = 'on_' + str(event)
        for hook in getattr(self, event, ()):
            log.level >= logging.DEBUG and log.debug(
                'Running {event} hook {hook}'.format(event=event, hook=hook))
            hook(self, message) # TODO message

    @synchronized(conn_tx_lock)
    def _write(self, line):
        log.level >= logging.DEBUG and log.debug('TX bytes: ' + line)
        self._connection.push(bytes(line) + LINE_TERMINATOR)

    def privmsg(self, target, text):
        self._write('PRIVMSG {} :{}'.format(target, text))

    def notice(self, target, text):
        self._write('NOTICE {} :{}'.format(target, text))

    def every_so_often(self):
        # TODO check if nick available
        # TODO check if channels joined
        # check if queues are empty
        pass
 
    def expect(self, coroutine, replies, autostart=False):
        if autostart: next(coroutine)
        log.level >= logging.DEBUG and log.debug(
            'Expecting replies {} for coroutine {}'.format(replies, coroutine))
        self._replies.expect(coroutine, replies)
    
    def add_handler(self, event, handler):
        if not is_event_handler(event) or not callable(handler):
            log.error('Invalid event or event handler: {}: {}'.format(event, handler))
            return
        try: getattr(self, event).append(handler)
        except AttributeError:
            setattr(self, event, [handler])
        finally: log.debug('Attached event handler ' + str(handler))
    
    def remove_handler(self, event, handler):
        try: getattr(self, event).remove(handler)
        except AttributeError, ValueError:
            log.warning('Event handler not active for event {}: {}'.format(event, handler))
            return False
        else: log.debug('Removed event handler ' + str(handler))

    def _handle_connect(self):
        """closures self so it is available in handle_connect"""
        # TODO move this to a separate plugin?
        # FIXME: this all is shit, fix this!!!
        def handle_connect():
            """called by asyncore on connection established."""
            def set_nick():
                """cycles possible nicknames until one is accepted"""
                nicks = self.config('main/nick').strip(',').split(',')
                for suffix in ' 12345':
                    for nick in nicks:
                        nick = nick.strip() + suffix
                        self._write('NICK {}'.format(nick))
                        if (yield) == irc.RPL_WELCOME:
                            self.nick = nick
                            yield True; return
                self.nick = ''
                log.error('Could not set a nickname. IRC reply: ' + str(reply))
                yield True; return
            def register_user():
                # mixed RFC1459 and RFC2812 for max portability
                self._write('USER botko i {server} :{real_name}'.format(**self.config['main']))
                if (yield) in (irc.RPL_WELCOME, irc.ERR_ALREADYREGISTRED):
                    yield True; return
                else: log.error('Could not register with server, see raw connection log for details')
            def join_channels():
                channels = self.config('main/channels')
                self._write('JOIN ' + channels)
                reply = (yield)
                if reply == irc.RPL_ENDOFNAMES:
                    try: log.info('Starting {} "on_every" threads'.format(
                                  len([thread.start() for thread in self.on_every])))
                    except AttributeError: pass
                    self.channels = channels.split(' ')[0].split(',')  # HACK
                    yield True; return
                else: log.error('Could not join channels. IRC reply: ' + str(reply))

            self.expect(set_nick(), irc.REPLIES_NICK, True)
            self.expect(register_user(), irc.REPLIES_USER, True)
            self.expect(join_channels(), irc.REPLIES_JOIN, True)
        self._trigger_event('connect')
        return handle_connect

    def _handle_close(self):
        # TODO restart if not quit on purpose, or is that in connection.handle_close() ?
        log.info('Unloading plugins ...')
        self._trigger_event('unload')
        from time import sleep
        sleep(1)  # HACK
        log.info('Closing connection')
        self._connection.close()

    def _process_line(self, line):
        log.level >= logging.DEBUG and log.debug('RX bytes: ' + line.decode('utf-8'))
        message = irc.parse_line(line.decode('utf-8'))
        code, command = message.code, message.command
        if code:
            self._replies.fulfil(code)
            if code == irc.RPL_WELCOME:
                self._trigger_event('welcome', message)
        if command == 'privmsg':
            if message.text.startswith('\x01') and message.text.endswith('\x01'):
                self._trigger_event('ctcp', message)
            elif message.param[0].startswith(('#', '&', '+', '!')):
                self._trigger_event('chanmsg', message)
            else:
                self._trigger_event('privmsg', message)
        self._trigger_event(str(command), message)

    def _ensure_endswith_slash(self, dir):
        if not dir: return ''
        return dir + path.sep if not dir.endswith(path.sep) else dir

def excepthook(*args, **kwargs):
    import sys, traceback
    traceback.print_exc()
    sys.exit(1)

def init_logging(level=logging.NOTSET):
    global log
    log = logging.getLogger()
    log.setLevel(level)
    stderr = logging.StreamHandler()
    stderr.setLevel(level)
    formatter = logging.Formatter('%(asctime).19s %(levelname)-5s %(module)s:%(lineno)d  %(message)s')
    stderr.setFormatter(formatter)
    log.addHandler(stderr)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='A simple Python IRC bot.')
    parser.add_argument('--config', '-c', metavar='FILE', default='botko.conf',
                        help='configuration file to use') # TODO change default
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='verbose state reporting; use twice for debug')
    args = parser.parse_args()
    init_logging(logging.WARNING - logging.DEBUG*args.verbose)
    try:
        from configparser import ConfigParser
    except ImportError:
        from ConfigParser import ConfigParser
    parser = ConfigParser()
    with open(args.config) as f: parser.readfp(f)
    try:
        bot = Bot(parser._sections)  # ConfigParser provides dict of dicts in _sections
        bot.run()
    except KeyboardInterrupt:
        bot._handle_close()
    except Exception as e: excepthook()


if __name__ == '__main__':
    main()
