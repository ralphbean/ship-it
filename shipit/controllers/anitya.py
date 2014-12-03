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

import urllib
import webbrowser

import twisted.internet.defer

import shipit.controllers as base
import shipit.utils

from shipit.log import log


class AnityaContext(base.BaseContext, base.Searchable):
    prompt = 'ANITYA'

    def __init__(self, *args, **kwargs):
        super(AnityaContext, self).__init__(*args, **kwargs)
        self.anitya_url = self.controller.config['anitya_url']
        self.command_map.update({
            'q': self.switch_main,
            'esc': self.switch_main,

            'o': self.open_anitya,
            'n': self.new_anitya,
            'c': self.check_anitya,
        })
        self.filter_map.update({
            'm': self.toggle_mismatch_filter,
            'a': self.toggle_missing_filter,
        })

    def assume_primacy(self):
        log('anitya assuming primacy')

    def toggle_mismatch_filter(self, key):
        """ Show Mismatches | Toggle showing only upstream/rawhide mismatches.
        """

        # First try to remove it.  If it was there, then bail
        if self.controller.ui.listbox.remove_filter('anitya_mismatch'):
            self.controller.ui.listbox.filter_results()
            return None

        # Otherwise, add it.
        def callback(package):
            rawhide, upstream = package.get_rawhide(), package.get_upstream()
            if '(' in rawhide or '(' in upstream:
                return False
            elif rawhide != upstream:
                return True
            else:
                return False

        self.controller.ui.listbox.add_filter('anitya_mismatch', callback)
        self.controller.ui.listbox.filter_results()

    def toggle_missing_filter(self, key):
        """ Show Missing | Toggle showing only packages missing from anitya.
        """

        # First try to remove it.  If it was there, then bail
        if self.controller.ui.listbox.remove_filter('anitya_missing'):
            self.controller.ui.listbox.filter_results()
            return None

        # Otherwise, add it.
        def callback(package):
            return package.get_upstream() == '(not found)'

        self.controller.ui.listbox.add_filter('anitya_missing', callback)
        self.controller.ui.listbox.filter_results()

    def open_anitya(self, key):
        """ Open | Open an anitya project in your web browser. """
        anitya_url = self.anitya_url
        row = self.controller.ui.get_active_row()
        idx = row.upstream.get('id')
        if idx:
            url = '%s/project/%i' % (anitya_url, idx)
        else:
            url = '%s/projects/search/?pattern=%s' % (anitya_url, row.name)
        log("Opening %r" % url)
        webbrowser.open_new_tab(url)

    def new_anitya(self, key):
        """ New | Add project to release-monitoring.org """
        anitya_url = self.anitya_url
        row = self.controller.ui.get_active_row()
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
    def check_anitya(self, key):
        """ Check | Force a check of the latest upstream package. """
        anitya_url = self.anitya_url
        row = self.controller.ui.get_active_row()
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
