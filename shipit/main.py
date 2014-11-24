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

import copy
import re
import time
import webbrowser

import moksha.hub
import txrequests
import urwid

from twisted.internet import defer, utils
from twisted.internet import reactor

import shipit.config
import shipit.consumers
import shipit.log
import shipit.models
import shipit.producers
import shipit.reactor
import shipit.ui

from shipit.log import log
from shipit.utils import noop


# No need to install this, since txrequests does it at import-time.
#from twisted.internet import epollreactor
#epollreactor.install()

# xdg and gvfs for unknown reasons produce garbage on stderr that messes up
# our display, so we remove them and happily fall back to firefox or whatever
for nuisance in ['xdg-open', 'gvfs-open']:
    if nuisance in webbrowser._tryorder:
        webbrowser._tryorder.remove(nuisance)


# Add vim keys.
vim_keys = {
    'k':        'cursor up',
    'j':      'cursor down',
    'h':      'cursor left',
    'l':     'cursor right',
}
for key, value in vim_keys.items():
    urwid.command_map[key] = value


def command():
    """ Main entry point.

    This is what gets called when you run 'shipit' on the command line.
    """
    config, fedmsg_config = shipit.config.load_config()
    shipit.log.initialize(config, fedmsg_config)
    shipit.utils.initialize_http(config, fedmsg_config)
    ui, palette = shipit.ui.assemble_ui(config, fedmsg_config)
    models = shipit.models.assemble_models(config, fedmsg_config)
    mainloop = shipit.reactor.initialize(
        config, fedmsg_config, ui, palette, models)
    mainloop.run()
