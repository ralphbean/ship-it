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

import os
import shutil
import tempfile
import traceback

import twisted.internet.defer

import shipit.controllers as base

from shipit.log import log
from shipit.utils import run
from shipit.buildsys import Buildsys


class BuildContext(base.BaseContext, base.Searchable):
    prompt = 'BUILD (%s)'

    def __init__(self, controller, branch, *args, **kwargs):
        self.branch = branch
        self.prompt = self.prompt % branch

        config = controller.config
        self.git_url = config['dist_git_url']
        self.userstring = config['git_userstring']

        self.koji = Buildsys(config)

        self.target_tag = {
            'rawhide': 'rawhide',
        }[self.branch]

        super(BuildContext, self).__init__(controller, *args, **kwargs)
        self.command_map.update({
            'q': self.switch_main,
            'esc': self.switch_main,

            'r': self.open_scratch_build,
        })
        self.filter_map.update({
        })

    def assume_primacy(self):
        log('build %r assuming primacy' % self.branch)

    @twisted.internet.defer.inlineCallbacks
    def open_scratch_build(self, key, rows):
        """ Scratch | Kick off a scratch build of a package """
        for row in rows:
            package = row.name
            upstream = row.package.upstream['version']
            if not upstream:
                log("Cannot bump %r, no upstream version found." % package)
                continue

            # Clone the package to a tempdir
            tmp = tempfile.mkdtemp(prefix='shipit-', dir='/var/tmp')
            try:
                url = self.git_url.format(package=package)
                log("Cloning %r to %r" % (url, tmp))
                output = yield run(['git', 'clone', url, tmp])

                specfile = tmp + '/' + package + '.spec'

                # This requires rpmdevtools-8.5 or greater
                cmd = [
                    '/usr/bin/rpmdev-bumpspec',
                    '--new', upstream,
                    '-c', '"Latest upstream, %s"' % upstream,
                    '-u', '"%s"' % self.userstring,
                    specfile,
                ]
                output = yield run(cmd)

                # First, get all patches and other sources from dist-git
                output = yield run(['fedpkg', 'sources'], cwd=tmp)

                # Then go and get the *new* tarball from upstream.
                # For these to work, it requires that rpmmacros be redefined to
                # find source files in the tmp directory.
                output = yield run(['spectool', '-g', specfile], cwd=tmp)
                macros = [
                    '-D', '%_topdir .',
                    '-D', '%_sourcedir .',
                    '-D', '%_srcrpmdir .',
                ]
                output = yield run(
                    ['rpmbuild'] + macros + ['-bs', specfile], cwd=tmp)

                srpm = os.path.join(tmp, output.strip().split()[-1])

                session = self.koji.session_maker()
                task_id = self.koji.scratch_build(
                    session, package, srpm, self.target_tag)

                shutil.rmtree(tmp)

                # TODO - register the task_id mapped to the package name with
                # the consumer so we can watch for success.

                yield twisted.internet.defer.returnValue(task_id)
            except:
                for line in traceback.format_exc().strip().split('\n'):
                    log(line)
                raise
