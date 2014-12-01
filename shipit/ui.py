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
import urllib
import webbrowser

import twisted.internet.defer
import urwid

import shipit.log
import shipit.utils

from shipit.log import log

# TODO kill this, global state
row_actions, batch_actions = None, None

def cols(a, b, c):
    return urwid.Columns([
        (40, urwid.Text(a)),
        (13, urwid.Text(b, align='right')),
        (32, urwid.Text(c, align='right')),
    ], dividechars=1)


class Row(urwid.WidgetWrap):

    legend = cols(u'package', u'upstream', u'rawhide')

    def __init__(self, package):
        self.package = package
        self.name = package.pkgdb['name']
        loading = '(loading...)'
        super(Row, self).__init__(
            urwid.AttrMap(cols(self.name, loading, loading), None, 'reversed'))
        if self.package.rawhide:
            self.set_rawhide(self.package.rawhide)
        if self.package.upstream:
            self.set_upstream(self.package.upstream)

    def __repr__(self):
        return "<Row %r>" % self.name

    def set_rawhide(self, rawhide):
        self.rawhide = rawhide
        version, release = rawhide
        column = 2  # Column number
        self._w.original_widget.contents[column][0].set_text(version)
        return shipit.utils.noop()

    def get_rawhide(self):
        column = 2  # Column number
        return self._w.original_widget.contents[column][0].get_text()

    def set_upstream(self, upstream):
        column = 1  # Column number
        self.upstream = upstream
        version = upstream.get('version', '(not found)')
        version = version or '(not checked)'
        self._w.original_widget.contents[column][0].set_text(version)
        return shipit.utils.noop()

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


class StatusBar(urwid.Text):
    """ The little one-line bar at the very bottom.  """

    default = '    '.join([
        '/ - Search',
        'a - Anitya',
        'q - Quit',
    ])

    def __repr__(self):
        return "<StatusBar>"

    def set_text(self, markup=default):
        super(StatusBar, self).set_text('    ' + markup)

    def ready(self, *args, **kwargs):
        self.set_text()

class FilterableListBox(urwid.ListBox):
    """ The big main view of all your packages... """

    def __init__(self, statusbar):
        self.statusbar = statusbar
        self.searchmode, self.pattern = False, ''
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

    def filter_results(self):
        for i, item in enumerate(self.originals):
            if re.search(self.pattern, item.name):
                if item not in self.reference:
                    self.reference.insert(i, item)

        for item in list(self.reference):
            if not re.search(self.pattern, item.name):
                self.reference.remove(item)

        if self.searchmode:
            self.statusbar.set_text('/' + self.pattern)

    def start_search(self):
        self.searchmode, self.pattern = True, ''
        self.filter_results()

    def end_search(self, filter=True):
        self.searchmode, self.pattern = False, ''
        if filter:
            self.filter_results()
        self.statusbar.set_text()

    def set_originals(self, originals):
        self.originals = copy.copy(originals)
        self.filter_results()

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


def assemble_ui(config, fedmsg_config, model):
    global batch_actions
    global row_actions
    anitya_url = config['anitya_url']
    logsize = config['logsize']

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

    def new_anitya(row):
        data = dict(
            name=row.package.pkgdb['name'],
            homepage=row.package.pkgdb['upstream_url'],
            distro='Fedora',
            package_name=row.package.pkgdb['name'],
        )

        # Try to guess at what backend to prefill...
        backends = {
            'ftp.debian.org': 'Debian project',
            'www.drupal.org': 'Drupal7',
            'freecode.com': 'Freshmeat',
            'github.com': 'Github',
            'download.gnome.org': 'GNOME',
            'ftp.gnu.org': 'GNU project',
            'code.google.com': 'Google code',
            'hackage.haskell.org': 'Hackage',
            'launchpad.net': 'launchpad',
            'www.npmjs.org': 'npmjs',
            'packagist.org': 'Packagist',
            'pear.php.net': 'PEAR',
            'pecl.php.net': 'PECL',
            'pypi.python.org': 'PyPI',
            'rubygems.org': 'Rubygems',
            'sourceforge.net': 'Sourceforge',
        }
        for target, backend in backends.items():
            if target in row.package.pkgdb['upstream_url']:
                data['backend'] = backend
                break

        # It's not always the case that these need removed, but often enough...
        prefixes = [
            'python-',
            'php-',
            'nodejs-',
        ]
        for prefix in prefixes:
            if data['name'].startswith(prefix):
                data['name'] = data['name'][len(prefix):]

        # For these, we can get a pretty good guess at the upstream name
        easy_guesses = [
            'Debian project',
            'Drupal7',
            'Freshmeat',
            'Github',
            'GNOME',
            'GNU project',
            'Google code',
            'Hackage',
            'launchpad',
            'npmjs',
            'PEAR',
            'PECL',
            'PyPI',
            'Rubygems',
            'Sourceforge',
        ]
        for guess in easy_guesses:
            if data['backend'] == guess:
                data['name'] = data['homepage'].strip('/').split('/')[-1]

        url = anitya_url + '/project/new?' + urllib.urlencode(data)
        log("Opening %r" % url)
        webbrowser.open_new_tab(url)

    @twisted.internet.defer.inlineCallbacks
    def check_anitya(row):
        idx = row.upstream.get('id')
        if not idx:
            log("Cannot check anitya.  Anitya has no record of this.")
            return

        url = '%s/api/version/get' % anitya_url
        resp = yield shipit.utils.http.post(url, data=dict(id=idx))
        data = resp.json()
        if 'error' in data:
            log('Anitya error: %r' % data['error'])
        else:
            row.package.set_upstream(data)


    batch_actions = {
        'A': basic_batch(open_anitya)
    }

    row_actions = {
        'a': open_anitya,
        'n': new_anitya,
        'c': check_anitya,
    }


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
    main = urwid.Frame(urwid.Frame(columns, footer=logbox), footer=statusbar)

    # TODO - someday make this configurable from shipitrc
    palette = [
        ('reversed', 'standout', '')
    ]

    return main, palette
