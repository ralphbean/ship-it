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

import shipit.config
import shipit.consumers
import shipit.log
import shipit.models
import shipit.producers
import shipit.reactor
import shipit.ui


# Global state
mainloop = None


def command():
    """ Main entry point.

    This is what gets called when you run 'shipit' on the command line.
    """
    global mainloop
    config, fedmsg_config = shipit.config.load_config()


    shipit.log.initialize(config, fedmsg_config)

    # Install some hacks
    shipit.utils.vimify()
    shipit.utils.patch_webbrowser()

    shipit.utils.initialize_http(config, fedmsg_config)

    models = shipit.models.assemble_models(config, fedmsg_config)

    ui, palette = shipit.ui.assemble_ui(config, fedmsg_config)

    mainloop = shipit.reactor.initialize(
        config, fedmsg_config, ui, palette, models)

    mainloop.run()
