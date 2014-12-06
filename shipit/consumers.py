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

import traceback
import uuid

import fedmsg.consumers

import shipit.log


def log_errors(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            for line in traceback.format_exc().strip().split('\n'):
                shipit.log.log(line)
    return wrapper


class ShipitConsumer(fedmsg.consumers.FedmsgConsumer):
    config_key = unicode(uuid.uuid4())
    topic = '*'

    def __init__(self, hub, model):
        self.model = model
        super(ShipitConsumer, self).__init__(hub)

    @log_errors
    def consume(self, msg):
        topic, msg = msg['topic'], msg['body']

        # Just dev debugging
        if 'anitya' in topic:
            shipit.log.log('received fedmsg %r' % topic)

        if 'anitya.project.map' in topic:
            message = msg['msg']['message']
            packagename = message['new']
            if message['distro'] == 'Fedora' and packagename in self.model:
                shipit.log.log('Setting upstream on %r' % packagename)
                self.model[packagename].set_upstream(msg['msg']['project'])
            else:
                shipit.log.log('Did not set upstream.')
        elif 'anitya.project.version' in topic:
            package = None
            for mapping in msg['msg']['message']['packages']:
                packagename = mapping['package_name']
                if mapping['distro'] == 'Fedora' and packagename in self.model:
                    package = packagename
                    break

            if not package:
                return

            self.model[package].set_upstream(msg['msg']['project'])



all_consumers = [ShipitConsumer]
