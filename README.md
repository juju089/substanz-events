# Substanz München · Veranstaltungen

Mobile, installierbare Web-App mit Suche, Kategorien, Datumsfiltern, Offline-Leseansicht und abonnierbarem Kalender. Für das öffentliche Repository **juju089/substanz-events**, Branch **main**.

**Am PC beginnen: [ANLEITUNG-PC.html](ANLEITUNG-PC.html) nach dem Entpacken doppelt anklicken.** Alternativ gibt es die Anleitung als [Markdown](ANLEITUNG-PC.md).

## Adressen nach erfolgreicher Einrichtung

- App: https://juju089.github.io/substanz-events/
- Kalender-Abo: https://juju089.github.io/substanz-events/events.ics
- Apple-Abo: webcal://juju089.github.io/substanz-events/events.ics

Diese Adressen werden erst nach dem Upload, Aktivieren von Pages und einem erfolgreichen Workflow-Lauf erreichbar. Es wurde im Rahmen der ZIP-Erstellung nichts in dein Repository hochgeladen.

## Enthalten

- `site/`: fertige statische PWA, Icons, Manifest und Service Worker, kein Frontend-Build nötig.
- `site/data/events.json`: echter erster Datenbestand aus der offiziellen Seite, kein Demo-Inhalt.
- `site/data/status.json`: Zeitpunkt und Ergebnis des letzten Abrufversuchs.
- `site/events.ics`: vollständiger Kalender; einzelne Termine können zusätzlich in der App gespeichert werden.
- `scripts/update_events.py`: Python-Parser und ICS-Erzeugung, nur Standardbibliothek.
- `.github/workflows/update-and-deploy.yml`: Tests, täglicher Abruf, Datensicherung und Pages-Veröffentlichung in **einem** Workflow.
- `tests/`: gespeicherte Originalseite und wiederholbare Tests ohne Netzwerk.
- `PRUEFBERICHT.md`: tatsächlich durchgeführte Prüfungen und verbleibende Grenzen.

## Datenquelle und Fehlerverhalten

Verwendet wird ausschließlich https://substanz-club.com/alle-events, nicht die ältere Seite `/events` und keine ausgedachten wiederkehrenden Termine. Der HTML-Parser liest aktuelle Elementor-Veranstaltungskarten: numerisches Datum mit Jahr, Titel, Beschreibung, Einlass, Beginn und vorhandene Ticket-/Reservierungslinks. Kategorien werden anhand des Textes zugeordnet und sind eine Orientierung.

Die Website bietet nicht für jede Veranstaltung eine Beginnzeit. Dann verwenden App und Kalender ausdrücklich **Einlass**, der Kalendertitel enthält „Einlass; Beginn offen“. Es werden keine Endzeiten erfunden. UTC-Zeiten im Gesamtfeed berücksichtigen `Europe/Berlin` einschließlich Sommerzeit. Die Einzeldateien enthalten eine Berlin-Zeitzonendefinition. Termin-IDs hängen von Datum und Titel ab und bleiben bei Zeitänderungen gleich; Titel- oder Datumsänderungen ergeben eine neue ID.

Bei Netzfehlern gibt es drei Versuche mit Zeitlimit. Leere Antworten, fehlende Pflichtfelder, ungültige Daten/Zeiten, eine veraltete Liste ohne zukünftige Termine und ein Rückgang um mehr als 50 % der zukünftigen Termine (ab sechs bisherigen zukünftigen Terminen) werden abgewiesen. JSON und ICS werden bei solchen Fehlern nicht überschrieben. `status.json` meldet den Fehler; die App zeigt die Warnung. Mit `--allow-stale` veröffentlicht der Workflow weiterhin den letzten erfolgreichen Datenbestand. Ohne vorhandene Daten schlägt er fehl. Ein Abruffehler mit erhaltenen Daten ist also eine **Warnung**, auch wenn der Lauf grün endet; siehe Laufzusammenfassung.

