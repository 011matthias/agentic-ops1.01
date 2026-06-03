// Content for beauty-lounge. Every field traces to
// workspace/projects/local-web/prospects/beauty-lounge/data.md.
// data_confidence: medium (verified via directories; the live site is down
// with an expired SSL cert, so it could not be read directly).
// Unverified fields use the CHECK sentinel and render as [BITTE PRÜFEN].
// This salon offers KOSMETIK + NAGELDESIGN + WELLNESS only. NO Friseur/hair.

export const CHECK = "[BITTE PRÜFEN]";

export const beautyLounge = {
  name: "Beauty Lounge",
  fullName: "Beauty Lounge Karlsruhe",
  owner: "Ilona Fait",
  tagline:
    "Kosmetik, Nageldesign und Wellness in der Karlsruher Innenstadt: ein ruhiger Ort, an dem man sich Zeit für Sie nimmt.",
  address: {
    street: "Amalienstraße 39",
    zip: "76133",
    city: "Karlsruhe",
    district: "Innenstadt-West",
  },
  phone: "0721 2495054",
  phoneHref: "tel:+497212495054",
  email: CHECK,

  // Three service families derived from the verified verbatim service list.
  // No hair / Friseur anywhere (B4 correction). Treatment names are sourced
  // verbatim; prices are NOT verified and stay [BITTE PRÜFEN].
  families: [
    {
      key: "gesicht",
      label: "Gesicht & Kosmetik",
      lede: "Klassische und apparative Kosmetik, abgestimmt auf Ihre Haut.",
      treatments: [
        "Gesichtsbehandlungen (klassische und apparative Kosmetik)",
        "Fruchtsäurebehandlung",
        "Mikrodermabrasion",
        "Micro-Needling",
        "Sauerstoffbehandlung",
        "Make-up",
        "Augenbrauenkorrektur (Wax)",
        "BDR-Enthaarung",
      ],
    },
    {
      key: "nageldesign",
      label: "Nageldesign",
      lede: "Hände und Füße, gepflegt und präzise modelliert.",
      treatments: [
        "Nagelmodellage",
        "Fußnägelmodellage",
        "Maniküre",
        "Pediküre / Fußpflege",
      ],
    },
    {
      key: "wellness",
      label: "Wellness & Massage",
      lede: "Ein Moment Ruhe, der den Tag entschleunigt.",
      treatments: ["Hot-Stone-Massage"],
    },
  ],

  // Flat Preisliste: every treatment, price unverified -> [BITTE PRÜFEN].
  // Grouped by family so the table stays scannable.
  priceList: [
    { family: "Gesicht & Kosmetik", treatment: "Gesichtsbehandlung (klassisch)", price: CHECK },
    { family: "Gesicht & Kosmetik", treatment: "Apparative Kosmetik", price: CHECK },
    { family: "Gesicht & Kosmetik", treatment: "Fruchtsäurebehandlung", price: CHECK },
    { family: "Gesicht & Kosmetik", treatment: "Mikrodermabrasion", price: CHECK },
    { family: "Gesicht & Kosmetik", treatment: "Micro-Needling", price: CHECK },
    { family: "Gesicht & Kosmetik", treatment: "Sauerstoffbehandlung", price: CHECK },
    { family: "Gesicht & Kosmetik", treatment: "Make-up", price: CHECK },
    { family: "Gesicht & Kosmetik", treatment: "Augenbrauenkorrektur (Wax)", price: CHECK },
    { family: "Gesicht & Kosmetik", treatment: "BDR-Enthaarung", price: CHECK },
    { family: "Nageldesign", treatment: "Nagelmodellage", price: CHECK },
    { family: "Nageldesign", treatment: "Fußnägelmodellage", price: CHECK },
    { family: "Nageldesign", treatment: "Maniküre", price: CHECK },
    { family: "Nageldesign", treatment: "Pediküre / Fußpflege", price: CHECK },
    { family: "Wellness & Massage", treatment: "Hot-Stone-Massage", price: CHECK },
  ],

  hours: [
    { day: "Montag", times: "09:00 bis 18:30" },
    { day: "Dienstag", times: "09:00 bis 18:30" },
    { day: "Mittwoch", times: "09:00 bis 18:30" },
    { day: "Donnerstag", times: "09:00 bis 18:30" },
    { day: "Freitag", times: "09:00 bis 18:30" },
    { day: "Samstag", times: "09:00 bis 14:00" },
    { day: "Sonntag", times: "geschlossen" },
  ],
  hoursNote: "Zusätzliche Termine nach telefonischer Vereinbarung.",

  websiteOld: CHECK,
} as const;

export type BeautyLounge = typeof beautyLounge;
