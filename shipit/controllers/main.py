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

import urwid
import twisted.internet.defer

import shipit.controllers as base

from shipit.log import log


class MainContext(base.BaseContext, base.Searchable):
    prompt = 'READY'

    def __init__(self, *args, **kwargs):
        super(MainContext, self).__init__(*args, **kwargs)
        self.command_map.update(collections.OrderedDict([
            ('q', self.quit),
            ('esc', self.quit),
            ('?', self.switch_help),
            ('a', self.switch_anitya),
            ('b', self.switch_rawhide),
            ('d', self.debug),
        ]))
        #self.filter_map.update(collections.OrderedDict([
        #]))

    def assume_primacy(self):
        pass

    def quit(self, key, rows):
        """ Quit | Quit """
        raise urwid.ExitMainLoop()

    def switch_anitya(self, key, rows):
        """ Anitya | Enter anitya (release-monitoring.org) mode. """
        self.controller.set_context('anitya')

    def switch_rawhide(self, key, rows):
        """ Rawhide | Enter rawhide mode (scratch, koji, dist-git). """
        self.controller.set_context('rawhide')

    def switch_help(self, key, rows):
        """ Help | Help on available commands.. i.e., this menu """
        self.controller.set_context('help')

    @twisted.internet.defer.inlineCallbacks
    def debug(self, key, rows):
        """ Debug | Log some debug information about the highlighted row. """
        for row in rows:
            yield log('pkgdb: %r' % row.package.pkgdb)
            yield log('rawhide: %r' % (row.package.rawhide,))
            yield log('upstream: %r' % row.package.upstream)
