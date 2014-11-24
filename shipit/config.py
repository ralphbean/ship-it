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

import fedmsg.config

import shipit.consumers

defaults = {
    # TODO - zomg remove this.
    'username': 'ralph',

    'logsize': 30,
    'http.threads': 10,
    'yum_conf': 'conf/yum.conf',

    # URLs
    'pkgdb_url': 'https://admin.fedoraproject.org/pkgdb',
    'anitya_url': 'https://release-monitoring.org',
}


def load_config(shipitrc_path=None):
    """ Return tuple containing shipitrc config and fedmsg config """
    return load_shipitrc_config(shipitrc_path), load_fedmsg_config()


def load_shipitrc_config(path):
    config = copy.copy(defaults)
    # TODO - load common config from disk
    loaded = {}
    config.update(loaded)
    return config


def load_fedmsg_config():
    config = fedmsg.config.load_config()

    # Rephrase the /etc/fedmsg.d/ config as moksha *.ini format.
    config.update({
        'zmq_subscribe_endpoints': ','.join(
            ','.join(bunch) for bunch in config['endpoints'].values()
        ),
    })
    # Enable our consumers by default
    config.update(dict([
        (c.config_key, True) for c in shipit.consumers.all_consumers
    ]))
    return config

