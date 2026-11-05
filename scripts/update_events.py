"""Official Substanz HTML -> validated JSON and RFC 5545 calendar. Python 3.12+."""
from __future__ import annotations
import argparse
from datetime import datetime, date, timedelta, timezone
from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

SOURCE = 'https://substanz-club.com/alle-events'
BERLIN = ZoneInfo('Europe/Berlin')
DATE = re.compile(r'\b(\d{1,2})\.(\d{1,2})\.(20\d{2})\b')
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []
    def all(self, tag=None):
        for c in self.children:
            if isinstance(c, Node):
                if tag is None or c.tag == tag:
                    yield c
                yield from c.all(tag)
    def text(self):
        return re.sub(r'\s+', ' ', ' '.join(c.text() if isinstance(c, Node) else c for c in self.children)).strip()

class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.current = Node()
    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.current)
        self.current.children.append(n)
        if tag not in VOID:
            self.current = n
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)
    def handle_endtag(self, tag):
        n = self.current
        while n.parent is not None:
            if n.tag == tag:
                self.current = n.parent
                return
            n = n.parent
    def handle_data(self, data):
        self.current.children.append(data)

def category(title, description):
    s = (title + ' ' + description).lower()
    for pattern, label in [(r'quiz', 'Quiz'), (r'bingo', 'Bingo'), (r'karaoke', 'Karaoke'),
                           (r'comedy|stand.up', 'Comedy'), (r'konzert|showcase', 'Konzert'),
                           (r'film', 'Film'), (r'lesung|liest|talk', 'Lesung'), (r'\bdj\b|party|vinyl', 'Party')]:
        if re.search(pattern, s):
            return label
    return 'Sonstiges'

def clock(text, label):
    m = re.search(label + r'\s*(\d{1,2}):(\d{2})', text, re.I)
    if not m:
        return None
    h, minute = map(int, m.groups())
    if h > 23 or minute > 59:
        raise ValueError('Ungültige Uhrzeit')
    return f'{h:02}:{minute:02}'

def safe_url(value):
    value = urljoin(SOURCE, value)
    return value if urlparse(value).scheme == 'https' else None

def parse_events(html):
    tree = Tree()
    tree.feed(html)
    events = {}
    # Each current Elementor inner section is one complete event card.
    cards = [n for n in tree.root.all('section') if 'elementor-inner-section' in n.attrs.get('class', '').split()
             and any('fa-calendar' in i.attrs.get('class', '') for i in n.all('i'))]
    if not cards:
        raise ValueError('Keine Veranstaltungskarten: Seitenstruktur möglicherweise geändert')
    for card in cards:
        headings = list(card.all('h2'))
        spans = [n.text() for n in card.all('span') if 'elementor-icon-list-text' in n.attrs.get('class', '').split()]
        dates = [DATE.search(s) for s in spans if DATE.search(s)]
        if len(headings) != 1 or len(dates) != 1:
            raise ValueError('Unvollständige oder mehrdeutige Karte; bisherige Daten bleiben erhalten')
        day, month, year = map(int, dates[0].groups())
        day_string = date(year, month, day).isoformat()
        title = headings[0].text()
        description = ' '.join(n.text() for n in card.all('p'))
        info = ' '.join(spans)
        start, doors = clock(info, r'(?:Beginn|Start)'), clock(info, r'(?:Einlass|Doors|Ab)')
        if not title or (not start and not doors):
            raise ValueError('Titel oder Zeit fehlt; Abbruch statt unvollständiger Daten')
        links = [safe_url(n.attrs['href']) for n in card.all('a') if n.attrs.get('href') and re.search(r'ticket|reserv|anmelden', n.text(), re.I)]
        uid = hashlib.sha256((day_string + '|' + title.casefold()).encode()).hexdigest()[:24] + '@substanz-events'
        event = dict(id=uid, date=day_string, title=title, description=description,
                     start=start, doors=doors, category=category(title, description),
                     ticket=next((x for x in links if x), None), source=SOURCE)
        if uid in events and events[uid] != event:
            raise ValueError('Widersprüchliche doppelte Veranstaltung')
        events[uid] = event
    return sorted(events.values(), key=lambda e: (e['date'], e['start'] or e['doors'], e['title']))

def escape_ics(s):
    return s.replace('\\', '\\\\').replace('\r', '').replace('\n', r'\n').replace(';', r'\;').replace(',', r'\,')

def fold_line(line):
    chunks, current = [], ''
    for char in line:
        if len((current + char).encode('utf-8')) > 75:
            chunks.append(current)
            current = ' '
        current += char
    return '\r\n'.join(chunks + [current])

