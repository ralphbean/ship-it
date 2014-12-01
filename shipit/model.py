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

import collections
import time

import twisted.internet.defer

from twisted.internet import utils

import shipit.reactor
import shipit.signals
import shipit.utils
from shipit.log import log


def assemble_model(config, fedmsg_config):
    return PackageList(config, fedmsg_config)


class Package(shipit.signals.AsyncNotifier):
    def __init__(self, pkgdb, *args, **kwargs):
        self.name = pkgdb['name']
        self.pkgdb = pkgdb
        self.rawhide = None
        self.upstream = None
        super(Package, self).__init__(*args, **kwargs)

    def __repr__(self):
        return "<Package %r>" % self.name

    def set_upstream(self, upstream):
        self.upstream = upstream
        self.signal('upstream', upstream)

    def set_rawhide(self, rawhide):
        self.rawhide = rawhide
        self.signal('rawhide', rawhide)


class PackageList(shipit.signals.AsyncNotifier, collections.OrderedDict):
    """ Primary DB object.
    Keeps a list of all your packages, with:
    - convenience methods for searching
    - callbacks, so the UI can be notified on changes.
    """
    nvr_dict = {}

    def __init__(self, config, fedmsg_config, *args, **kwargs):
        self.yum_conf = config['yum_conf']
        self.anitya_url = config['anitya_url']
        self.pkgdb_url = config['pkgdb_url']
        self.username = config['username']

        super(PackageList, self).__init__(*args, **kwargs)

    def __repr__(self):
        return "<PackageList>"

    @twisted.internet.defer.inlineCallbacks
    def build_nvr_dict(self):

        cmdline = ["/usr/bin/repoquery",
                "--quiet",
                "--config=%s" % self.yum_conf,
                "--archlist=src",
                "--all",
                "--qf",
                "'%{name}\t%{version}\t%{release}'"]

        #if repoid:
        #    cmdline.append('--repoid=%s' % repoid)

        start = time.time()
        yield log("Running %r" % ' '.join(cmdline))
        stdout = yield utils.getProcessOutput(cmdline[0], cmdline[1:])
        delta = time.time() - start
        yield log("Done with repoquery in %is" % delta)

        for line in stdout.split("\n"):
            line = line.strip().strip("'")
            if line:
                name, version, release = line.split("\t")
                self.nvr_dict[name] = (version, release)
                self.signal('rawhide', name, self.nvr_dict[name])

        yield log("Done building nvr dict with %i items" % len(self.nvr_dict))


    @twisted.internet.defer.inlineCallbacks
    def load_pkgdb_packages(self):
        url = self.pkgdb_url + '/api/packager/package/' + self.username
        yield log('Loading packages from ' + url)
        start = time.time()

        resp = yield shipit.utils.http.get(url)
        pkgdb = resp.json()

        for package in pkgdb['point of contact']:
            name = package['name']
            package = self[name] = Package(pkgdb=package)
            self.register('rawhide', name, package.set_rawhide)
            if name in self.nvr_dict:
                yield package.set_rawhide(self.nvr_dict.get(name))

        self.signal('pkgdb', self.items())

        delta = time.time() - start

        yield log('Found %i packages in %is' % (len(self), delta))

        deferreds = []
        for name in self:
            url = self.anitya_url + '/api/project/Fedora/' + name
            deferreds.append(shipit.utils.http.get(url))

        for d, name, package in zip(deferreds, *zip(*self.items())):
            response = yield d
            project = response.json()

            yield package.set_upstream(project)

        self.signal('initialized', self.items())

        delta = time.time() - start
        yield log('Done loading data in %is' % delta)
