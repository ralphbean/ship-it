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

import webbrowser

import twisted.internet.defer
import twisted.internet.utils
import txrequests
import urwid

import shipit.log
import shipit.reactor
import shipit.utils


# Global state
http = None

def noop():
    """ Returns a no-op twisted deferred. """
    d = twisted.internet.defer.Deferred()
    shipit.reactor.reactor.callLater(0, d.callback, None)
    return d


def initialize_http(config, fedmsg_config):
    global http
    http = txrequests.Session(maxthreads=config['http.threads'])


def vimify():
    """ Add vim keys to urwid """
    vim_keys = {
        'k':        'cursor up',
        'j':      'cursor down',
        'h':      'cursor left',
        'l':     'cursor right',
    }
    for key, value in vim_keys.items():
        urwid.command_map[key] = value


def patch_webbrowser():
    """ Patch the python stdlib webbrowser module.

    xdg and gvfs for unknown reasons produce garbage on stderr that messes up
    our display, so we remove them and happily fall back to firefox or whatever
    """
    for nuisance in ['xdg-open', 'gvfs-open']:
        if nuisance in webbrowser._tryorder:
            webbrowser._tryorder.remove(nuisance)


@twisted.internet.defer.inlineCallbacks
def run(cmd, cwd=None):
    yield shipit.log.log('(%s)$ %s' % (cwd, ' '.join(cmd)))

    out, err, code = yield twisted.internet.utils.getProcessOutputAndValue(
        cmd[0], args=cmd[1:], path=cwd)

    if err:
        yield shipit.log.log("stderr: %r" % err)

    if code != 0:
        yield shipit.log.log('ERROR:  return code %r' % code)
        raise Exception

    yield twisted.internet.defer.returnValue(out)
