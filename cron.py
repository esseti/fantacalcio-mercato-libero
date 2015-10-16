#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os

from google.appengine.api import mail
import webapp2
from webapp2_extras.appengine.auth.models import User
from google.appengine.ext.webapp import template

from models import Config, Call


def set_open_or_closed(v):
    c = Config.query().get()
    if not c:
        c = Config()
    c.is_open = v
    c.put()


def sendMailCall(call):
    #TODO: fix template
    message = mail.EmailMessage(sender="MercatoLibero <noreply@st-ml-gae.appspotmail.com>",
                                subject="Nuova chiamata")
    users = User.query().fetch()
    to = ""
    for user in users:
        to += user.email + ";"
    message.to = to
    path = os.path.join(os.path.dirname(__file__), 'templates', 'mail_call.html')
    calls_open = Call.query(Call.status == "OPEN").fetch()
    open = [e.to_dict() for e in calls_open]
    params = dict(call=call.to_dict(), open=open)
    res = template.render(path, params)
    message.html = res
    message.send()


def sendMailResult():
    # TODO: test this
    message = mail.EmailMessage(sender="MercatoLibero <noreply@st-ml-gae.appspotmail.com>",
                                subject="Risultati")
    users = User.query().fetch()
    to = ""
    for user in users:
        to += user.email + ";"
    message.to = to
    calls_open = Call.query(Call.status == "OPEN").fetch()
    status = Config.query().get()
    if not status:
        status = Config()
    status.is_open = True
    status.put()
    if len(calls_open) > 0:
        path = os.path.join(os.path.dirname(__file__), 'templates', 'mail_call.html')
        params = dict(open=[e.to_dict() for e in calls_open])
        res = template.render(path, params)
        for o in calls_open:
            o.status = "CLOSED"
            o.put()
        message.html = res
        message.send()


class MailHandler(webapp2.RequestHandler):
    def get(self):
        sendMailResult()
        self.response.write("cron done!")


class StopCalls(webapp2.RequestHandler):
    def get(self):
        status = Config.query().get()
        if not status:
            status = Config()
        status.is_open = False
        status.put()


app = webapp2.WSGIApplication([
    ('/tasks/result', MailHandler),
    ('/tasks/stop', StopCalls),
], debug=True)
