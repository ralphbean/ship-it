import os
import random
import string
import time

import koji

from shipit.log import log


class Buildsys(object):
    def __init__(self, config):
        self.config = config

        self.server = config['koji_server']
        self.weburl = config['koji_weburl']

        self.cert = config['koji_cert']
        self.ca_cert = config['koji_ca_cert']

        #self.target_tag = config['koji_target_tag']

        self.priority = 30
        self.opts = {'scratch': True}

    def session_maker(self):
        koji_session = koji.ClientSession(self.server, {'timeout': 3600})
        koji_session.ssl_login(self.cert, self.ca_cert, self.ca_cert)
        return koji_session

    def url_for(self, task_id):
        return self.weburl + '/taskinfo?taskID=%i' % task_id

    @staticmethod
    def _unique_path(prefix):
        """ Create a unique path fragment.

        This is a copy and paste from /usr/bin/koji.
        """
        suffix = ''.join([
            random.choice(string.ascii_letters) for i in range(8)
        ])
        return '%s/%r.%s' % (prefix, time.time(), suffix)

    def upload_srpm(self, session, source):
        log('Uploading {source} to koji'.format(source=source))
        serverdir = self._unique_path('cli-build')
        session.uploadWrapper(source, serverdir)
        return "%s/%s" % (serverdir, os.path.basename(source))

    def scratch_build(self, session, name, source, target_tag):
        remote = self.upload_srpm(session, source)
        log('Intiating koji build for %r' % dict(
            name=name, target=target_tag, source=remote, opts=self.opts))
        task_id = session.build(
            remote, target_tag, self.opts, priority=self.priority)
        log('Done: task_id={task_id}'.format(task_id=task_id))
        return task_id
