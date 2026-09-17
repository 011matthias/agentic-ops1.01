# Prototype Fund Runde 03: Projektskizze

**Bewerbungsfenster 01.10.2026 bis 30.11.2026. Bis zu 47.500 EUR für sechs
Monate, Einzelperson.** Onlineformular, Jury entscheidet, kein Mensch muss
angesprochen werden. Stand dieser Skizze: 2026-09-16.

Voraussetzungen, alle erfüllt: volljährig (19), Hauptwohnsitz Deutschland
(Karlsruhe), selbständig und hier steuerpflichtig (Einzelunternehmen),
Softwareprojekt, Veröffentlichung unter einer Open-Source-Lizenz.

---

## Der Projektname

**`veritas`** oder **`recon-eval`**, Arbeitstitel. Ein Werkzeug, mit dem sich
die Genauigkeit eines KI-Systems so messen lässt, dass eine fremde Person das
Ergebnis nachrechnen kann.

## Das Problem, in einem Absatz

Immer mehr Entscheidungen laufen durch KI-Systeme, und praktisch jeder
Anbieter behauptet eine Trefferquote. Diese Zahlen sind fast nie überprüfbar:
Sie stehen auf einer Produktseite, niemand nennt die Datengrundlage, niemand
kann nachrechnen, und die Zahl wurde in aller Regel auf denselben Daten
ermittelt, auf denen das System optimiert wurde. Wer als Kommune, Redaktion,
Verein oder kleines Unternehmen ein KI-System einkauft, hat kein Werkzeug, um
eine solche Behauptung zu prüfen. Genau dieses Werkzeug fehlt als freie
Infrastruktur.

## Was gebaut wird

Eine installierbare Bibliothek plus Kommandozeilenwerkzeug, das eine
Genauigkeitsaussage erzeugt, die **eine dritte Person unabhängig
nachvollziehen kann**. Vier Eigenschaften, die zusammen den Unterschied
machen:

1. **Der gesperrte Messwert.** Die Bewertungsfunktion wird über ihren Hash
   festgeschrieben. Der Trainings- und der Holdout-Teil der Daten stehen
   *innerhalb* dieser festgeschriebenen Datei, damit der optimierende Prozess
   die Trennlinie nicht verschieben kann.
2. **Wächter, die keine Zahlen verraten.** Die Schutzprüfungen geben nur
   bestanden oder nicht bestanden aus, nie die Holdout-Werte selbst. Sonst
   ließe sich der Holdout über viele Durchläufe indirekt mitoptimieren. Die
   Wächter sind ebenfalls gehasht, damit sie zwischen zwei Läufen nicht
   abgeschwächt werden können.
3. **Der Zirkelschluss-Test.** Wenn die Beispieldaten von Menschen mit Hilfe
   einer Heuristik bewertet wurden, misst man am Ende womöglich nur, wie gut
   das System diese Heuristik nachspricht. Das Werkzeug zerlegt das Ergebnis
   nach Beweisgüte und zeigt, ob der Gewinn nur in der schwachen Klasse liegt.
4. **Das Intervall statt der Zahl.** Bei 60 Beispielen ist "97 Prozent" keine
   Aussage. Ausgegeben wird eine Spanne (Wilson beziehungsweise
   Clopper-Pearson, Dreierregel bei null Fehlern) und dazu, wie viele
   Beispiele für eine gewünschte Genauigkeit der Aussage nötig wären.

Dazu ein öffentlicher, synthetischer Beispieldatensatz, damit jede Person das
Werkzeug ohne eigene Daten ausprobieren kann, und eine Dokumentation, die
erklärt, wie eine belastbare Messung aufgebaut wird.

## Warum das gemeinnützig ist, nicht nur nützlich

- **Einkaufsseite.** Öffentliche Stellen und kleine Organisationen kaufen KI
  ein und können Anbieterangaben heute nicht prüfen. Das Werkzeug gibt ihnen
  eine Prüffrage, die sie stellen können: Nennen Sie Ihre Datengrundlage und
  lassen Sie die Messung nachrechnen.
- **Recherche.** Redaktionen und zivilgesellschaftliche Organisationen, die
  KI-Systeme untersuchen, brauchen eine Methode, die vor Widerspruch besteht.
- **EU-KI-Verordnung.** Für einen Teil der Systeme werden belegte Aussagen
  über Leistungsfähigkeit verlangt. Freie Werkzeuge dafür gibt es kaum.
