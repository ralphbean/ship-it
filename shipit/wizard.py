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

import getpass
import os

import shipit.config


default_yum_conf = """
[main]
cachedir=/var/tmp/ship-it-yum/rawhide/
keepcache=0
debuglevel=2
logfile=/var/tmp/ship-it-yum.log
exactarch=1
obsoletes=1
gpgcheck=1
plugins=1
installonly_limit=3

[rawhide]
name=Rawhide Source
failovermethod=priority
baseurl=http://download.fedoraproject.org/pub/fedora/linux/development/rawhide/source/SRPMS/
enabled=1
#metadata_expire=7d
gpgcheck=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$releasever-$basearch
skip_if_unavailable=False
"""


values = [
    ('username', 'Your FAS username.'),
    ('password',
     'Your FAS password.',
     'You can also set this to @oracle:<command> with a command that',
     'will print the password to stdout (like "pass").'),

    ('logsize', 'This is the size of the log window in the UI.'),
    ('logfile', 'Where should shipit store log files?'),

    ('yum_conf', 'The yum config file to be used by repoquery'),

    ('http.threads', 'How many threads should shipit use for http requests?'),

    ('pkgdb_url', 'URL of the pkgdb web app'),
    ('anitya_url', 'URL of anitya web app'),
]


def run(path):

    print()
    print("It appears you do not yet have shipit configured at %r" % path)
    print("This short wizard will set up the configuration for you.")
    print("Some options are required, but you can press <Enter> to accept")
    print("defaults for most values...")


    outlines = ["[shipit]\n"]
    for items in values:
        name, comments = items[0], items[1:]
        print()
        outlines.append('\n')
        for comment in comments:
            print(comment)
            outlines.append("# " + comment + '\n')

        prompt = name
        default = None
        if name in shipit.config.defaults:
            default = shipit.config.defaults[name]
            prompt += " [%s]" % unicode(default)

        prompt += ":  "

        if 'password' in name:
            value = getpass.getpass(prompt)
        else:
            value = raw_input(prompt)

        value = value.strip()

        if not value and default:
            value = unicode(default)
        elif not value:
            print("%r is required.  Exiting..." % name)
            return 1

        if name == 'yum_conf' and not os.path.exists(value):
            if not os.path.exists(os.path.dirname(value)):
                os.makedirs(os.path.dirname(value))
                print("Created %s" % os.path.dirname(value))

            with open(value, 'w') as f:
                f.write(default_yum_conf)

            print("Wrote %s" % value)

        outlines.append(name + ' = ' + value + '\n')

    with open(path, 'w') as f:
        f.writelines(outlines)

    print("Wrote %s" % path)
    print("Run 'shipit' to try again.")

    return 0
