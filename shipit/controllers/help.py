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

import shipit.controllers
import shipit.ui

from shipit.log import log


def doccols(a, b, c):
    return urwid.Columns([
        (12, urwid.Text(a, align='right')),
        (12, urwid.Text(b, align='left')),
        (50, urwid.Text(c, align='left')),
    ], dividechars=2)


class SectionRow(shipit.ui.BaseRow):
    def __init__(self, section):
        super(SectionRow, self).__init__(urwid.AttrMap(
            doccols(section, u'', u''), None, 'reversed'))


class DocRow(shipit.ui.BaseRow):
    def __init__(self, key, docs):
        super(DocRow, self).__init__(urwid.AttrMap(
            doccols(key, *docs), None, 'reversed'))


class HelpContext(shipit.controllers.BaseContext):
    prompt = 'HELP'

    def __init__(self, *args, **kwargs):
        super(HelpContext, self).__init__(*args, **kwargs)
        self.command_map = {
            'q': self.switch_main,
            'esc': self.switch_main,
        }

    def switch_main(self, key, rows):
        self.controller.ui.listbox.set_originals(self.saved_originals)
        super(HelpContext, self).switch_main(key, rows)

    def assume_primacy(self):
        log('help assuming primacy')
        self.saved_originals = self.controller.ui.listbox.originals

        rows = []
        help_dict = self.build_help_dict()
        log("help dict is %r" % (help_dict,))
        for kind, sections in help_dict.items():
            for section, items in sections.items():
                rows.append(SectionRow(section))
                for key, docs in items.items():
                    rows.append(DocRow(key, docs))

        self.controller.ui.listbox.set_originals(rows)

    def build_help_dict(self):
        return self.controller.build_help_dict()
