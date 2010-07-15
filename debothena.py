#!/usr/bin/python
import re
import urllib
from lxml import etree
import time
import sys
from random import choice
import os

try:
    import zephyr
except ImportError:
    import site
    site.addsitedir('/mit/broder/lib/python%s/site-packages' % sys.version[:3])
    import zephyr


last_seen = {}
seen_timeout = 5 * 60
parser = etree.HTMLParser(encoding='UTF-8')

def build_matcher(regex, flags=0):
    r = re.compile(regex, flags)
    def match(zgram):
        return r.findall(zgram.fields[-1])
    return match

matchers = (
    ('Debathena', [build_matcher(r'\btrac[-\s:]*#([0-9]{1,5})\b', re.I)]),

    ('Debathena', [build_matcher(r'#([0-9]{1,5})\b')])
    )

def fetch_debathena(ticket):
    u = 'http://debathena.mit.edu/trac/ticket/%s' % ticket
    f = urllib.urlopen(u)
    t = etree.parse(f, parser)
    title = t.xpath('string(//h2[@class])')
    if title:
        return u, title
    else:
        return u, None

fetchers = {
    'Debathena': fetch_debathena,
    }

def find_ticket_info(zgram):
    for tracker, ms in matchers:
        for m in ms:
            ticket = m(zgram)
            for t in ticket:
                yield tracker, t

def undebathena_fun():
    u = 'http://debathena.mit.edu/trac/wiki/PackageNamesWeDidntUse'
    f = urllib.urlopen(u)
    t = etree.parse(f, parser)
    package = choice(t.xpath('id("content")//li')).text.strip()
    dir = choice(['/etc', '/bin', '/usr/bin', '/sbin', '/usr/sbin',
                  '/dev/mapper', '/etc/default', '/var/run'])
    file = choice(os.listdir(dir))
    return u, "%s should divert %s/%s" % (package, dir, file)

def main():
    zephyr.init()
    subs = zephyr.Subscriptions()
    subs.add(('broder-test', '*', '*'))
    subs.add(('debathena', '*', '*'))
    subs.add(('undebathena', '*', '*'))

    while True:
        zgram = zephyr.receive(True)
        if not zgram:
            continue
        if zgram.opcode.lower() == 'kill':
            sys.exit(0)
        messages = []
        for tracker, ticket in find_ticket_info(zgram):
            fetcher = fetchers.get(tracker)
            if fetcher:
                if (zgram.opcode.lower() != 'auto' and
                    last_seen.get((tracker, ticket), 0) < time.time() - seen_timeout):
                    if zgram.cls == 'undebathena':
                        u, t = undebathena_fun()
                    else:
                        u, t = fetcher(ticket)
                    if not t:
                        t = 'Unable to identify ticket %s' % ticket
                    messages.append('%s ticket %s: %s' % (tracker, ticket, t))
                last_seen[(tracker, ticket)] = time.time()
        if messages:
            z = zephyr.ZNotice()
            z.cls = zgram.cls
            z.instance = zgram.instance
            z.recipient = zgram.recipient
            z.opcode = 'auto'
            z.sender = 'debothena'
            z.fields = [u, '\n'.join(messages)]
            z.send()


if __name__ == '__main__':
    main()
