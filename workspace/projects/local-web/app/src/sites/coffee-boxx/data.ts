// Content for coffee-boxx. Every field traces to
// workspace/projects/local-web/prospects/coffee-boxx/data.md.
// Unverified fields use the CHECK sentinel and render as [BITTE PRÜFEN].
// No menu item or price is invented (current real menu is a PDF) — the
// categories below ARE sourced (data.md "Offerings"); items + prices are
// explicitly left for the café to fill (BRIEF B4 rule).

export const CHECK = "[BITTE PRÜFEN]";

export const coffee = {
  name: "Coffee Boxx",
  team: "Marco und Team",
  tagline:
    "Kaffeespezialitäten, frische Panini und hausgemachter Kuchen, mitten in Karlsruhe.",
  address: {
    street: "Moltkestr. 44",
    zip: "76133",
    city: "Karlsruhe",
    // A second location at Kaiserstr. 93 is referenced; which is the
    // primary site is unverified.
    note: "Zweiter Standort Kaiserstr. 93 " + CHECK,
  },
  phone: "+49 721 49085949",
  phoneHref: "tel:+4972149085949",
  email: CHECK,
  socials: CHECK,
  websiteOld: "coffee-boxx.de",

  // Sourced opening hours (data.md / directory listings).
  hours: [
    { day: "Montag", times: "07:30 – 19:00" },
    { day: "Dienstag", times: "07:30 – 19:00" },
    { day: "Mittwoch", times: "07:30 – 19:00" },
    { day: "Donnerstag", times: "07:30 – 19:00" },
    { day: "Freitag", times: "07:30 – 19:00" },
    { day: "Samstag", times: "10:00 – 18:00" },
    { day: "Sonntag", times: "10:00 – 18:00" },
  ],

  // Categories ARE sourced ("Offerings"). Individual items + prices are
  // NOT — they live in the café's current PDF and must not be invented.
  menu: [
    {
      category: "Kaffeespezialitäten",
      note: "Espresso, Cappuccino, Latte und Saisonales.",
    },
    {
      category: "Panini",
      note: "Frisch belegt und warm gepresst.",
    },
    {
      category: "Kuchen",
      note: "Hausgemachte Auswahl, täglich wechselnd.",
    },
  ],

  // Imagery slots (Figure name -> caption); photos via fetch-imagery.mjs.
  gallery: [
    { name: "gallery-1", label: "Espressomaschine, Café-Interieur", ratio: "4 / 5" },
    { name: "gallery-2", label: "Panini, frisch gepresst", ratio: "4 / 5" },
    { name: "gallery-3", label: "Kuchenstück auf dem Teller", ratio: "1 / 1" },
  ],
} as const;

export type Coffee = typeof coffee;
