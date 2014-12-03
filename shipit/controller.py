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

import abc
import collections
import inspect
import operator
import re
import urllib
import webbrowser

import urwid
import twisted.internet.defer

import shipit.utils

from shipit.log import log



def assemble_controller(config, fedmsg_config, ui, palette, model):
    return MasterController(config, fedmsg_config, ui, palette, model)


class MasterController(object):
    """ Master controller.

    This thing is responsible for remember what context we are in (main,
    anitya, rawhide..).  It is also responsible for changing the context and
    setting the UI appropriately.  All keypresses should flow through here.
    """
    def __init__(self, config, fedmsg_config, ui, palette, model):
        self.config = config
        self.fedmsg_config = fedmsg_config
        self.ui = ui
        self.palette = palette
        self.model = model

        self.contexts = {
            'main': MainContext(self),
            'anitya': AnityaContext(self),
            'help': HelpContext(self),
        }
        self.set_context('main')

    def set_context(self, name):
        self.context = name
        context = self.contexts[self.context]
        context.assume_primacy()
        self.ui.statusbar.set_prompt(context.prompt)
        self.ui.statusbar.set_text(self.short_help())

    def keypress(self, key):
        log('MasterController got key %r' % (key,))
        if isinstance(key, tuple):
            # Then it is actually a mouse click.
            return
        context = self.contexts[self.context]
        context.keypress(key)  # Ignore the result

    def short_help(self):
        help_dict = self.build_help_dict()[self.context]
        short_docs = collections.defaultdict(list)
        for key, docs in help_dict.items():
            short, long = docs
            short_docs[short].append(key)

        return "   ".join([
            "%s - %s" % ("|".join(keys), s) for s, keys in sorted(
                short_docs.items(), key=operator.itemgetter(0))
        ])

    def build_help_dict(self):
        result = collections.defaultdict(lambda: collections.defaultdict(dict))
        for name, context in self.contexts.items():
            for key, function in context.command_map.items():
                doc = inspect.getdoc(function)
                short, long = doc.split(' | ', 1)
                result[name][key] = (short, long)
        return result


class BaseContext(object):
    __metaclass__ = abc.ABCMeta
    prompt = '?????'

    def __init__(self, controller, *args, **kwargs):
        self.controller = controller
        self.command_map = {}
        super(BaseContext, self).__init__(*args, **kwargs)

    @abc.abstractmethod
    def assume_primacy(self):
        """ Gets called when this context becomes the active one.

        Contexts should adjust the UI to look however it should look.
        It could also trigger the model to do some async updates or...
        """
        pass

    def keypress(self, key):
        """ Handle keypress for each context.

        Each context has its own commands which should be handled here.
        """
        log('BaseContext saw key %r' % key)

        # First, see if any mixins want to handle this
        parent = super(BaseContext, self)
        if hasattr(parent, 'keypress'):
            result = parent.keypress(key)
            if result is None:
                return None

        if key in self.command_map:
            return self.command_map[key](key)

        return key

    def switch_main(self, key):
        """ Back | Return to the top-level context. """
        self.controller.set_context('main')


class Mixin(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def keypress(self, key):
        return key


class Searchable(Mixin):
    def __init__(self, *args, **kwargs):

        # accepting is a boolean indicating that we are accepting keystrokes
        self.accepting = False
        # pattern is the regex we are building to search with.
        self.pattern = ''

        super(Searchable, self).__init__(*args, **kwargs)

        self.command_map.update({
            '/': self.start_search,
        })

    def trigger_filtration(self):
        """ Tell the UI to reconsider its list of filter callbacks. """
        self.controller.ui.listbox.filter_results()
        if self.accepting:
            self.controller.ui.statusbar.set_text('/' + self.pattern)

    def insert_callback(self):
        """ Add our callback to the UI filterer. """
        return self.controller.ui.listbox.add_filter('search', self.check)

    def remove_callback(self):
        """ Remove our callback from the UI filterer.

        Returns the callback if it was there.  Returns None if it was not.
        """
        return self.controller.ui.listbox.remove_filter('search')

    def check(self, package):
        """ This is a callback called by the UI when it wants to know if this
        filter think it should include or exclude a given package from the
        view.
        """
        return re.search(self.pattern, package.name)

    def start_search(self, key):
        """ Search | Filter packages with a regular expression. """
        if not self.controller.ui.listbox.initialized():
            return key
        self.accepting, self.pattern = True, ''
        self.insert_callback()

    def end_search(self):
        self.accepting, self.pattern = False, ''
        self.controller.ui.statusbar.set_text(self.controller.short_help())

    def keypress(self, key):
        if not self.controller.ui.listbox.initialized():
            return key

        if key == 'esc':
            self.end_search()
            if self.remove_callback():
                self.trigger_filtration()
                return None
            else:
                return key
        elif not self.accepting:
            # If we have not already started a search, then don't intercept
            # keys further..
            return key
        elif key == 'enter':
            self.end_search()
        elif key == 'backspace' and self.accepting:
            if self.pattern:
                self.pattern = self.pattern[:-1]
            else:
                self.end_search()
                self.remove_callback()
            self.trigger_filtration()
        elif self.accepting:
            self.pattern += key
            self.trigger_filtration()
        else:
            return key  # unhandled

        return None  # handled


class MainContext(BaseContext, Searchable):
    prompt = 'READY'

    def __init__(self, *args, **kwargs):
        super(MainContext, self).__init__(*args, **kwargs)
        self.command_map.update({
            'q': self.quit,
            'esc': self.quit,
            '?': self.switch_help,
            'a': self.switch_anitya,

            'd': self.debug,
            's': self.add_silly,
            'r': self.remove_silly,
        })

    def assume_primacy(self):
        pass

    def quit(self, key):
        """ Quit | Quit """
        raise urwid.ExitMainLoop()

    def switch_anitya(self, key):
        """ Anitya | Enter anitya (release-monitoring.org) mode. """
        self.controller.set_context('anitya')

    def switch_help(self, key):
        """ Help | Help on available commands. """
        self.controller.set_context('help')

    @twisted.internet.defer.inlineCallbacks
    def debug(self, key):
        """ Debug | Log some debug information about the highlighted row. """
        row = self.controller.ui.get_active_row()
        yield log('pkgdb: %r' % row.package.pkgdb)
        yield log('rawhide: %r' % (row.package.rawhide,))
        yield log('upstream: %r' % row.package.upstream)

    def add_silly(self, key):
        """ Add Silly | Install a silly test filter. """
        def callback(package):
            return package.name.startswith('foobaz')
        self.controller.ui.listbox.add_filter('silly', callback)
        self.controller.ui.listbox.filter_results()

    def remove_silly(self, key):
        """ Remove Silly | Remove the silly test filter. """
        self.controller.ui.listbox.remove_filter('silly')
        self.controller.ui.listbox.filter_results()


class AnityaContext(BaseContext, Searchable):
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

    def assume_primacy(self):
        log('anitya assuming primacy')

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


class HelpContext(BaseContext):
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
