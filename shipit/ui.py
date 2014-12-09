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

import urwid

import shipit.log
import shipit.utils

# TODO kill this, global state
row_actions, batch_actions = None, None


class BaseRow(urwid.WidgetWrap):
    def keypress(self, size, key):
        return key

    def selectable(self):
        return True


def pkgcols(a, b, c, d):
    return urwid.Columns([
        (40, urwid.Text(a)),
        (5, urwid.Text(b, align='center')),
        (13, urwid.Text(c, align='right')),
        (32, urwid.Text(d, align='right')),
    ], dividechars=1)


class PackageRow(BaseRow):
    legend = pkgcols(u'package', u'match', u'upstream', u'rawhide')

    def __init__(self, package):
        self.package = package
        self.name = package.pkgdb['name']
        loading = '(loading...)'
        super(PackageRow, self).__init__(urwid.AttrMap(
            pkgcols(self.name, u'', loading, loading), None, 'reversed'))
        if self.package.rawhide:
            self.set_rawhide(self.package.rawhide)
        if self.package.upstream:
            self.set_upstream(self.package.upstream)

    def __repr__(self):
        return "<PackageRow %r>" % self.name

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


class StatusBar(urwid.Text):
    """ One of the little one-line bar at the very bottom.  """

    prompt = '    '

    def __repr__(self):
        return "<StatusBar>"

    def set_text(self, markup):
        self.markup = markup
        super(StatusBar, self).set_text(self.prompt + '   ' + markup)

    def set_prompt(self, prompt):
        self.prompt = prompt
        self.set_text(self.markup)


class FilterableListBox(urwid.ListBox):
    """ The big main view of all your packages... """

    def __init__(self, commandbar):
        self.commandbar = commandbar
        self.filters = {}
        self.reference = []
        self.set_originals([])
        super(FilterableListBox, self).__init__(self.reference)

    def __repr__(self):
        return "<FilterableListBox>"

    def initialized(self):
        return bool(self.originals)

    def set_originals(self, originals):
        self.originals = copy.copy(originals)
        self.filter_results()

    def add_filter(self, name, callback):
        self.filters[name] = callback

    def remove_filter(self, name):
        return self.filters.pop(name, None)

    def clear(self):
        while self.reference:
            self.reference.pop()

    def filter_results(self):
        # Add in all the originals on which *all* callbacks agree
        for i, item in enumerate(self.originals):
            if item in self.reference:
                continue
            if all([check(item) for check in self.filters.values()]):
                self.reference.insert(i, item)

        # Remove any with which *at least one* callback disagrees
        for item in list(self.reference):
            if item not in self.reference:
                continue
            if any([not check(item) for check in self.filters.values()]):
                self.reference.remove(item)


class MainUI(urwid.Frame):
    def get_active_row(self):
        return self.listbox.focus


def assemble_ui(config, fedmsg_config, model):
    logsize = config['logsize']

    def basic_batch(func):
        def decorated(list_object):
            for item in list_object.reference:
                func(item)
        return decorated

    logbox = urwid.BoxAdapter(urwid.ListBox(shipit.log.logitems), logsize)
    logbox = urwid.LineBox(logbox, 'Logs')

    filterbar = StatusBar('')
    commandbar = StatusBar('Initializing...')
    footer = urwid.Pile([filterbar, commandbar])
    listbox = FilterableListBox(commandbar=commandbar)

    # Wire up some async update signals.  See shipit.signals.
    def initialize(packages):
        rows = [PackageRow(package) for name, package in packages]
        listbox.set_originals(rows)
        for row, name, package in zip(rows, *zip(*packages)):
            package.register('rawhide', None, row.set_rawhide)
            package.register('upstream', None, row.set_upstream)
    model.register('pkgdb', None, initialize)

    window = urwid.Frame(listbox, header=PackageRow.legend)
    main = MainUI(urwid.Frame(window, footer=logbox), footer=footer)

    # Hang these here for easy reference
    main.filterbar = filterbar
    main.commandbar = commandbar
    main.listbox = listbox
    main.window = window

    # TODO - someday make this configurable from shipitrc
    palette = [
        ('reversed', 'standout', '')
    ]

    return main, palette
