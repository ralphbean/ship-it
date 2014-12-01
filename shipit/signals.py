# This file is part of shipit, a curses-based, fedmsg-aware heads up display
# for Fedora package maintainers.
# Copyright (C) 2014  Ralph Bean <rbean@redhat.com>
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see
# <http://www.gnu.org/licenses/>.

from __future__ import print_function

import collections

import shipit.reactor

from shipit.log import log


def cb_repr(callback):
    """ Return a more terse object for debugging. """
    if getattr(callback, 'im_self', None):
        return callback.im_self
    return callback

def key_repr(key):
    """ Return a more terse object for debugging. """
    if isinstance(key, basestring):
        return key
    return "<%s>" % type(key).__name__


class AsyncNotifier(object):
    def __init__(self, *args, **kwargs):
        self.callbacks = collections.defaultdict(list)
        super(AsyncNotifier, self).__init__(*args, **kwargs)

    def signal(self, event, key, *args, **kwargs):
        entry = self.callbacks[event]

        if isinstance(entry, dict):
            entry = entry[key]

        args = args if args else (key,) + args
        for callback in entry:
            #log("** signalling %r <- (%s/%s) <- %r" % (
            #    cb_repr(callback), event, key_repr(key), self))
            shipit.reactor.reactor.callLater(0, callback, *args, **kwargs)

    def register(self, event, key, callback):
        entry = self.callbacks[event]

        if key and entry and not isinstance(entry, dict):
            raise ValueError("Mixing subkeys and not is disallowed.")

        if key and not entry:
            self.callbacks[event] = collections.defaultdict(list)

        if key:
            entry = self.callbacks[event][key]

        #log("** registering %r <- %s/%s <- %r" % (
        #    cb_repr(callback), event, key_repr(key), self))

        entry.append(callback)
