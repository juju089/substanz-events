/* Shared calendar behavior, also tested with Node's built-in test runner. */
(function (root) {
  'use strict';
  const escape = s => String(s).replace(/\\/g, '\\\\').replace(/\r/g, '').replace(/\n/g, '\\n').replace(/;/g, '\\;').replace(/,/g, '\\,');
  function fold(s) {
    let line = '', result = [];
    for (const c of s) {
      if (new TextEncoder().encode(line + c).length > 75) { result.push(line); line = ' '; }
      line += c;
    }
    return [...result, line].join('\r\n');
  }
  function single(e) {
    // A per-event download uses TZID + VTIMEZONE (including daylight saving).
    const zone = ['BEGIN:VTIMEZONE', 'TZID:Europe/Berlin', 'BEGIN:DAYLIGHT', 'DTSTART:19700329T020000', 'RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU', 'TZOFFSETFROM:+0100', 'TZOFFSETTO:+0200', 'END:DAYLIGHT', 'BEGIN:STANDARD', 'DTSTART:19701025T030000', 'RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU', 'TZOFFSETFROM:+0200', 'TZOFFSETTO:+0100', 'END:STANDARD', 'END:VTIMEZONE'];
    const time = (e.start || e.doors).replace(':', '') + '00';
    const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
    const description = `${e.description}\n${e.start ? 'Beginn: ' + e.start : 'Beginn offen. Kalenderzeit = Einlass.'}\nEinlass: ${e.doors || 'nicht angegeben'}\n${e.source}`;
    return ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//substanz-events//DE', ...zone, 'BEGIN:VEVENT', `UID:${e.id}`, `DTSTAMP:${stamp}`, `DTSTART;TZID=Europe/Berlin:${e.date.replace(/-/g, '')}T${time}`, `SUMMARY:${escape(e.title + (e.start ? '' : ' (Einlass; Beginn offen)'))}`, `DESCRIPTION:${escape(description)}`, `LOCATION:${escape('Substanz, Ruppertstraße 28, 80337 München')}`, `URL:${e.source}`, 'END:VEVENT', 'END:VCALENDAR'].map(fold).join('\r\n') + '\r\n';
  }
  function today(now = new Date()) { return new Intl.DateTimeFormat('sv-SE', {timeZone: 'Europe/Berlin', year:'numeric', month:'2-digit', day:'2-digit'}).format(now); }
  function filtered(events, query, type, range, current = today()) {
    const anchor = Date.parse(current + 'T00:00:00Z');
    return events.filter(e => {
      const days = (Date.parse(e.date + 'T00:00:00Z') - anchor) / 86400000;
      const inRange = range === 'past' ? days < 0 : range === 'today' ? days === 0 : range === 'week' ? days >= 0 && days < 7 : range === 'month' ? days >= 0 && days < 30 : days >= 0;
      return inRange && (type === 'Alle' || e.category === type) && (e.title + ' ' + e.description).toLocaleLowerCase('de').includes(query.trim().toLocaleLowerCase('de'));
    });
  }
  const api = {single, fold, escape, filtered, today};
  if (typeof module !== 'undefined') module.exports = api;
  else root.Substanz = api;
})(globalThis);
