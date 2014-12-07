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

import ConfigParser as configparser
import copy
import os
import sys

import fedmsg.config

import shipit.consumers
import shipit.wizard

defaults = {
    'logsize': 30,
    'logfile': os.path.expanduser('~/.config/shipit/shipit.log'),
    'yum_conf': os.path.expanduser('~/.config/shipit/yum.conf'),

    'http.threads': 10,

    # URLs
    'pkgdb_url': 'https://admin.fedoraproject.org/pkgdb',
    'anitya_url': 'https://release-monitoring.org',
    'dist_git_url': 'http://pkgs.fedoraproject.org/cgit/{package}.git',

    'koji_server': 'https://koji.fedoraproject.org/kojihub',
    'koji_weburl': 'http://koji.fedoraproject.org/koji',

    'koji_cert': os.path.expanduser('~/.fedora.cert'),
    'koji_ca_cert': os.path.expanduser('~/.fedora-server-ca.cert'),

}

if 'BODHI_USER' in os.environ:
    defaults['username'] = os.environ['BODHI_USER']
    defaults['git_userstring'] = '%s <%s@fedoraproject.org>' % (
        defaults['username'], defaults['username'])


def load_config():
    """ Return tuple containing shipitrc config and fedmsg config """
    return load_shipitrc_config(), load_fedmsg_config()


def load_shipitrc_config():
    config = copy.copy(defaults)

    # Load common config from disk
    parser = configparser.ConfigParser()
    filename = os.path.expanduser('~/.config/shipit/shipitrc')
    print("Reading", filename)
    if not parser.read([filename]):
        # If no file was read, let's create one and quit
        sys.exit(shipit.wizard.run(filename))

    loaded = parser._sections['shipit']

    config.update(loaded)

    typecasts = {
        'logsize': int,
        'http.threads': int,
    }

    for key, cast in typecasts.items():
        config[key] = cast(config[key])

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
