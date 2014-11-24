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
import datetime

import urwid

import shipit.main
import shipit.utils

logitems = None
logfile = None

def initialize(config, fedmsg_config):
    global logitems
    global logfile
    logitems = collections.deque(maxlen=config['logsize'])
    logfile = config['logfile']


def log(msg):
    if logitems is None:
        raise ValueError("shipit.log not initialized")

    prefix = "[%s] " % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # TODO -- remove urwid here and have just a base list with urwid applied later
    msg = prefix + msg
    logitems.append(urwid.Text(msg))

    with open(logfile, 'a') as f:
        f.write(msg + '\n')

    # We need to asynchronously update our logs while other inlineCallbacks
    # block are ongoing, so we do...
    d = shipit.utils.noop()
    d.addCallback(lambda x: shipit.main.mainloop.draw_screen())
    return d
