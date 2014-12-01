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

import urwid

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

    def keypress(self, key):
        log('MasterController got key %r' % key)
        context = self.contexts[self.context]
        context.keypress(key)  # Ignore the result


class BaseContext(object):
    __metaclass__ = abc.ABCMeta
    prompt = '?????'

    def __init__(self, controller):
        self.controller = controller

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
        """ Return to the top-level context. """
        self.controller.set_context('main')


class Mixin(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def keypress(self, key):
        return key


class Searchable(Mixin):
    def keypress(self, key):
        log('Searchable saw key %r' % key)
        return key


class MainContext(BaseContext, Searchable):
    prompt = 'READY'

    def __init__(self, *args, **kwargs):
        super(type(self), self).__init__(*args, **kwargs)
        self.command_map = {
            'q': self.quit,
            'Q': self.quit,
            'esc': self.quit,
            '?': self.switch_help,
            'a': self.switch_anitya,
        }

    def assume_primacy(self):
        pass

    def quit(self, key):
        """ Quit """
        raise urwid.ExitMainLoop()

    def switch_anitya(self, key):
        """ Enter anitya (release-monitoring.org) mode. """
        self.controller.set_context('anitya')

    def switch_help(self, key):
        """ Help on available commands. """
        self.controller.set_context('help')


class AnityaContext(BaseContext):
    prompt = 'ANITYA'

    def __init__(self, *args, **kwargs):
        super(type(self), self).__init__(*args, **kwargs)
        self.command_map = {
            'q': self.switch_main,
            'Q': self.switch_main,
            'esc': self.switch_main,
        }

    def assume_primacy(self):
        log('anitya assuming primacy')


class HelpContext(BaseContext):
    prompt = 'HELP'

    def __init__(self, *args, **kwargs):
        super(type(self), self).__init__(*args, **kwargs)
        self.command_map = {
            'q': self.switch_main,
            'Q': self.switch_main,
            'esc': self.switch_main,
        }

    def assume_primacy(self):
        log('help assuming primacy')
        #log('%s' % pprint.pformat(self.build_help_dict()))

    def build_help_dict(self):
        result = collections.defaultdict(lambda: collections.defaultdict(dict))
        for name, context in self.controller.contexts.items():
            for key, function in context.command_map.items():
                result[name][key] = inspect.getdoc(function)
        return result
