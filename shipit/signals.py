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


class AsyncNotifier(object):
    _callbacks = collections.defaultdict(list)

    def signal(self, event, key):
        entry = self._callbacks[event]

        if isinstance(entry, dict):
            entry = entry[key]

        if entry:
            log("Triggering %r callbacks on key %r" % (len(entry), key))

        args = [key] if key else []
        for callback in entry:
            shipit.reactor.reactor.callLater(0, callback, *args)

    def register(self, event, key, callback):
        entry = self._callbacks[event]

        if key and entry and not isinstance(entry, dict):
            raise ValueError("Mixing subkeys and not is disallowed.")

        if key and not entry:
            self._callbacks[event] = collections.defaultdict(list)

        if key:
            entry = self._callbacks[event][key]

        log("Registering callback %r on %r/%r" % (callback, event, key))

        entry.append(callback)
