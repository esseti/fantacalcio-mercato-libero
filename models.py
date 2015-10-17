#!/usr/bin/env python
#
# Copyright Stefano Tranquillini - stefanotranquillini.me
# GNU GPL v2.0 
#

from google.appengine.ext import ndb
from webapp2_extras.appengine.auth.models import User

__author__ = 'Stefano Tranquillini'


class Offer(ndb.Model):
    team = ndb.KeyProperty(kind=User)
    cut = ndb.StringProperty()
    price = ndb.IntegerProperty()
    dt = ndb.DateTimeProperty(auto_now_add=True)

    def to_dict(self, user=None):
        result = super(Offer, self).to_dict()
        result['team'] = self.team.get().username
        del result['dt']
        return result


class Call(ndb.Model):
    player = ndb.StringProperty()
    called_by = ndb.KeyProperty(kind=User)
    offers = ndb.KeyProperty(kind=Offer, repeated=True)
    status = ndb.StringProperty(choices=['OPEN', 'CLOSED'], default="OPEN")
    dt = ndb.DateTimeProperty(auto_now_add=True)

    def to_dict(self, user=None):
        result = super(Call, self).to_dict()
        del result['dt']
        result['called_by'] = self.called_by.get().username
        ofs = []
        offers = ndb.get_multi(self.offers)
        print offers
        print self.offers
        offers = sorted(offers, key=lambda o: o.price)
        for offer in offers:
            if user:
                if offer.team == user.key:
                    ofs.append(offer.to_dict())
            else:
                ofs.append(offer.to_dict())
        result['offers'] = ofs
        result['id'] = self.key.urlsafe()
        return result


class Config(ndb.Model):
    is_open = ndb.BooleanProperty()
