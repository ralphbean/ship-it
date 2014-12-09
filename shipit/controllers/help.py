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

import shipit.controllers
import shipit.ui


def doccols(section, key, doc):
    return urwid.Columns([
        (7, urwid.Text(section, align='right')),
        (7, urwid.Text(key, align='center')),
        (65, urwid.Text(doc, align='left')),
    ], dividechars=1)


class DocRow(shipit.ui.BaseRow):
    legend = doccols('mode', 'keys', 'documentation')

    def __init__(self, section, key, doc):
        self._selectable = not (section)
        super(DocRow, self).__init__(urwid.AttrMap(
            doccols(section, key, doc), None, 'reversed'))

    def selectable(self):
        return self._selectable


class HelpContext(shipit.controllers.BaseContext):
    prompt = 'HELP'

    def __init__(self, *args, **kwargs):
        super(HelpContext, self).__init__(*args, **kwargs)
        self.command_map = collections.OrderedDict([
            ('q', self.switch_main),
            ('esc', self.switch_main),
        ])

    def switch_main(self, key, rows):
        """ Back | Close this help menu. """
        self.controller.ui.listbox.clear()
        self.controller.ui.listbox.set_originals(self.saved_originals)
        self.controller.ui.window.set_header(self.saved_header)
        super(HelpContext, self).switch_main(key, rows)

    def assume_primacy(self):
        self.saved_originals = self.controller.ui.listbox.originals
        self.saved_header = self.controller.ui.window.header

        help_dict = self.build_help_dict()
        collapsed = collections.defaultdict(
            lambda: collections.defaultdict(list))
        for kind, sections in help_dict.items():
            for section, items in sections.items():
                for key, docs in items.items():
                    short, long = docs
                    collapsed[section][long].append(key)

        rows = []
        for section in collapsed:
            rows.append(DocRow(section, '', ''))
            for doc in collapsed[section]:
                keys = "|".join(collapsed[section][doc])
                rows.append(DocRow('', keys, doc))

        self.controller.ui.listbox.clear()
        self.controller.ui.listbox.set_originals(rows)
        self.controller.ui.window.set_header(DocRow.legend)

    def build_help_dict(self):
        return self.controller.build_help_dict()
