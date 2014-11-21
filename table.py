import collections
import datetime
import time

import txrequests
import urwid

from twisted.internet import defer, utils

# TODO - make this configurable
LOGSIZE = 20
THREADS = 10
YUM_CONF = 'conf/yum.conf'

pkgdb_url = 'https://admin.fedoraproject.org/pkgdb'
anitya_url = 'https://release-monitoring.org'


def cols(a, b, c):
    return urwid.Columns([
        (40, urwid.Text(a)),
        (13, urwid.Text(b, align='right')),
        (32, urwid.Text(c, align='right')),
    ], dividechars=1)

legend = cols(u'package', u'upstream', u'rawhide')

logitems = collections.deque(maxlen=LOGSIZE)
status = urwid.BoxAdapter(urwid.ListBox(logitems), LOGSIZE)
status = urwid.LineBox(status, 'Logs')


def log(msg):
    prefix = "[%s] " % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logitems.append(urwid.Text(prefix + msg))

    # We need to asynchronously update our logs while other inlineCallbacks
    # block are ongoing, so we do...
    d = defer.Deferred()
    reactor.callLater(0, d.callback, None)
    d.addCallback(lambda x: mainloop.draw_screen())
    return d


class Row(urwid.WidgetWrap):
    def __init__(self, package):
        for key, value in package.items():
            setattr(self, key, value)
        loading = '(loading...)'
        super(Row, self).__init__(
            urwid.AttrMap(cols(self.name, loading, loading), None, 'reversed'))

    def set_rawhide(self, value):
        rawhide = 2  # Column number
        self._w.original_widget.contents[rawhide][0].set_text(value)
        return log('Set %r rawhide to %r' % (self.name, self.get_rawhide()))

    def get_rawhide(self):
        rawhide = 2  # Column number
        return self._w.original_widget.contents[rawhide][0].get_text()

    def set_upstream(self, value):
        upstream = 1  # Column number
        self._w.original_widget.contents[upstream][0].set_text(value)
        return log('Set %r upstream to %r' % (self.name, self.get_upstream()))

    def get_upstream(self):
        upstream = 1  # Column number
        return self._w.original_widget.contents[upstream][0].get_text()

    def selectable(self):
        return True

    @defer.inlineCallbacks
    def keypress(self, size, key):
        yield log("Received keypress %r %r" % (size, key))
        # TODO - does this need to return the key to chain in urwid land?


@defer.inlineCallbacks
def build_nvr_dict(repoid='rawhide'):
    cmdline = ["/usr/bin/repoquery",
               "--quiet",
               "--config=%s" % YUM_CONF,
               "--archlist=src",
               "--all",
               "--qf",
               "'%{name}\t%{version}\t%{release}'"]

    if repoid:
        cmdline.append('--repoid=%s' % repoid)

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


@defer.inlineCallbacks
def load_pkgdb_packages():
    username = 'ralph'
    url = pkgdb_url + '/api/packager/package/' + username
    yield log('Loading packages from ' + url)
    start = time.time()

    resp = yield http_session.get(url)
    pkgdb = resp.json()

    packages = [package for package in pkgdb['point of contact']]
    delta = time.time() - start
    for package in packages:
        package['upstream'] = '(loading...)'
        package['rawhide'] = '(loading...)'
        rows.append(Row(package))

    yield log('Found %i packages in %is' % (len(packages), delta))

    deferreds = []
    for package in packages:
        url = anitya_url + '/api/project/Fedora/' + package['name']
        deferreds.append(http_session.get(url))

    for d, row in zip(deferreds, rows):
        response = yield d
        project = response.json()

        if project.get('version'):
            yield row.set_upstream(project['version'])
        else:
            yield row.set_upstream('(not found)')

        yield row.set_rawhide(nvr_dict.get(row.name, ('(not found)',))[0])

    delta = time.time() - start
    yield log('Done loading data in %is' % delta)


# XXX - global state
rows = []
nvr_dict = {}

listbox = urwid.ListBox(rows)
right = urwid.Frame(listbox, header=legend)

# TODO -- eventually put a menu here
left = urwid.SolidFill('x')

columns = urwid.Columns([(12, left), right], 2)
main = urwid.Frame(columns, footer=status)


palette = [
    ('reversed', 'standout', '')
]

# No need to install this, since txrequests does it at import-time.
#from twisted.internet import epollreactor
#epollreactor.install()

# TODO -- close this down nicely at shutdown
http_session = txrequests.Session(maxthreads=THREADS)

from twisted.internet import reactor
reactor.callWhenRunning(build_nvr_dict)
reactor.callWhenRunning(load_pkgdb_packages)
mainloop = urwid.MainLoop(main, palette, event_loop=urwid.TwistedEventLoop())
mainloop.run()
