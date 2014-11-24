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

import urwid

import moksha.hub

import shipit.consumers
import shipit.models
import shipit.utils
import shipit.producers

from twisted.internet import reactor


def unhandled_input(key):
    if key in ['q', 'Q']:
        raise urwid.ExitMainLoop()


def initialize(config, fedmsg_config, ui, palette, models):

    consumers = shipit.consumers.all_consumers
    producers = shipit.producers.all_producers
    hub = moksha.hub.CentralMokshaHub(fedmsg_config, consumers, producers)

    reactor.callWhenRunning(shipit.models.build_nvr_dict)
    reactor.callWhenRunning(shipit.models.load_pkgdb_packages)

    def cleanup(*args, **kwargs):
        hub.close()
        shipit.utils.http.close()

    reactor.addSystemEventTrigger('before', 'shutdown', cleanup)
    return urwid.MainLoop(
        ui, palette,
        event_loop=urwid.TwistedEventLoop(),
        unhandled_input=unhandled_input,
    )
