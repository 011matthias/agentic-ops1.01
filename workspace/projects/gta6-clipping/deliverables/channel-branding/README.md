# cl1pmaxxers: Kanal-Design (GTA 6)

Eigenes Artwork im Vice-City-Abendlook: Neon-Sonne, Palmen, Skyline, Meer.
Bewusst ohne GTA- oder Rockstar-Logo, ohne deren Schrift, Figuren oder
Screenshots: Das sind geschützte Marken, und beide Plattformen behandeln so
etwas als Markenverletzung oder als Vortäuschen eines offiziellen Kanals.
Den Spielnamen „GTA 6“ als Text zu nennen ist in Ordnung.

## Dateien

| Datei | Wofür | Maße |
|---|---|---|
| `profile-800.png` | Profilbild YouTube und TikTok, mit Schriftzug „CL1P“ | 800 × 800 |
| `profile-800-ohne-text.png` | dasselbe ohne Schriftzug, falls dir das lieber ist | 800 × 800 |
| `youtube-banner-2048x1152.png` | YouTube-Banner; Name und Untertitel liegen im Bereich, den jedes Gerät zeigt (1235 × 338) | 2048 × 1152 |
| `youtube-wasserzeichen-150.png` | YouTube-Wasserzeichen unten rechts in jedem Video, Hintergrund durchsichtig | 150 × 150 |

Beide Plattformen schneiden das Profilbild rund zu; alles Wichtige liegt im Kreis.

## Hochladen

**YouTube** (am PC, studio.youtube.com, mit dem Kanal-Konto):

1. Links „Anpassung“ („Customization“) → Reiter „Branding“.
2. „Bild“ → Hochladen → `profile-800.png`.
3. „Bannerbild“ → Hochladen → `youtube-banner-2048x1152.png`, Vorschau prüfen, „Fertig“.
4. „Video-Wasserzeichen“ → Hochladen → `youtube-wasserzeichen-150.png`, Anzeigezeit „Gesamtes Video“.
5. Reiter „Allgemeine Informationen“ → Beschreibung (Text unten) einfügen → oben rechts „Veröffentlichen“.

**TikTok** (in der App): Profil → „Profil bearbeiten“ → „Foto ändern“ → `profile-800.png`; Bio (Text unten) einfügen.

## Texte

**YouTube-Kanalbeschreibung**

```text
GTA 6 stream highlights, cut short.

We follow what viewers clip and keep only those moments: the chaos, the fails and the clutch plays from the biggest GTA 6 streams.

Every clip credits the streamer in the title. Streamer and want a clip taken down? Email [KONTAKT-E-MAIL] and it comes down.

Not affiliated with or endorsed by Rockstar Games or Take-Two Interactive.
```

**TikTok-Bio** (höchstens 80 Zeichen)

```text
GTA 6 stream highlights. Only the moments viewers clipped most.
```

Offen, bevor die Texte live gehen:

- `[KONTAKT-E-MAIL]`: eine Adresse, über die Streamer eine Löschung verlangen können. Sie ist der Eingang für die Beschwerde-Wache aus p2 (Owner-Entscheidung 2026-11-17: clippen ohne vorher zu fragen, bei Beschwerde raus).
- „Every clip credits the streamer in the title“ ist eine Zusage: Die Titel aus p1.3/p1.4 müssen den Streamer nennen.

## Neu rendern

Quelle: `src/scene.js` (Szene als SVG) und `src/render.html`. Mit Chrome, ein Bild pro Aufruf:

```text
chrome --headless=new --hide-scrollbars --default-background-color=00000000 --virtual-time-budget=15000
       --window-size=2048,1152 --screenshot=youtube-banner-2048x1152.png "file:///.../src/render.html?asset=banner"
```

`asset` = `banner` | `profile` | `profile-plain` | `watermark` (Fenstergröße passend setzen);
`&guides=1` zeichnet die Zuschnitt-Hilfslinien ein. Schriften: Anton, Bebas Neue, Mr Dafoe (Google Fonts, frei nutzbar).
