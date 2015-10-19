#!/usr/bin/env python
#
# Copyright Stefano Tranquillini - stefanotranquillini.me
# GNU GPL v2.0 
#
# Code for getting emails..

import logging
import webapp2
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

class LogSenderHandler(InboundMailHandler):
	def receive(self, mail_message):
		sender=mail_message.sender
		plaintext_bodies = mail_message.bodies('text/plain')
		for content_type, body in plaintext_bodies:
			text = body.decode()
		logging.info("Received a message from: %s %s", sender, text)
        
app = webapp2.WSGIApplication([LogSenderHandler.mapping()], debug=True)