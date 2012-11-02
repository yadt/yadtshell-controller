#! /usr/bin/env python
import logging
import json

from yadtshellcontroller.fysom import Fysom


# fsm:
# send request
#     [waiting]
#         waiting_timeout
#             [failure]
#         requested action failed
#             [waiting]
#         requested action started
#             [pending]
#                 waiting_timeout
#                     [pending]
#                 pending_timeout
#                     [failure]
#                 requested action failed
#                     [failure]
#                 requested action finished
#                     [success]

class Controller(object):
    def __init__(self):
        self.logger = logging.getLogger()
        self.fsm = Fysom({
            'initial': 'idle',
            'events': [
                {'name': 'finished', 'src': 'idle', 'dst': 'success'},
                {'name': 'waiting_timeout', 'src': 'idle', 'dst': 'failure'},
                {'name': 'request', 'src': 'idle', 'dst': 'waiting'},
                {'name': 'waiting_timeout', 'src': 'waiting', 'dst': 'failure'},
                {'name': 'waiting_timeout', 'src': 'pending', 'dst': 'pending'},
                {'name': 'failed', 'src': 'waiting', 'dst': 'waiting'},
                {'name': 'started', 'src': 'waiting', 'dst': 'pending'},
                {'name': 'pending_timeout', 'src': 'pending', 'dst': 'failure'},
                {'name': 'failed', 'src': 'pending', 'dst': 'failure'},
                {'name': 'finished', 'src': 'pending', 'dst': 'success'},
                {'name': 'started', 'src': 'pending', 'dst': 'pending'}
            ],
            'callbacks': {
                'onwaiting': self.onwaiting,
                'onfailed': self.onfailed,
                'onpending': self.onpending,
                'onsuccess': self.onsuccess,
                'onfailure': self.onfailure
            }
        })

    def request(self, reactor, client, target, waiting_timeout, pending_timeout, cmd, args=None):
        self.fsm.onchangestate = self.logstatechange
        self.reactor = reactor
        self.client = client
        self.target = target
        self.waiting_timeout = waiting_timeout
        self.pending_timeout = pending_timeout
        self.cmd = cmd
        self.args = args
        if cmd == "info":
            self._init_info_()
            message = 'connect for info took longer than %i seconds' % self.waiting_timeout
        else:
            self._init_request_()
            message = 'start of yadtshell process on target took longer than %i seconds' % self.waiting_timeout
        self.reactor.callLater(
            self.waiting_timeout,
            self.fsm.waiting_timeout,
            msg=message)

    def _init_info_(self):
        self.client.onEvent = self.onInfo

    def onInfo(self, target, event):
        print json.dumps(event, indent=4)
        self.fsm.finished(msg='info received')

    def _init_request_(self):
        self.client.onEvent = self.onEvent
        self.client.addOnSessionOpenHandler(self.publish_request)

    def onsuccess(self, e):
            self.reactor.exitcode = 0
            self.reactor.stop()

    def onfailure(self, e):
            self.reactor.exitcode = 1
            self.reactor.stop()

    def onwaiting(self, e):
            self.reactor.callLater(
                self.waiting_timeout,
                self.fsm.waiting_timeout,
                msg="start took longer than %i seconds" % self.waiting_timeout)

    def onpending(self, e):
            self.reactor.callLater(
                self.pending_timeout,
                self.fsm.pending_timeout,
                msg="execution took longer than %i seconds" % self.pending_timeout)

    def onfailed(self, e):
        if e.src == 'waiting':
            self.logger.info('a yadtshell-receiver failed to start, waiting for more responses or timeout')
        else:
            self.logger.critical('%s %s' % (self.cmd, e.event))

    def logstatechange(self, e):
        self.logger.info('fsm: event "%s" received: [%s] -> [%s]' % (' '.join(filter(None, [e.msg, e.event])), e.src, e.dst))

    def onEvent(self, target, event):
        payload = None
        if event.get('payload'):
            try:
                payload = ' '.join(
                    ['%s=%s' % (key, value)
                        for d in event.get('payload')
                        for key, value in d.iteritems()
                    ])
            except Exception:
                pass
        self.logger.info('event "%s" received' % ' '.join(filter(None, [event['id'], event.get('cmd'), event.get('state'), payload])))
        if event.get('state'):
            fun = getattr(self.fsm, event.get('state'))
            if fun:
                fun(msg=event['id'])

    def publish_request(self):
        self.fsm.request(msg='%s on %s' % (self.cmd, self.target))
        self.client.publish_request_for_target(self.target, self.cmd, self.args)