Dieser Schutz erkennt nicht jede mögliche inhaltliche Änderung einer fremden Website. Eine größere echte Programmverkleinerung kann manuelles Prüfen und Anpassen erfordern. Bei geänderter Seitenstruktur muss der Parser gewartet werden. Veranstalterangaben und Änderungen immer auf der Quelle prüfen. Entfernte Termine verschwinden beim nächsten akzeptierten Abruf aus dem Feed; wie schnell ein Abo das übernimmt, entscheidet die Kalender-App.

## Automatik

Der Workflow läuft bei Uploads auf `main`, manuell und täglich um **05:17 UTC**, also 06:17 Uhr im deutschen Winter / 07:17 Uhr im Sommer. GitHub kann geplante Läufe verzögern und deaktiviert geplante Workflows in öffentlichen Repositories nach 60 Tagen ohne Repository-Aktivität. Der Workflow sichert bei jedem Lauf auch den neuen Abrufstatus als Commit, was normalerweise Aktivität erzeugt; kontrolliere die Actions-Ansicht trotzdem gelegentlich. Quelle: [GitHub: schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Der Workflow committet Daten mit dem eingebauten GitHub-Token und lädt danach `site/` als Pages-Artefakt hoch. Er verlässt sich nicht auf einen zweiten Workflow durch diesen Bot-Commit (solche Pushes lösen gewöhnlich keine weiteren Workflows aus). Benötigt werden keine eigenen Tokens oder Secrets. Das Repository muss Bot-Commits auf `main` erlauben; Branchschutz kann sie verhindern.

## Lokal prüfen oder weiterentwickeln

Voraussetzung: Python 3.12+ mit Zeitzonendaten und Node.js 24. GitHub Ubuntu bringt die Zeitzonendaten mit. Unter Windows gegebenenfalls einmal `py -m pip install tzdata` ausführen; das ist nur für lokale Python-Läufe nötig, nicht für den Upload.

Im Projektordner:

```text
python -m unittest discover -s tests -v
node --test tests/*.test.cjs
node --check site/app.js
node --check site/sw.js
python scripts/update_events.py
python -m http.server 8000 --directory site
```

Danach http://localhost:8000 öffnen. Bei Windows kann `py` statt `python` nötig sein. `index.html` nicht per Doppelklick testen: lokale Datei-URLs unterstützen Datenabruf und PWA nicht vollständig. Die Upload-Anleitung ist davon unabhängig direkt per Doppelklick lesbar.

Optionaler Offline-Parser-Test: `python scripts/update_events.py --html tests/fixtures/alle-events.html --site test-site`. Der Aktualitätsschutz weist den historischen Schnappschuss nach Ablauf der enthaltenen Termine bewusst zurück. Die Tests nutzen dagegen ein festes Datum und funktionieren auch später.

## Datenschutz und Gestaltung

Keine Analysewerkzeuge, Cookies für Tracking, Fremdschriften oder externen JavaScript-Bibliotheken. Die App speichert öffentlich geladene Termine im Browser (Local Storage / Cache Storage). Beim Besuch kommuniziert der Browser mit GitHub Pages; erst beim Öffnen eines Quellen- oder Ticketlinks mit der jeweiligen externen Seite. Browserdaten lassen sich über die Website-Datenverwaltung löschen. Das S-Icon ist eine eigenständige typografische Gestaltung, kein übernommenes Veranstalterlogo. Veranstaltungsinhalte und Test-HTML stammen vom Veranstalter; dessen Rechte bleiben unberührt. Die Übersicht ist unabhängig und keine offizielle Substanz-App. Wer die App öffentlich betreibt, muss eigene erforderliche Betreiberinformationen ergänzen; der Link zum Veranstalter bezeichnet dessen Impressum.

## Offizielle technische Quellen

- [GitHub Pages mit eigenem Workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Dateien und Ordner hochladen](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)
- [Geplante Workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

Ausführliche Einrichtung und Fehlerhilfe: **ANLEITUNG-PC.html**.
