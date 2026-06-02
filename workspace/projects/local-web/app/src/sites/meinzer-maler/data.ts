// Content for meinzer-maler. Every field traces to
// workspace/projects/local-web/prospects/meinzer-maler/data.md.
// Unverified fields use the CHECK sentinel and render as [BITTE PRÜFEN].

export const CHECK = "[BITTE PRÜFEN]";

export const meinzer = {
  name: "Michael Meinzer Malerfachbetrieb",
  shortName: "Meinzer Malerfachbetrieb",
  owner: "Michael Meinzer",
  role: "Malermeister",
  tagline:
    "Malerfachbetrieb in Karlsruhe-Knielingen: Wände, Fassaden und Sanierung, sauber und zum Festpreis vom Meister.",
  address: {
    street: "Saarlandstr. 84",
    zip: "76187",
    city: "Karlsruhe",
    district: "Knielingen",
  },
  phone: "0721 9702290",
  phoneHref: "tel:+4972197 02290",
  fax: "0721 9702292",
  email: CHECK,

  // Services sourced verbatim from the brief (see data.md).
  services: [
    {
      title: "Malerarbeiten",
      body: "Innenanstriche für Wohnräume, Treppenhäuser und Gewerbe, sauber abgeklebt und gleichmäßig deckend.",
    },
    {
      title: "Tapezierarbeiten",
      body: "Tapeten, Vlies und Raufaser fachgerecht angebracht, vom Untergrund bis zur fertigen Wand.",
    },
    {
      title: "Fassadenarbeiten",
      body: "Außenanstriche und Fassadengestaltung, die das Haus wieder frisch und wetterfest machen.",
    },
    {
      title: "Betonsanierung / Betonschutz",
      body: "Schadhaften Beton instand setzen und dauerhaft vor Witterung und Feuchtigkeit schützen.",
    },
    {
      title: "Schimmelpilzsanierung",
      body: "Schimmel fachgerecht entfernen und die Ursache angehen, damit er nicht wiederkommt.",
    },
    {
      title: "Renovierung",
      body: "Räume rundum auffrischen: ein Ansprechpartner vom ersten Termin bis zur besenreinen Übergabe.",
    },
  ],

  // The Festpreis-Werkbank process strip (signature section). The promise
  // is described qualitatively; no price figure is invented (B4).
  process: [
    {
      title: "Anfrage",
      body: "Sie melden sich kurz per Telefon, wir besprechen, worum es geht.",
    },
    {
      title: "Vor-Ort-Termin",
      body: "Wir schauen uns die Flächen vor Ort an und nehmen Maß.",
    },
    {
      title: "Festpreis-Angebot",
      body: "Sie bekommen ein klares Angebot zum Festpreis, ohne Überraschungen.",
    },
    {
      title: "Saubere Ausführung",
      body: "Wir arbeiten termingerecht und übergeben besenrein.",
    },
  ],

  hours: [
    { day: "Montag", times: ["07:00 – 17:00"] },
    { day: "Dienstag", times: ["07:00 – 17:00"] },
    { day: "Mittwoch", times: ["07:00 – 17:00"] },
    { day: "Donnerstag", times: ["07:00 – 17:00"] },
    { day: "Freitag", times: ["07:00 – 17:00"] },
    { day: "Samstag", times: ["07:00 – 12:00"] },
    { day: "Sonntag", times: [] },
  ],

  // Unverified, must render as [BITTE PRÜFEN], never invented.
  yearsInTrade: CHECK,
  team: CHECK,
  certifications: CHECK,

  updated: "2026-06-02",
} as const;

export type Meinzer = typeof meinzer;