- **Gegen Selbstbetrug.** Der Fall, den dieses Werkzeug als erstes verhindert
  hat, war kein Anbieter, der lügt, sondern ein optimierender Prozess, der
  sich unbemerkt auf seinen eigenen Prüfdatensatz eingestellt hätte.

## Die sechs Monate

| Monat | Arbeitspaket |
|---|---|
| 1 | Kern herauslösen: Bewertungsfunktion, Hash-Sperre, Wächter, Lauf-Motor als eigenständiges Paket, frei von jedem Kundenbezug. Lizenz, CI, erste Veröffentlichung. |
| 2 | Intervallschätzung und Stichprobenrechnung. Ab hier gibt das Werkzeug keine nackten Zahlen mehr aus. |
| 3 | Synthetischer Beispieldatensatz mit Beweisgüte-Klassen, damit der Zirkelschluss-Test ohne echte Daten demonstrierbar ist. |
| 4 | Zweiter Anwendungsfall aus einer anderen Domäne, damit belegt ist, dass die Methode nicht an einem Problem klebt. |
| 5 | Dokumentation und Anleitung: wie eine belastbare Messung entsteht, und die häufigen Fehler. |
| 6 | Härtung, Fehlerberichte einarbeiten, Version 1.0, Abschlussbericht. |

## Warum ich

Das ist kein Vorschlag, sondern die Verallgemeinerung von etwas, das bereits
läuft. Ich habe diese Maschinerie für die Abstimmung eines
Belegabgleich-Systems gebaut, das die Finanzunterlagen eines Unternehmens
verarbeitet, und sie gegen von Menschen bestätigte Beispiele aus sechs echten
Monaten laufen lassen. Der Aufbau, die Hash-Sperre, die Wächter und der
Zirkelschluss-Test existieren, sind in Betrieb und haben in mehreren
Durchläufen Verbesserungen verworfen, die nur nach Verbesserung aussahen.
Was fehlt, ist genau das, wofür die Förderung da ist: es aus einem
Kundenprojekt herauszulösen, die Statistik sauber zu machen und es so zu
veröffentlichen, dass andere es benutzen können.

---

## Was vor der Bewerbung noch stimmen muss

Ehrlich, weil eine Jury genau hier nachfragt:

1. **Die Genauigkeitszahl neu herleiten.** Die bisher intern genannte Zahl
   ("null Fehler im Holdout") ist falsch: die Bewertungsfunktion kennt zwei
   Fehlerkanäle, und zusammengerechnet ergibt sich ein anderer Wert. Vor jeder
   öffentlichen Aussage neu rechnen. Keine Zahl in die Bewerbung schreiben,
   die nicht nachgerechnet ist.
2. **Kundenbezug vollständig entfernen.** Der Kern muss ohne jeden Hinweis auf
   Brisken veröffentlichbar sein. Das betrifft auch die Beispieldaten: die 95
   bestätigten Paare gehören dem Kunden und werden nie veröffentlicht. Der
   synthetische Datensatz ersetzt sie.
3. **Das öffentliche Repository: entschieden, bleibt öffentlich** (2026-09-16).
   Für die Bewerbung trotzdem auf das herausgelöste Paket verweisen, nicht auf
   das Gesamt-Repository, damit die Jury die Vorarbeit ohne Kundenprojekt sieht.
4. **Zweite Domäne benennen.** Monat 4 braucht ein konkretes zweites Beispiel.
   Kandidat aus dem Bestand: die Bewertung von Agenten-Ausgaben
   (`tools/eval-agents.py` mit `tools/fixtures/agnt-evals/`), die bereits ohne
   Sprachmodell-Aufrufe deterministisch bewertet.
5. **Abgrenzung recherchieren.** Die Jury wird fragen, warum das nicht schon
   existiert. Vorhandene Werkzeuge zur Modellbewertung anschauen und in einem
   Absatz sagen, was sie nicht tun: nämlich die Messung gegen den
   optimierenden Prozess selbst absichern.

## Formales

- Onlineformular ab 01.10.2026, Einsendeschluss 30.11.2026.
- Gefördert werden Einzelpersonen und kleine Teams; hier Einzelperson.
- Veröffentlichung unter einer Open-Source-Lizenz ist Bedingung. Vorschlag:
  Apache-2.0, weil sie eine Patentklausel enthält und für Organisationen
  unkompliziert ist.
- Nachzuhalten für das Formular: Hauptwohnsitz, Steuernummer,
  Gewerbeanmeldung. Diese Angaben gehören ins Formular, nicht in diese Datei,
  weil das Repository öffentlich ist.
