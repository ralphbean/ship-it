import collections
import datetime
import time

import requests
import urwid

from twisted.internet import defer

# TODO - make this configurable
LOGSIZE = 10

pkgdb_url = 'https://admin.fedoraproject.org/pkgdb'


def cols(a, b, c):
    return urwid.Columns([
        (25, urwid.Text(a)),
        (10, urwid.Text(b)),
        urwid.Text(c, wrap='clip')
    ])

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
    def __init__(self, a, b, c):
        super(Row, self).__init__(
            urwid.AttrMap(cols(a, b, c), None, 'reversed'))

    def selectable(self):
        return True

    @defer.inlineCallbacks
    def keypress(self, size, key):
        yield log("Received keypress %r %r" % (size, key))
        # TODO - does this need to return the key to chain in urwid land?


@defer.inlineCallbacks
def load_pkgdb_packages():
    username = 'ralph'
    url = pkgdb_url + '/api/packager/package/' + username
    yield log('Loading packages from ' + url)
    start = time.time()
    resp = requests.get(url)
    pkgdb = resp.json()
    packages = [package for package in pkgdb['point of contact']]
    for package in packages:
        rows.append(Row(package['name'], '', ''))
    delta = time.time() - start
    yield log('Found %i packages in %is' % (len(packages), delta))


# XXX - global state
rows = []

listbox = urwid.ListBox(rows)
right = urwid.Frame(listbox, header=legend)

# TODO -- eventually put a menu here
left = urwid.SolidFill('x')

columns = urwid.Columns([(12, left), right], 2)
main = urwid.Frame(columns, footer=status)


palette = [
    ('reversed', 'standout', '')
]

from twisted.internet import epollreactor
epollreactor.install()
from twisted.internet import reactor
reactor.callWhenRunning(load_pkgdb_packages)
mainloop = urwid.MainLoop(main, palette, event_loop=urwid.TwistedEventLoop())
mainloop.run()
