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

import time

import twisted.internet.defer

from twisted.internet import utils

import shipit.utils
from shipit.log import log

# TODO -- kill this.  we shouldn't import ui in model
import shipit.ui


def assemble_models(config, fedmsg_config):
    # TODO -- not sure what to do with this yet.
    return None

# TODO - global state for now :(
nvr_dict = {}

@twisted.internet.defer.inlineCallbacks
def build_nvr_dict(config, fedmsg_config):
    yum_conf = config['yum_conf']

    cmdline = ["/usr/bin/repoquery",
            "--quiet",
            "--config=%s" % yum_conf,
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
            nvr_dict[name] = (version, release)

    yield log("Done building nvr dict with %i items" % len(nvr_dict))


@twisted.internet.defer.inlineCallbacks
def load_pkgdb_packages(config, fedmsg_config):
    anitya_url = config['anitya_url']
    pkgdb_url = config['pkgdb_url']

    username = 'ralph'
    url = pkgdb_url + '/api/packager/package/' + username
    yield log('Loading packages from ' + url)
    start = time.time()

    resp = yield shipit.utils.http.get(url)
    pkgdb = resp.json()

    packages = [package for package in pkgdb['point of contact']]
    delta = time.time() - start
    for package in packages:
        package['upstream'] = '(loading...)'
        package['rawhide'] = '(loading...)'
        shipit.ui.rows.append(shipit.ui.Row(package))

    yield log('Found %i packages in %is' % (len(packages), delta))

    deferreds = []
    for package in packages:
        url = anitya_url + '/api/project/Fedora/' + package['name']
        deferreds.append(shipit.utils.http.get(url))

    for d, row in zip(deferreds, shipit.ui.rows):
        response = yield d
        project = response.json()

        if project.get('version'):
            yield row.set_upstream(project)
        else:
            yield row.set_upstream({})

        yield row.set_rawhide(nvr_dict.get(row.name, ('(not found)',))[0])

    shipit.ui.listbox.set_originals(shipit.ui.rows)

    delta = time.time() - start
    shipit.ui.statusbar.set_text()
    yield log('Done loading data in %is' % delta)
