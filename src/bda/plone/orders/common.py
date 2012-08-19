import uuid
import datetime
from zope.interface import implementer
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from souper.interfaces import ICatalogFactory
from souper.soup import (
    get_soup,
    Record,
    NodeAttributeIndexer,
    NodeTextIndexer,
)
from node.utils import instance_property
from node.ext.zodb import OOBTNode
from bda.plone.checkout import CheckoutAdapter
from bda.plone.cart import (
    readcookie,
    deletecookie,
    extractitems,
    get_catalog_brain,
)
from bda.plone.cart.interfaces import ICartItemDataProvider


DT_FORMAT = '%m.%d.%Y-%H:%M'


@implementer(ICatalogFactory)
class BookingsCatalogFactory(object):

    def __call__(self, context=None):
        catalog = Catalog()
        uid_indexer = NodeAttributeIndexer('uid')
        catalog[u'uid'] = CatalogFieldIndex(uid_indexer)
        buyable_uid_indexer = NodeAttributeIndexer('buyable_uid')
        catalog[u'buyable_uid'] = CatalogFieldIndex(buyable_uid_indexer)
        order_uid_indexer = NodeAttributeIndexer('order_uid')
        catalog[u'order_uid'] = CatalogFieldIndex(order_uid_indexer)
        creator_indexer = NodeAttributeIndexer('creator')
        catalog[u'creator'] = CatalogFieldIndex(creator_indexer)
        created_indexer = NodeAttributeIndexer('created')
        catalog[u'created'] = CatalogFieldIndex(created_indexer)
        exported_indexer = NodeAttributeIndexer('exported')
        catalog[u'exported'] = CatalogFieldIndex(exported_indexer)
        title_indexer = NodeAttributeIndexer('title')
        catalog[u'title'] = CatalogFieldIndex(title_indexer)
        return catalog


@implementer(ICatalogFactory)
class OrdersCatalogFactory(object):

    def __call__(self, context=None):
        catalog = Catalog()
        uid_indexer = NodeAttributeIndexer('uid')
        catalog[u'uid'] = CatalogFieldIndex(uid_indexer)
        booking_uids_indexer = NodeAttributeIndexer('booking_uids')
        catalog[u'booking_uids'] = CatalogKeywordIndex(booking_uids_indexer)
        creator_indexer = NodeAttributeIndexer('creator')
        catalog[u'creator'] = CatalogFieldIndex(creator_indexer)
        created_indexer = NodeAttributeIndexer('created')
        catalog[u'created'] = CatalogFieldIndex(created_indexer)
        state_indexer = NodeAttributeIndexer('state')
        catalog[u'state'] = CatalogFieldIndex(state_indexer)
        name_indexer = NodeAttributeIndexer('personal_data.name')
        catalog[u'personal_data.name'] = CatalogFieldIndex(name_indexer)
        surname_indexer = NodeAttributeIndexer('personal_data.surname')
        catalog[u'personal_data.surname'] = CatalogFieldIndex(surname_indexer)
        city_indexer = NodeAttributeIndexer('billing_address.city')
        catalog[u'billing_address.city'] = CatalogFieldIndex(city_indexer)
        search_attributes = ['personal_data.name',
                             'personal_data.surname',
                             'billing_address.city']
        text_indexer = NodeTextIndexer(search_attributes)
        catalog[u'text'] = CatalogTextIndex(text_indexer)
        return catalog


class OrderCheckoutAdapter(CheckoutAdapter):
    
    @instance_property
    def order(self):
        return OOBTNode()
    
    @property
    def vessel(self):
        return self.order.attrs
    
    def save(self, providers, widget, data):
        super(OrderCheckoutAdapter, self).save(providers, widget, data)
        creator = None
        member = self.context.portal_membership.getAuthenticatedMember()
        if member:
            creator = member.getId()
        created = datetime.datetime.now()
        order = self.order
        order.attrs['uid'] = uuid.uuid4()
        order.attrs['creator'] = creator
        order.attrs['created'] = created
        order.attrs['state'] = 'new'
        bookings = self.create_bookings(order)
        order.attrs['booking_uids'] = [_.attrs['uid'] for _ in bookings]
        orders_soup = get_soup('bda_plone_orders_orders', self.context)
        orders_soup.add(order)
        bookings_soup = get_soup('bda_plone_orders_bookings', self.context)
        for booking in bookings:
            bookings_soup.add(booking)
        deletecookie(self.request)
    
    def create_bookings(self, order):
        ret = list()
        items = extractitems(readcookie(self.request))
        for uid, count, comment in items:
            brain = get_catalog_brain(self.context, uid)
            item_data = ICartItemDataProvider(brain.getObject())
            booking = OOBTNode()
            booking.attrs['uid'] = uuid.uuid4()
            booking.attrs['buyable_uid'] = uid
            booking.attrs['buyable_count'] = count
            booking.attrs['buyable_comment'] = comment
            booking.attrs['order_uid'] = order.attrs['uid']
            booking.attrs['creator'] = order.attrs['creator']
            booking.attrs['created'] = order.attrs['created']
            booking.attrs['exported'] = False
            booking.attrs[u'title'] = brain and brain.Title or 'unknown'
            booking.attrs[u'net'] = item_data.net
            booking.attrs[u'vat'] = item_data.vat
            ret.append(booking)
        return ret