def make_ics(events, timestamp):
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//substanz-events//DE', 'CALSCALE:GREGORIAN',
             'METHOD:PUBLISH', 'X-WR-CALNAME:Substanz München', 'X-WR-TIMEZONE:Europe/Berlin']
    stamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    for e in events:
        local = datetime.fromisoformat(e['date'] + 'T' + (e['start'] or e['doors'])).replace(tzinfo=BERLIN)
        summary = e['title'] if e['start'] else e['title'] + ' (Einlass; Beginn offen)'
        desc = e['description'] + '\n' + ('Beginn: ' + e['start'] if e['start'] else 'Beginn nicht angegeben. Kalenderzeit = Einlass.')
        if e['doors']:
            desc += '\nEinlass: ' + e['doors']
        desc += '\nOffizielle Quelle: ' + SOURCE
        if e['ticket']:
            desc += '\nTickets / Reservierung: ' + e['ticket']
        # No DTEND: the source does not publish reliable end times.
        lines += ['BEGIN:VEVENT', 'UID:' + e['id'], 'DTSTAMP:' + stamp,
                  'DTSTART:' + local.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
                  'SUMMARY:' + escape_ics(summary), 'DESCRIPTION:' + escape_ics(desc),
                  'LOCATION:' + escape_ics('Substanz, Ruppertstraße 28, 80337 München'),
                  'URL:' + SOURCE, 'END:VEVENT']
    return ('\r\n'.join(fold_line(line) for line in lines + ['END:VCALENDAR']) + '\r\n').encode('utf-8')

def fetch_html():
    last = None
    for attempt in range(3):
        try:
            req = Request(SOURCE, headers={'User-Agent': 'substanz-events/1.0 (+https://github.com/juju089/substanz-events)'})
            with urlopen(req, timeout=30) as response:
                if urlparse(response.url).hostname not in {'substanz-club.com', 'www.substanz-club.com'}:
                    raise ValueError('Unerwartete Weiterleitung')
                if 'text/html' not in response.headers.get('Content-Type', ''):
                    raise ValueError('Antwort ist kein HTML')
                raw = response.read(4_000_001)
                if len(raw) > 4_000_000:
                    raise ValueError('Antwort zu groß')
                return raw.decode('utf-8')
        except Exception as error:
            last = error
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError('Offizielle Seite nach drei Versuchen nicht abrufbar') from last

def validate_change(events, old, today):
    future = [e for e in events if e['date'] >= today.isoformat()]
    if not future:
        raise ValueError('Keine zukünftigen Termine; leere oder veraltete Quelle')
    old_future = [e for e in old.get('events', []) if e['date'] >= today.isoformat()]
    if len(old_future) >= 6 and len(future) < len(old_future) * 0.5:
        raise ValueError('Mehr als 50 Prozent der zukünftigen Termine fehlen; manuell prüfen')

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def update(site, loader=fetch_html, now=None, allow_stale=False):
    now = now or datetime.now(timezone.utc)
    timestamp = now.isoformat(timespec='seconds').replace('+00:00', 'Z')
    data = site / 'data'
    data.mkdir(parents=True, exist_ok=True)
    target, calendar = data / 'events.json', site / 'events.ics'
    old = json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
    try:
        events = parse_events(loader())
        validate_change(events, old, now.astimezone(BERLIN).date())
        # Build both outputs fully before touching the last successful files.
        payload = dict(source=SOURCE, updatedAt=timestamp, events=events)
        ics = make_ics(events, timestamp)
    except Exception as error:
        write_json(data / 'status.json', dict(ok=False, checkedAt=timestamp, message='Abruf fehlgeschlagen. Letzter erfolgreicher Datenstand bleibt erhalten.'))
        print(f'::warning::{type(error).__name__}: {error}', file=sys.stderr)
        if not (allow_stale and old.get('events') and calendar.exists()):
            raise
        print('WARNUNG: Veröffentlichung mit bisherigem Datenstand.', file=sys.stderr)
        return False
    # Disk errors must be fatal: the workflow must not commit or deploy a partial write.
    write_json(data / 'events.json.tmp', payload)
    (site / 'events.ics.tmp').write_bytes(ics)
    os.replace(site / 'events.ics.tmp', calendar)
    os.replace(data / 'events.json.tmp', target)
    write_json(data / 'status.json', dict(ok=True, checkedAt=timestamp, message='Abruf erfolgreich'))
    print(f'{len(events)} echte Veranstaltungen gespeichert')
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=Path, default=Path('site'))
    parser.add_argument('--allow-stale', action='store_true')
    parser.add_argument('--html', type=Path, help='Gespeicherte Originalseite statt Live-Abruf')
    args = parser.parse_args()
    try:
        update(args.site, loader=(lambda: args.html.read_text(encoding='utf-8')) if args.html else fetch_html, allow_stale=args.allow_stale)
    except Exception as error:
        print(f'Abbruch: {error}', file=sys.stderr)
        sys.exit(1)
