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


def assemble_controller(config, fedmsg_config, ui, palette, model):
    return MasterController(config, fedmsg_config, ui, palette, model)


class MasterController(object):
    """ Master controller.

    This thing is responsible for remembering what context we are in (main,
    anitya, rawhide..).  It is also responsible for changing the context and
    setting the UI appropriately.  All keypresses should flow through here.
    """
    def __init__(self, config, fedmsg_config, ui, palette, model):
        self.config = config
        self.fedmsg_config = fedmsg_config
        self.ui = ui
        self.palette = palette
        self.model = model

        # Import these in here to avoid circular imports
        import shipit.controllers.main

        import shipit.controllers.anitya
        import shipit.controllers.help

        self.contexts = {
            'main': shipit.controllers.main.MainContext(self),
            'anitya': shipit.controllers.anitya.AnityaContext(self),
            'help': shipit.controllers.help.HelpContext(self),
        }
        self.set_context('main')

    def set_context(self, name):
        self.context = name
        context = self.contexts[self.context]
        context.assume_primacy()
        self.ui.commandbar.set_prompt(context.prompt)
        self.ui.commandbar.set_text(self.short_command_help())
        self.ui.filterbar.set_prompt(' ' * len(context.prompt))
        self.ui.filterbar.set_text(self.short_filter_help())

    def keypress(self, key):
        if isinstance(key, tuple):
            # Then it is actually a mouse click.
            return
        context = self.contexts[self.context]
        context.keypress(key)  # Ignore the result

    def short_command_help(self):
        return self._short_help(0)

    def short_filter_help(self):
        return self._short_help(1)

    def _short_help(self, index):
        help_dict = self.build_help_dict()[index][self.context]

        short_docs = collections.defaultdict(list)
        for key, docs in help_dict.items():
            short, long = docs
            short_docs[short].append(key)

        return "   ".join([
            "%s - %s" % ("|".join(keys), s) for s, keys in sorted(
                short_docs.items(), key=operator.itemgetter(0))
        ])

    def build_help_dict(self):
        cmds = collections.defaultdict(lambda: collections.defaultdict(dict))
        for name, context in self.contexts.items():
            for key, function in context.command_map.items():
                doc = inspect.getdoc(function)
                short, long = doc.split(' | ', 1)
                cmds[name][key] = (short, long)

        flts = collections.defaultdict(lambda: collections.defaultdict(dict))
        for name, context in self.contexts.items():
            for key, function in context.filter_map.items():
                doc = inspect.getdoc(function)
                short, long = doc.split(' | ', 1)
                flts[name][key] = (short, long)

        return cmds, flts


class BaseContext(object):
    __metaclass__ = abc.ABCMeta
    prompt = '?????'

    def __init__(self, controller, *args, **kwargs):
        self.controller = controller
        self.command_map = {}
        self.filter_map = {}
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

        # First, see if any mixins want to handle this
        parent = super(BaseContext, self)
        if hasattr(parent, 'keypress'):
            result = parent.keypress(key)
            if result is None:
                return None

        # Look for the command and run it
        if key in self.command_map:
            row = self.controller.ui.get_active_row()
            return self.command_map[key](key, [row])

        # Capital-cased commands can be applied in batch
        if key.lower() in self.command_map:
            rows = self.controller.ui.listbox.reference
            self.command_map[key.lower()](key, rows)

        # Otherwise, check the list of filters to apply
        if key in self.filter_map:
            return self.filter_map[key](key)

        return key

    def switch_main(self, key, rows):
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

        self.filter_map.update({
            '/': self.start_search,
        })

    def trigger_filtration(self):
        """ Tell the UI to reconsider its list of filter callbacks. """
        self.controller.ui.listbox.filter_results()
        if self.accepting:
            self.controller.ui.commandbar.set_text('/' + self.pattern)

    def insert_callback(self):
        """ Add our callback to the UI filterer. """

        def callback(package):
            return re.search(self.pattern, package.name)

        return self.controller.ui.listbox.add_filter('search', callback)

    def remove_callback(self):
        """ Remove our callback from the UI filterer.

        Returns the callback if it was there.  Returns None if it was not.
        """
        return self.controller.ui.listbox.remove_filter('search')


    def start_search(self, key):
        """ Search | Filter packages with a regular expression. """
        if not self.controller.ui.listbox.initialized():
            return key
        self.accepting, self.pattern = True, ''
        self.insert_callback()

    def end_search(self):
        self.accepting, self.pattern = False, ''
        self.controller.ui.commandbar.set_text(
            self.controller.short_command_help())

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
