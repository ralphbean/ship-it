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

    @abc.abstractmethod
    def keypress(self, key):
        """ Handle keypress for each context.

        Each context has its own commands which should be handled here.
        """
        return key

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

    def assume_primacy(self):
        pass

    def keypress(self, key):
        log('MainContext saw key %r' % key)
        # First, see if any mixins want to handle this
        result = super(MainContext, self).keypress(key)
        if result is None:
            return None

        if key in ['q', 'Q']:
            raise urwid.ExitMainLoop()
        if key in ['?']:
            return self.controller.set_context('help')
        if key in ['a']:
            return self.controller.set_context('anitya')

        return key

class AnityaContext(BaseContext):
    prompt = 'ANITYA'

    def assume_primacy(self):
        log('anitya assuming primacy')

    def keypress(self, key):
        log('anitya keypress %r' % key)

        if key in ['q', 'Q', 'esc']:
            return self.controller.set_context('main')


class HelpContext(BaseContext):
    prompt = 'HELP'

    def assume_primacy(self):
        log('help assuming primacy')

    def keypress(self, key):
        log('help keypress %r' % key)
