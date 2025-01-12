#!/usr/bin/env python3

import logging
from getpass import getpass
from argparse import ArgumentParser

import slixmpp
from slixmpp.exceptions import XMPPError
from slixmpp.xmlstream import ET, tostring

import os
from datetime import datetime 

class PubsubClient(slixmpp.ClientXMPP):

    def __init__(self, jid, password, server,
                       node=None, action='nodes', data=''):
        super().__init__(jid, password)

        self.register_plugin('xep_0030')
        self.register_plugin('xep_0059')
        self.register_plugin('xep_0060')

        self.actions = ['nodes', 'create', 'delete', 'get_configure',
                        'publish', 'get', 'retract',
                        'purge', 'subscribe', 'unsubscribe']
        self.actions.append('add_owner')
        self.actions.append('get_affiliation')

        self.action = action
        self.node = node
        self.data = data
        self.pubsub_server = server

        self.add_event_handler('session_start', self.start)

    async def start(self, event):
        await self.get_roster()
        self.send_presence()

        try:
            await getattr(self, self.action)()
        except:
            logging.exception('Could not execute %s:', self.action)
        self.disconnect()

    async def nodes(self):
        try:
            result = await self['xep_0060'].get_nodes(self.pubsub_server, self.node)
            for item in result['disco_items']['items']:
                logging.info('  - %s', str(item))
        except XMPPError as error:
            logging.error('Could not retrieve node list: %s', error.format())

    async def create(self):
        try:
            await self['xep_0060'].create_node(self.pubsub_server, self.node)
            logging.info('Created node %s', self.node)
        except XMPPError as error:
            logging.error('Could not create node %s: %s', self.node, error.format())

    async def delete(self):
        try:
            await self['xep_0060'].delete_node(self.pubsub_server, self.node)
            logging.info('Deleted node %s', self.node)
        except XMPPError as error:
            logging.error('Could not delete node %s: %s', self.node, error.format())

    async def get_configure(self):
        try:
            configuration_form = await self['xep_0060'].get_node_config(self.pubsub_server, self.node)
            logging.info('Configure form received from node %s: %s', self.node, configuration_form['pubsub_owner']['configure']['form'])
        except XMPPError as error:
            logging.error('Could not retrieve configure form from node %s: %s', self.node, error.format())

    async def publish(self):
        if self.data:
            payload = ET.fromstring(self.data)
        else:
            payload = ET.fromstring("<test xmlns='test'>hello world</test>")

        try:
            result = await self['xep_0060'].publish(self.pubsub_server, self.node, payload=payload)
            logging.info('Published at item id: %s', result['pubsub']['publish']['item']['id'])
        except XMPPError as error:
            logging.error('Could not publish to %s: %s', self.node, error.format())

    async def get(self):
        try:
            result = await self['xep_0060'].get_item(self.pubsub_server, self.node, self.data)
            for item in result['pubsub']['items']['substanzas']:
                logging.info('Retrieved item %s: %s', item['id'], tostring(item['payload']))
        except XMPPError as error:
            logging.error('Could not retrieve item %s from node %s: %s', self.data, self.node, error.format())

    async def retract(self):
        try:
            await self['xep_0060'].retract(self.pubsub_server, self.node, self.data)
            logging.info('Retracted item %s from node %s', self.data, self.node)
        except XMPPError as error:
            logging.error('Could not retract item %s from node %s: %s', self.data, self.node, error.format())

    async def purge(self):
        try:
            await self['xep_0060'].purge(self.pubsub_server, self.node)
            logging.info('Purged all items from node %s', self.node)
        except XMPPError as error:
            logging.error('Could not purge items from node %s: %s', self.node, error.format())

    async def subscribe(self):
        try:
            iq = await self['xep_0060'].subscribe(self.pubsub_server, self.node)
            subscription = iq['pubsub']['subscription']
            logging.info('Subscribed %s to node %s', subscription['jid'], subscription['node'])
        except XMPPError as error:
            logging.error('Could not subscribe %s to node %s: %s', self.boundjid.bare, self.node, error.format())

    async def unsubscribe(self):
        try:
            await self['xep_0060'].unsubscribe(self.pubsub_server, self.node)
            logging.info('Unsubscribed %s from node %s', self.boundjid.bare, self.node)
        except XMPPError as error:
            logging.error('Could not unsubscribe %s from node %s: %s', self.boundjid.bare, self.node, error.format())

    async def get_affiliation(self):
        try:
            iq = await self['xep_0060'].get_affiliations(self.pubsub_server, self.node)
            affiliation = iq['pubsub']['affiliations']['affiliation']
            logging.info(f"Affiliations for {self.boundjid.bare} {self.node} {affiliation}")
        except XMPPError as error:
            logging.error('Could not get affiliations', self.boundjid.bare, self.node, error.format())

    async def add_owner(self):
        affiliations = [(new_owner, "owner") for new_owner in self.data.split(",")]
        try:
            iq = await self['xep_0060'].modify_affiliations(self.pubsub_server, self.node, affiliations=affiliations)
            affiliation = iq
            logging.info(f"Affiliations for {self.boundjid.bare} {self.node} {affiliation}")
        except XMPPError as error:
            logging.error('Could not get affiliations', self.boundjid.bare, self.node, error.format())


