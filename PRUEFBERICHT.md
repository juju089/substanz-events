# Prüfbericht · 5. November 2026

## Ergebnis

Das Paket wurde für `juju089/substanz-events` erstellt. Ein echter HTTPS-Abruf der offiziellen Seite `https://substanz-club.com/alle-events` war erfolgreich. Der Parser hat **29 Veranstaltungen** vom 4. November 2026 bis zum 19. April 2027 eingelesen. Die ursprüngliche HTML-Antwort liegt als reproduzierbarer Test-Schnappschuss bei. Der erste echte Datenstand ist in `site/data/events.json` und `site/events.ics` enthalten; der genaue Abrufzeitpunkt steht in den Dateien.

Die ältere URL `/events` enthält ein anderes, teils überholtes Programm und wird bewusst nicht verwendet. Es werden keine Termine aus Wochentagsregeln ergänzt. Die Seite enthält auch Newsletter-Bereiche; der Parser identifiziert Veranstaltungskarten anhand der aktuellen HTML-Struktur und des Kalender-Symbols.

## Durchgeführte Prüfungen

- **10 Python-Tests erfolgreich:** 29 Originalkarten, Datumsgrenzen und Titel, kyrillische Zeichen, Ticketlink, Beginn versus Einlass, Zeiten ohne „Uhr“, Datum trotz Schreibfehler „Motag“, stabile Termin-IDs bei Uhrzeitänderung, ungültige Karte und Uhrzeit, leere und veraltete Quelle, ungewöhnlich großer Datenverlust, ICS-Zeilenfaltung und Zeichensatz, UTC mit Winter- und Sommerzeit, Netz-Wiederholungsversuche, erster Abruffehler ohne Bestand, spätere Abruf-/Parserfehler mit vorhandenem Bestand, Erholung nach einem Fehler und zwingender Abbruch bei einem simulierten Schreibfehler.
- **7 Node-Tests erfolgreich:** Such-, Kategorie- und Zeitfilter, deutsches Datum in Berlin unabhängig von der Gerätezeitzone, Einzel-ICS mit Zeitzonenregeln, Escaping und maximal 75 UTF-8-Bytes pro Kalenderzeile, Manifest-/Dateipfade, Service-Worker-Installation und Offline-Fallback im Testmodell, Umgehung des Kalenders durch den Service Worker sowie App-Integration für Laden, Rendern, Suche, Kategorien, Zurücksetzen, Offline-Lesen, gesperrten Browser-Speicher und Abrufwarnungen.
- **JavaScript-Syntax geprüft:** `app.js`, `calendar.js`, `sw.js`.
- **Unabhängiger ICS-Parser:** `icalendar` 7.3.0 konnte den Gesamtfeed mit 29 VEVENTs und 29 eindeutigen UIDs ohne gemeldete VEVENT-Fehler lesen. Stichprobe: Karaoke am 05.11.2026 um 21:00 Uhr Berlin entspricht 20:00 UTC. Die Einzel-ICS wurde ebenfalls mit dem unabhängigen Parser kontrolliert.
- **Unabhängiger YAML-Parser:** PyYAML 6.0.3 konnte die Workflow-Datei lesen; Zeitplan, Job-Abhängigkeit, Pages-Berechtigungen, Bot-Schreibrecht und Veröffentlichungsordner wurden kontrolliert. Action-Versionen und Pages-Konzept wurden mit offizieller GitHub-Dokumentation abgeglichen.
- **ZIP-Prüfung:** Archiv nach Erstellung geöffnet, CRC-Prüfung ausgeführt, erforderliche Dateien einschließlich `.github/workflows/update-and-deploy.yml` geprüft; Tests nach erneutem Entpacken ausgeführt. Keine Zugangsdaten, temporären Dateien oder installierten Prüf-Bibliotheken sind im Paket.

## Nachgewiesener Schutz der bisherigen Daten

Die Tests erzeugen zuerst einen gültigen Datenbestand, merken sich die Bytes von JSON und ICS und simulieren danach Timeout, fehlerhaftes HTML sowie eine beschädigte Originalkarte. **JSON und ICS bleiben bei jedem dieser Fehler Byte für Byte unverändert.** Nur der getrennte Abrufstatus meldet den Fehler. Ein anschließender erfolgreicher Abruf setzt die Warnung zurück. Fehler beim Schreiben auf Datenträger werden nicht als erfolgreicher Ersatzbetrieb behandelt; der Workflow bricht dann vor Commit und Veröffentlichung ab.

## Grenzen der Prüfung

**Es wurde nichts in das GitHub-Repository hochgeladen und kein echter GitHub-Actions-/Pages-Lauf ausgeführt.** Diese Prüfung erfolgt nach deinem Upload mit den Repository-Einstellungen. Die Anleitung enthält die nötigen Schritte und häufige Fehlermeldungen.

Eine visuelle Browserprüfung konnte hier nicht abgeschlossen werden: Die Vorschau-Verbindung zum lokalen Testserver lief in ein Zeitlimit. Der anschließende Versuch mit dem lokalen Browser wurde vom Computer-Use-Werkzeug beendet, weil es die aktuelle Browseradresse nicht zuverlässig feststellen konnte. Es wird daher kein erfolgreicher Screenshot-, Layout-, echter Browser-Offline- oder Geräte-Installationstest behauptet. Die Tests für App und Service Worker verwenden Testmodelle; sie ersetzen keinen Test auf einem echten iPhone oder Android-Gerät. Das CSS enthält responsive Layouts für schmale Displays, diese wurden hier nicht visuell bestätigt.

Die offizielle Veranstaltungsseite kann sich ändern oder fehlerhafte Inhalte enthalten. Die Plausibilitätsprüfung erkennt nicht jede denkbare unvollständige Antwort. Bei größeren Änderungen kann Wartung am Parser nötig werden. Kalender-Apps wählen selbst ihr Aktualisierungsintervall. GitHub-Zeitpläne können sich verzögern. Der Erfolg einer tatsächlichen Apple-/Google-/Outlook-Abonnierung wurde nicht auf einem Benutzerkonto getestet.

## Prüfungen wiederholen

Im Projektordner (Python 3.12+, Node 24):

```text
python -m unittest discover -s tests -v
node --test tests/*.test.cjs
node --check site/app.js
node --check site/calendar.js
node --check site/sw.js
python scripts/update_events.py
```

Die Python-/Node-Tests benötigen keine zusätzlichen Pakete. Die unabhängigen Prüf-Bibliotheken wurden nur zur Paketkontrolle verwendet und sind keine Laufzeitvoraussetzung. Für lokale Python-Läufe unter Windows können separat installierte `tzdata`-Daten nötig sein; auf GitHub Ubuntu sind sie vorhanden.
