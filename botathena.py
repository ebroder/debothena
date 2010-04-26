#!/usr/bin/python
import re
import urllib
from lxml import etree
import time

try:
    import zephyr
except ImportError:
    import site, sys
    site.addsitedir('/mit/broder/lib/python%s/site-packages' % sys.version[:3])
    import zephyr


last_seen = {}
parser = etree.HTMLParser()

def build_matcher(regex, flags=0):
    r = re.compile(regex, flags)
    def match(zgram):
        m = r.search(zgram.instance)
        if m:
            return m.group(1)
        m = r.search(zgram.fields[-1])
        if m:
            return m.group(1)
    return match

matchers = (
    ('Debathena', [build_matcher(r'\btrac[- ]#([0-9]+)\b', re.I)]),

    ('Debathena', [build_matcher(r'#([0-9]+)\b')])
    )

def fetch_debathena(ticket):
    f = urllib.urlopen('http://debathena.mit.edu/trac/ticket/%s' % ticket)
    t = etree.parse(f, parser)
    title = t.xpath('//h2[@class]/text()')
    if title:
        return title[0]

fetchers = {
    'Debathena': fetch_debathena,
    }

def find_ticket_info(zgram):
    for tracker, ms in matchers:
        for m in ms:
            ticket = m(zgram)
            if ticket:
                return tracker, ticket
    return None, None

def main():
    zephyr.init()
    subs = zephyr.Subscriptions()
    subs.add(('broder-test', '*', '*'))

    while True:
        zgram = zephyr.receive(True)
        if not zgram:
            continue
        if zgram.opcode.lower() == 'auto':
            continue
        tracker, ticket = find_ticket_info(zgram)
        if tracker:
            fetcher = fetchers.get(tracker)
            if fetcher:
                if last_seen.get((tracker, ticket), 0) < time.time() - 30:
                    t = fetcher(ticket)
                    if not t:
                        t = 'Unable to identify ticket %s' % ticket
                    zgram.opcode = 'auto'
                    zgram.fields = ['botathena',
                                    '%s ticket %s: %s' % (tracker, ticket, t)]
                    zgram.sender = 'botathena'
                    zgram.send()
                last_seen[(tracker, ticket)] = time.time()


if __name__ == '__main__':
    main()