if __name__ == '__main__':
    choices = ["nodes", "create", "delete", "get_configure", "purge", "subscribe", "unsubscribe", "publish", "retract", "get"]
    choices.append("add_owner")
    choices.append("get_affiliation")

    # Setup the command line arguments.
    parser = ArgumentParser()
    parser.version = '%%prog 0.1'
    parser.usage = "Usage: %%prog [options] <jid> " + \
                             '|'.join(choices) + \
                             ' [<node> <data>]'

    parser.add_argument("-q","--quiet", help="set logging to ERROR",
                        action="store_const",
                        dest="loglevel",
                        const=logging.ERROR,
                        default=logging.INFO)
    parser.add_argument("-d","--debug", help="set logging to DEBUG",
                        action="store_const",
                        dest="loglevel",
                        const=logging.DEBUG,
                        default=logging.INFO)

    # JID and password options.
    parser.add_argument("-j", "--jid", dest="jid",
                        help="JID to use")
    parser.add_argument("-p", "--password", dest="password",
                        help="password to use")

    parser.add_argument("server")
    parser.add_argument("action", choices=choices)
    parser.add_argument("node", nargs='?')
    parser.add_argument("data", nargs='?')

    args = parser.parse_args()

    # Setup logging.
    logging.basicConfig(level=args.loglevel,
                        # format='%(levelname)-8s %(message)s')
                        format='%(asctime)s [%(levelname)s %(filename)s +%(lineno)s] %(message)s')

    # Setup the Pubsub client
    xmpp = PubsubClient(args.jid, args.password,
                        server=args.server,
                        node=args.node,
                        action=args.action,
                        data=args.data)

    if True:
        # If you want to verify the SSL certificates offered by a server:
        CERT_DIR = 'certs/'
        xmpp.ca_certs = CERT_DIR + "/server_ca.pem"
        xmpp.certfile = CERT_DIR + "/client.pem"
        xmpp.keyfile  = CERT_DIR + "/client.key"

        if os.path.isdir(CERT_DIR):
            if not os.path.isfile(xmpp.ca_certs):
                logging.critical('CA Certificate not found at %s' % xmpp.ca_certs)
                exit()
            if not os.path.isfile(xmpp.certfile):
                logging.error('Client Certificate not found at %s' % xmpp.certfile)
            if not os.path.isfile(xmpp.keyfile):
                logging.error('Client Key not found at %s' % xmpp.ca_certs)
        else:
            logging.critical('Certificate Directory not found at %s' % os.getcwd())
            exit()

    # Connect to the XMPP server and start processing XMPP stanzas.
    xmpp.connect()
    xmpp.process(forever=False)
