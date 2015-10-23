#!/usr/bin/env python
#
# Copyright Stefano Tranquillini - stefanotranquillini.me
# GNU GPL v2.0 
#
from google.appengine.api import users

__author__ = 'Stefano Tranquillini'

import os

from google.appengine.ext import deferred

from google.appengine.ext.ndb.key import Key
from google.appengine.ext.webapp import template
import webapp2
import jinja2
from webapp2_extras import auth, sessions

from webapp2_extras.auth import InvalidPasswordError, InvalidAuthIdError

from cron import sendMailCall
from models import Call, Config, Offer


# some support functions
def is_open_or_close():
    c = Config.query().get()
    if not c:
        c = Config()
        c.is_open = False
        c.put()
        return False
    return c.is_open


# code found online
def user_required(handler):
    """
      Decorator that checks if there's a user associated with the current session.
      Will also fail if there's no session present.
    """

    def check_login(self, *args, **kwargs):
        auth = self.auth
        g_user = None
        if users.get_current_user():
            g_user = self.user_model.get_by_auth_id(users.get_current_user().email())
        if not g_user and not auth.get_user_by_session():
            self.redirect(self.uri_for('login'), abort=True)
        else:
            return handler(self, *args, **kwargs)

    return check_login


class BaseHandler(webapp2.RequestHandler):
    @webapp2.cached_property
    def auth(self):
        """Shortcut to access the auth instance as a property."""
        return auth.get_auth()

    @webapp2.cached_property
    def user_info(self):
        """Shortcut to access a subset of the user attributes that are stored
        in the session.

        The list of attributes to store in the session is specified in
          config['webapp2_extras.auth']['user_attributes'].
        :returns
          A dictionary with most user information
        """
        return self.auth.get_user_by_session()

    @webapp2.cached_property
    def user(self):
        """Shortcut to access the current logged in user.

        Unlike user_info, it fetches information from the persistence layer and
        returns an instance of the underlying model.

        :returns
          The instance of the user model associated to the logged in user.
        """
        if users.get_current_user():
            return self.user_model.get_by_auth_id(users.get_current_user().email())
        else:
            u = self.user_info
            return self.user_model.get_by_id(u['user_id']) if u else None

    @webapp2.cached_property
    def user_model(self):
        """Returns the implementation of the user model.

        It is consistent with config['webapp2_extras.auth']['user_model'], if set.
        """
        return self.auth.store.user_model

    @webapp2.cached_property
    def session(self):
        """Shortcut to access the current session."""
        return self.session_store.get_session(backend="datastore")

    def render_template(self, view_filename, params={}):
        if self.user:
            params['username'] = self.user.username
            if users.get_current_user():
                params['logout'] = users.create_logout_url('/')
        path = os.path.join(os.path.dirname(__file__), 'templates', view_filename)
        self.response.out.write(template.render(path, params))

    def display_message(self, message):

        """Utility function to display a template with a simple message."""
        params = {
            'message': message
        }
        self.render_template('message.html', params)

    # this is needed for webapp2 sessions to work
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)


class LoginHandler(BaseHandler):
    def get(self):
        self._serve_page()

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        try:
            u = self.auth.get_user_by_password(username, password, remember=True,
                                               save_session=True)
            self.redirect(self.uri_for('home'))
        except (InvalidAuthIdError, InvalidPasswordError) as e:
            print 'Login failed for user %s because of %s' % (username, type(e))
            self._serve_page(True)

    def _serve_page(self, failed=False):
        username = self.request.get('username')
        error = None
        if users.get_current_user() and not self.user_model.get_by_auth_id(users.get_current_user().email()):
            error = "l'utente google non e' abilitato a usare questo sito. Fare logout"
        params = {
            'username': username,
            'failed': failed,
            'google_login': users.create_login_url('/'),
            'error': error,
            'google_logout': users.create_logout_url(
                '/')
        }
        self.render_template('login.html', params)


class LogoutHandler(BaseHandler):
    def get(self):
        self.auth.unset_session()
        self.redirect(self.uri_for('home'))


class OfferHandler(BaseHandler):
    @user_required
    def get(self, call):
        self.render_template('offer.html', dict(call=call))

    @user_required
    def post(self, call):
        ids = Offer.allocate_ids(size=1)

        user = self.user
        call = Key(urlsafe=call).get()
        taglio = self.request.get('taglio')
        offerta = self.request.get('offerta')
        o = Offer(id=ids[0])
        o.team = user.key
        o.cut = taglio
        o.price = int(offerta)
        o.put()
        call.offers.append(o.key)
        call.put()
        self.render_template('message.html', params=dict(message="offerta ricevuta"))


class CallHandler(BaseHandler):
    @user_required
    def get(self):
        if is_open_or_close():
            self.render_template('call.html')

    @user_required
    def post(self):
        # we need to create the id before, GAE is slow at this
        ids = Call.allocate_ids(size=1)
        user = self.user
        call = Call(id=ids[0])
        call.player = self.request.get('giocatore')
        call.called_by = user.key
        call.put()
        # deffer the task
        # sendMailCall(call)
        deferred.defer(sendMailCall, call=call)
        # redirect to Offer
        self.redirect(self.uri_for('offer', call=call.key.urlsafe()))


class DeleteHandler(BaseHandler):
    @user_required
    def get(self, call):
        # that's bad approach, but it's the fastest one
        call = Key(urlsafe=call).get()
        user = self.user
        o = None
        j = -1
        i = j
        # search for the offer in the call
        for offer in call.offers:
            j += 1
            t_offer = offer.get()
            if t_offer.team == user.key:
                print 'found'
                o = offer
                i = j
                break
        if i > -1:
            # delete it.
            del call.offers[i]
            call.put()
        if o:
            o.delete()
        self.render_template('message.html', params=dict(message="offerta eliminata"))


class MainHandler(BaseHandler):
    @user_required
    def get(self):
        calls_open = Call.query(Call.status == "OPEN").fetch()
        calls_past = Call.query(Call.status == "CLOSED").fetch()
        template_values = dict(open=[e.to_dict(self.user) for e in calls_open], past=[e.to_dict() for e in calls_past],
                               is_open=is_open_or_close())
        self.render_template('index.html', template_values)


config = {
    'webapp2_extras.sessions': {
        'secret_key': 'mnweo82746^2332-0)(#$`1$13$$1114&&!^'
    }
}
app = webapp2.WSGIApplication([
    webapp2.Route('/delete/<call>', DeleteHandler, name='offer_delete'),
    webapp2.Route('/offer/<call>', OfferHandler, name='offer'),
    webapp2.Route('/call', CallHandler, name='call'),
    webapp2.Route('/login', LoginHandler, name='login'),
    webapp2.Route('/logout', LogoutHandler, name='logout'),
    webapp2.Route('/', MainHandler, name='home'),

], debug=True, config=config)

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
