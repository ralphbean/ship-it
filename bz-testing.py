#!/usr/bin/env python

import bugzilla
import requests
import sys
import subprocess as sp



pkgdb_url = 'https://admin.fedoraproject.org/pkgdb'
anitya_url = 'https://release-monitoring.org'

username = 'ralph'
resp = requests.get(pkgdb_url + '/api/packager/package/' + username)
pkgdb = resp.json()
print pkgdb.keys()
for package in pkgdb['point of contact']:
    name = package['name']
    resp = requests.get(anitya_url + '/api/project/Fedora/' + name )
    project = resp.json()
    import pprint; pprint.pprint(project)


sys.exit(0)

advanced = True
ignore_cc = False

OPEN_STATUSES = [
    'NEW',
    'ASSIGNED',
    'NEEDINFO',
    'ON_DEV',
    'MODIFIED',
    'POST',
    'REOPENED',
    'ON_QA',
    'FAILS_QA',
    'PASSES_QA',
]

COLUMN_LIST = [
    'id',
    'summary',
    'priority',
    'component',
    'longdescs',
]


def get_password_pass(name):
    """ Get a password from the 'pass' gpg password store. """
    with open('/dev/null', 'r') as blackhole:
        cmd = ['pass', name]
        proc = sp.Popen(cmd, stdout=sp.PIPE, stderr=blackhole)
        stdout, _ = proc.communicate()
        return stdout.strip()



url = 'https://bugzilla.redhat.com'
username = 'rbean@redhat.com'
password = get_password_pass('sites/rhbz')

bz = bugzilla.Bugzilla(url)
bz.login(username, password)

query = dict(
    column_list=COLUMN_LIST,
    bug_status=OPEN_STATUSES,
    email1=username,
    emailreporter1=1,
    emailassigned_to1=1,
    emailqa_contact1=1,
    emailtype1="substring",
)

if not ignore_cc:
    query['emailcc1'] = 1

if advanced:
    # Required for new bugzilla
    # https://bugzilla.redhat.com/show_bug.cgi?id=825370
    query['query_format'] = 'advanced'

bugs = bz.query(query)

print len(bugs), "bugs found."
bugs = [bug for bug in bugs if 'is available' in bug.short_desc]
print len(bugs), "bugs are for new upstream releases."

for bug in bugs:
    print bug
    print bug.component
    package = bug.component
    version = bug.short_desc.split()[0].split(package)[1][1:]
    print package, "to", version


    ## Kick off a scratch build
    ## Clone the package to a tempdir
    #tmp = tempfile.mkdtemp(prefix='thn-', dir='/var/tmp')
    #try:
    #    url = self.git_url.format(package=package)
    #    self.log.info("Cloning %r to %r" % (url, tmp))
    #    sh.git.clone(url, tmp)

    #    specfile = tmp + '/' + package + '.spec'

    #    # This requires the latest rpmdevtools from git
    #    # https://fedorahosted.org/rpmdevtools/
    #    cmd = [
    #        '/usr/bin/rpmdev-bumpspec',
    #        '--new', upstream,
    #        '-c', '"Latest upstream, %s for #%s"' % (upstream, rhbz),
    #        '-u', '"%s"' % self.userstring,
    #        specfile,
    #    ]
    #    output = self.run(cmd)
    #    output = self.run(['spectool', '-g', specfile], cwd=tmp)
    #    output = self.run(['fedpkg', 'srpm'], cwd=tmp)

    #    srpm = output.strip().split()[-1]
    #    self.log.debug("Got srpm %r" % srpm)

    #    session = self.session_maker()
    #    task_id = self.scratch_build(session, package, srpm)
    #    return task_id
    #finally:
    #    self.log.debug("Removing %r" % tmp)
    #    shutil.rmtree(tmp)
    #    pass

    sys.exit(0)
