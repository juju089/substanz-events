import json
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from datetime import datetime, timezone, date
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_events as u

FIXTURE = (Path(__file__).parent / 'fixtures' / 'alle-events.html').read_text(encoding='utf-8')
NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)

class ParserTests(unittest.TestCase):
    def setUp(self):
        self.events = u.parse_events(FIXTURE)
    def test_real_snapshot(self):
        self.assertEqual(len(self.events), 29)
        self.assertEqual(self.events[0]['date'], '2026-11-04')
        self.assertEqual(self.events[-1]['title'], 'KATLIX')
        self.assertEqual(self.events[-1]['date'], '2027-04-19')
        karaoke = next(e for e in self.events if e['date'] == '2026-11-05')
        self.assertEqual((karaoke['start'], karaoke['doors']), ('21:00', '18:30'))
        self.assertTrue(karaoke['ticket'].startswith('https://'))
        stella = next(e for e in self.events if e['title'] == 'STELLA STEGMANN')
        self.assertEqual(stella['start'], '19:30')
        self.assertEqual(stella['date'], '2026-11-30')  # Source typo "Motag" must not break the date.
        self.assertTrue(any('Артур' in e['title'] for e in self.events))
    def test_only_doors_is_not_invented_start(self):
        seaside = next(e for e in self.events if e['title'] == 'SEASIDE')
        self.assertIsNone(seaside['start'])
        self.assertEqual(seaside['doors'], '18:30')
        self.assertIn(r'Einlass\; Beginn offen', u.make_ics([seaside], NOW.isoformat()).decode())
    def test_uid_survives_time_change(self):
        changed = u.parse_events(FIXTURE.replace('Beginn 21:00', 'Beginn 22:00'))
        self.assertEqual([e['id'] for e in self.events], [e['id'] for e in changed])
    def test_missing_date_and_invalid_time_fail(self):
        for html in [FIXTURE.replace('04.11.2026', 'Datum folgt'), FIXTURE.replace('Beginn 21:00', 'Beginn 29:00'), '<html>Maintenance</html>']:
            with self.assertRaises(ValueError): u.parse_events(html)
    def test_calendar_encoding_folding_and_utc(self):
        raw = u.make_ics(self.events, NOW.isoformat())
        lines = raw.split(b'\r\n')
        self.assertTrue(all(len(line) <= 75 for line in lines))
        self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))
        unfolded = raw.decode().replace('\r\n ', '')
        self.assertEqual(unfolded.count('BEGIN:VEVENT'), 29)
        self.assertEqual(unfolded.count('END:VEVENT'), 29)
        self.assertIn('DTSTART:20261105T200000Z', unfolded)  # Winter: 21:00 Berlin = 20:00 UTC.
        summer = dict(self.events[1], date='2027-07-01', start='21:00')
        self.assertIn(b'DTSTART:20270701T190000Z', u.make_ics([summer], NOW.isoformat()))
        self.assertEqual(u.escape_ics('a,b;c\\d\ne'), 'a\\,b\\;c\\\\d\\ne')
    def test_mass_loss_and_stale_fail(self):
        with self.assertRaises(ValueError): u.validate_change(self.events[:2], {'events':self.events}, date(2026,11,5))
        with self.assertRaises(ValueError): u.validate_change(self.events, {}, date(2028,1,1))

class PersistenceTests(unittest.TestCase):
    def setUp(self):
        for context in [redirect_stdout(StringIO()), redirect_stderr(StringIO())]:
            context.__enter__()
            self.addCleanup(context.__exit__, None, None, None)
    def test_fetch_and_parse_failures_preserve_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            self.assertTrue(u.update(site, lambda: FIXTURE, NOW))
            before = [(site/p).read_bytes() for p in ['data/events.json', 'events.ics']]
            for loader in [lambda: (_ for _ in ()).throw(TimeoutError('timeout')), lambda: '<html>Error</html>', lambda: FIXTURE.replace('04.11.2026', 'unknown')]:
                self.assertFalse(u.update(site, loader, NOW, allow_stale=True))
                self.assertEqual(before, [(site/p).read_bytes() for p in ['data/events.json', 'events.ics']])
                self.assertFalse(json.loads((site/'data/status.json').read_text())['ok'])
            self.assertTrue(u.update(site, lambda: FIXTURE, NOW, allow_stale=True))
            self.assertTrue(json.loads((site/'data/status.json').read_text())['ok'])
    def test_first_failure_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): u.update(Path(tmp), lambda: 'bad', NOW, allow_stale=True)
            self.assertFalse((Path(tmp)/'events.ics').exists())
    def test_network_retries(self):
        with patch.object(u, 'urlopen', side_effect=TimeoutError), patch.object(u.time, 'sleep'):
            with self.assertRaises(RuntimeError): u.fetch_html()
            self.assertEqual(u.urlopen.call_count, 3)
    def test_disk_error_is_fatal_even_with_stale_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            u.update(site, lambda: FIXTURE, NOW)
            with patch.object(u.os, 'replace', side_effect=OSError('disk failure')):
                with self.assertRaises(OSError): u.update(site, lambda: FIXTURE, NOW, allow_stale=True)

if __name__ == '__main__': unittest.main()
