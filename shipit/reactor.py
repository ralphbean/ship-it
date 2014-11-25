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

import sys

import urwid

import moksha.hub

from twisted.internet import reactor


def unhandled_input(key):
    if key in ['q', 'Q']:
        raise urwid.ExitMainLoop()


def initialize(config, fedmsg_config, ui, palette, model):

    import shipit.consumers
    import shipit.producers

    import shipit.log
    import shipit.utils

    consumers = shipit.consumers.all_consumers
    producers = shipit.producers.all_producers
    hub = moksha.hub.CentralMokshaHub(fedmsg_config, consumers, producers)

    startup_routines = [
        model.build_nvr_dict,
        model.load_pkgdb_packages,
    ]
    for routine in startup_routines:
        reactor.callWhenRunning(routine)

    def cleanup(*args, **kwargs):
        hub.close()
        shipit.utils.http.close()

    reactor.addSystemEventTrigger('before', 'shutdown', cleanup)
    result = urwid.MainLoop(
        ui, palette,
        event_loop=urwid.TwistedEventLoop(),
        unhandled_input=unhandled_input,
    )

    # Last thing, print out the log to stderr
    for item in shipit.log.logitems:
        sys.stderr.write(item.get_text()[0] + '\n')

    return result
