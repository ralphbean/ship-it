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

import shipit.controllers

from shipit.log import log

class HelpContext(shipit.controllers.BaseContext):
    prompt = 'HELP'

    def __init__(self, *args, **kwargs):
        super(HelpContext, self).__init__(*args, **kwargs)
        self.command_map = {
            'q': self.switch_main,
            'esc': self.switch_main,
        }

    def assume_primacy(self):
        log('help assuming primacy')
        #log('%s' % pprint.pformat(self.build_help_dict()))

    def build_help_dict(self):
        return self.controller.build_help_dict()
