"""This plugin provides convenient object-serialization functions.

Use pickle-based functions for general serialization, or faster
marshal-based functions for when you are reliably working with objects
without recursive references and of only native python types (str, int,
list, dict, ...).
"""

import gzip, marshal
try: import cPickle as pickle
except ImportError: import pickle

class SerializationError(Exception): pass

def _gzip(filename, mode, data, serializer, func):
    filename = data_dir + filename + '.' + serializer + '.gz'
    try:
        with gzip.open(filename, *mode) as f:
            ret_val = func(f, data)
        return True if mode[0][0] == 'w' else ret_val
    except Exception as exc:
        action = 'write' if mode[0][0] == 'w' else 'read'
        bot.log.error('Could not {action} {file}: {exc}'.format(action=action, file=filename, exc=exc))
        raise SerializationError

def marshal_dump(filename, data):
    return _gzip(filename, ('wb', 1), data, 'marshal',
                 lambda f, d: f.write(marshal.dumps(d)))

def marshal_load(filename):
    return _gzip(filename, ('rb',), None, 'marshal',
                 lambda f, _: marshal.loads(f.read()))

def pickle_dump(filename, data):
    return _gzip(filename, ('wb', 1), data, 'pickle',
                 lambda f, d: pickle.dump(d, f, pickle.HIGHEST_PROTOCOL))

def pickle_load(filename):
    return _gzip(filename, ('rb',), None, 'pickle',
                 lambda f, _: pickle.load(f))

def on_load(_bot, _):
    global bot, data_dir
    bot = _bot
    data_dir = bot._ensure_endswith_slash(bot.config('main/data_dir'))
    # Attach methods to bot object
    bot.marshal_load = marshal_load
    bot.marshal_dump = marshal_dump
    bot.pickle_load = pickle_load
    bot.pickle_dump = pickle_dump
    bot.unserialize = pickle_load
    bot.serialize = pickle_dump
