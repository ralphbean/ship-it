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

import urwid

from twisted.internet import defer, utils

import shipit.config
import shipit.consumers
import shipit.producers
import shipit.log

from shipit.log import log
from shipit.utils import noop


def assemble_ui(config, fedmsg_config):
    anitya_url = config['anitya_url']
    pkgdb_url = config['pkgdb_url']
    logsize = config['logsize']
    yum_conf = config['yum_conf']

    def basic_batch(func):
        def decorated(list_object):
            for item in list_object.reference:
                func(item)
        return decorated

    def open_anitya(row):
        idx = row.upstream.get('id')
        if idx:
            url = '%s/project/%i' % (anitya_url, idx)
        else:
            url = '%s/projects/search/?pattern=%s' % (anitya_url, row.name)
        log("Opening %r" % url)
        webbrowser.open_new_tab(url)

    batch_actions = {
        'A': basic_batch(open_anitya)
    }

    row_actions = {
        'a': open_anitya
    }


    def cols(a, b, c):
        return urwid.Columns([
            (40, urwid.Text(a)),
            (13, urwid.Text(b, align='right')),
            (32, urwid.Text(c, align='right')),
        ], dividechars=1)

    legend = cols(u'package', u'upstream', u'rawhide')

    logbox = urwid.BoxAdapter(urwid.ListBox(shipit.log.logitems), logsize)
    logbox = urwid.LineBox(logbox, 'Logs')


    class StatusBar(urwid.Text):
        default = '    '.join([
            '/ - Search',
            'a - Anitya',
            'q - Quit',
        ])
        def set_text(self, markup=default):
            super(StatusBar, self).set_text('    ' + markup)

    statusbar = StatusBar('Initializing...')


    class FilterableListBox(urwid.ListBox):
        def __init__(self, items):
            self.reference = items
            self.set_originals([])
            self.searchmode, self.pattern = False, None
            super(FilterableListBox, self).__init__(items)

        def filter_results(self):
            for i, item in enumerate(self.originals):
                if re.search(self.pattern, item.name):
                    if item not in self.reference:
                        self.reference.insert(i, item)

            for item in list(self.reference):
                if not re.search(self.pattern, item.name):
                    self.reference.remove(item)

            if self.searchmode:
                statusbar.set_text('/' + self.pattern)

        def start_search(self):
            self.searchmode, self.pattern = True, ''
            self.filter_results()

        def end_search(self, filter=True):
            self.searchmode, self.pattern = False, ''
            if filter:
                self.filter_results()
            statusbar.set_text()

        def set_originals(self, originals):
            self.originals = copy.copy(originals)

        def keypress(self, size, key):
            if not self.originals:
                # Then we are not fully initialized, so just let keypresses pass
                return super(FilterableListBox, self).keypress(size, key)

            if key == '/':
                self.start_search()
            elif key == 'esc':
                self.end_search()
            elif key == 'enter':
                self.end_search(filter=False)
            elif key == 'backspace' and self.searchmode:
                if self.pattern:
                    self.pattern = self.pattern[:-1]
                else:
                    self.end_search()
                self.filter_results()
            elif self.searchmode:
                self.pattern += key
                self.filter_results()
            elif key in batch_actions:
                batch_actions[key](self)
            else:
                return super(FilterableListBox, self).keypress(size, key)


    class Row(urwid.WidgetWrap):
        def __init__(self, package):
            for key, value in package.items():
                setattr(self, key, value)
            loading = '(loading...)'
            super(Row, self).__init__(
                urwid.AttrMap(cols(self.name, loading, loading), None, 'reversed'))

        def set_rawhide(self, value):
            column = 2  # Column number
            self._w.original_widget.contents[column][0].set_text(value)
            return noop()

        def get_rawhide(self):
            column = 2  # Column number
            return self._w.original_widget.contents[column][0].get_text()

        def set_upstream(self, upstream):
            column = 1  # Column number
            self.upstream = upstream
            version = upstream.get('version', '(not found)')
            self._w.original_widget.contents[column][0].set_text(version)
            return noop()

        def get_upstream(self):
            column = 1  # Column number
            return self._w.original_widget.contents[column][0].get_text()

        def selectable(self):
            return True

        def keypress(self, size, key):
            log("Received keypress %r %r" % (size, key))
            if key in row_actions:
                row_actions[key](self)
            else:
                return key


    # XXX - global state
    rows = []
    nvr_dict = {}

    listbox = FilterableListBox(rows)
    right = urwid.Frame(listbox, header=legend)

    # TODO -- eventually put a menu here
    left = urwid.SolidFill('x')

    columns = urwid.Columns([(12, left), right], 2)
    main = urwid.Frame(urwid.Frame(columns, footer=logbox), footer=statusbar)

    # TODO - someday make this configurable from shipitrc
    palette = [
        ('reversed', 'standout', '')
    ]

    return main, palette
