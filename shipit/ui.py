# -*- coding: utf-8 -*-
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

import urwid

import shipit.log
import shipit.utils

from shipit.log import log

# TODO kill this, global state
row_actions, batch_actions = None, None

def cols(a, b, c, d):
    return urwid.Columns([
        (40, urwid.Text(a)),
        (5, urwid.Text(b, align='center')),
        (13, urwid.Text(c, align='right')),
        (32, urwid.Text(d, align='right')),
    ], dividechars=1)


class Row(urwid.WidgetWrap):

    legend = cols(u'package', u'match', u'upstream', u'rawhide')

    def __init__(self, package):
        self.package = package
        self.name = package.pkgdb['name']
        loading = '(loading...)'
        super(Row, self).__init__(urwid.AttrMap(
            cols(self.name, u'', loading, loading), None, 'reversed'))
        if self.package.rawhide:
            self.set_rawhide(self.package.rawhide)
        if self.package.upstream:
            self.set_upstream(self.package.upstream)

    def __repr__(self):
        return "<Row %r>" % self.name

    def keypress(self, size, key):
        return key

    def set_rawhide(self, rawhide):
        self.rawhide = rawhide
        version, release = rawhide
        column = 3  # Column number
        self._w.original_widget.contents[column][0].set_text(version)
        self.update_match()
        return shipit.utils.noop()

    def get_rawhide(self):
        column = 3  # Column number
        return self._w.original_widget.contents[column][0].get_text()[0]

    def set_upstream(self, upstream):
        column = 2  # Column number
        self.upstream = upstream
        version = upstream.get('version', '(not found)')
        version = version or '(not checked)'
        self._w.original_widget.contents[column][0].set_text(version)
        self.update_match()
        return shipit.utils.noop()

    def get_upstream(self):
        column = 2  # Column number
        return self._w.original_widget.contents[column][0].get_text()[0]

    def update_match(self):
        rawhide, upstream = self.get_rawhide(), self.get_upstream()
        if '(' in rawhide or '(' in upstream:
            self.set_match(u'?')
        elif rawhide != upstream:
            self.set_match(u'✗')
        else:
            self.set_match(u'✓')

    def set_match(self, match):
        column = 1  # Column number
        self.match = match
        self._w.original_widget.contents[column][0].set_text(match)
        return shipit.utils.noop()

    def selectable(self):
        return True


class StatusBar(urwid.Text):
    """ The little one-line bar at the very bottom.  """

    default = '    '.join([
        '/ - Search',
        'a - Anitya',
        'q - Quit',
    ])
    prompt = '    '

    def __repr__(self):
        return "<StatusBar>"

    def set_text(self, markup=default):
        self.markup = markup
        super(StatusBar, self).set_text(self.prompt + '   ' + markup)

    def ready(self, *args, **kwargs):
        self.set_text()

    def set_prompt(self, prompt):
        self.prompt = prompt
        self.set_text(self.markup)


class FilterableListBox(urwid.ListBox):
    """ The big main view of all your packages... """

    def __init__(self, statusbar):
        self.statusbar = statusbar
        self.reference = []
        self.set_originals([])
        super(FilterableListBox, self).__init__(self.reference)

    def __repr__(self):
        return "<FilterableListBox>"

    def initialize(self, packages):
        rows = [Row(package) for name, package in packages]
        self.set_originals(rows)
        for row, name, package in zip(rows, *zip(*packages)):
            package.register('rawhide', None, row.set_rawhide)
            package.register('upstream', None, row.set_upstream)

    def initialized(self):
        return bool(self.originals)

    def set_originals(self, originals):
        self.originals = copy.copy(originals)
        self.filter_results(searchmode=False, pattern='')

    def filter_results(self, searchmode, pattern):
        for i, item in enumerate(self.originals):
            if re.search(pattern, item.name):
                if item not in self.reference:
                    self.reference.insert(i, item)

        for item in list(self.reference):
            if not re.search(pattern, item.name):
                self.reference.remove(item)

        if searchmode:
            self.statusbar.set_text('/' + pattern)


class MainUI(urwid.Frame):
    def get_active_row(self):
        return self.listbox.focus


def assemble_ui(config, fedmsg_config, model):
    anitya_url = config['anitya_url']
    logsize = config['logsize']

    def basic_batch(func):
        def decorated(list_object):
            for item in list_object.reference:
                func(item)
        return decorated


    logbox = urwid.BoxAdapter(urwid.ListBox(shipit.log.logitems), logsize)
    logbox = urwid.LineBox(logbox, 'Logs')

    statusbar = StatusBar('Initializing...')
    listbox = FilterableListBox(statusbar=statusbar)

    # Wire up some async update signals.  See shipit.signals.
    model.register('pkgdb', None, listbox.initialize)
    model.register('initialized', None, statusbar.ready)

    right = urwid.Frame(listbox, header=Row.legend)
    left = urwid.SolidFill('x')  # TODO -- eventually put a menu here
    columns = urwid.Columns([(12, left), right], 2)
    main = MainUI(urwid.Frame(columns, footer=logbox), footer=statusbar)

    # Hang these here for easy reference
    main.statusbar = statusbar
    main.listbox = listbox

    # TODO - someday make this configurable from shipitrc
    palette = [
        ('reversed', 'standout', '')
    ]

    return main, palette
