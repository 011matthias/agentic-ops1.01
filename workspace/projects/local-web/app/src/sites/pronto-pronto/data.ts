// Content for pronto-pronto. Every field traces to
// workspace/projects/local-web/prospects/pronto-pronto/data.md.
// Sourced facts (19 zones, hours, payment, 10% / MBW 0,00, socials) are
// used verbatim. Individual dish prices + email are unverified -> CHECK.
// The menu lists the SOURCED cuisine categories only; no dish or price is
// invented (BRIEF B4 rule).

export const CHECK = "[BITTE PRÜFEN]";

export const pronto = {
  name: "Pronto-Pronto",
  fullName: "Pronto-Pronto Heimservice und Restaurant",
  tagline:
    "Pizza, Pasta und mehr aus Karlsruhe, frisch geliefert oder im Restaurant. 10% Rabatt bei Online-Bestellung, Mindestbestellwert 0,00 Euro.",
  address: {
    street: "Moltkestr. 79a",
    zip: "76133",
    city: "Karlsruhe",
  },
  phone: "0721 859762",
  phoneHref: "tel:+49721859762",
  email: CHECK,

  promo: { discount: "10% Rabatt bei Online-Bestellung", minOrder: "Mindestbestellwert 0,00 Euro" },

  // Sourced opening hours (data.md).
  hours: [
    { day: "Montag bis Donnerstag", times: "10:45 – 22:30" },
    { day: "Freitag und Samstag", times: "10:45 – 23:59" },
    { day: "Sonntag", times: "10:45 – 22:30" },
    { day: "Feiertage", times: "11:00 – 22:30" },
  ],

  payment: [
    "PayPal",
    "Lastschrift",
    "Kreditkarte",
    "EC",
    "Überweisung",
    "Bar",
  ],

  socials: [
    { label: "Facebook", handle: "/prontoprontokarlsruhe", href: "https://www.facebook.com/prontoprontokarlsruhe" },
    { label: "Instagram", handle: "@prontoprontokarlsruhe", href: "https://www.instagram.com/prontoprontokarlsruhe/" },
  ],

  // data.md states 19 zones; 15 are named, the rest are "u.a." (not
  // enumerated) — the unnamed ones are NOT invented.
  zonesTotal: 19,
  zonesNamed: [
    "Stutensee",
    "Waldstadt",
    "Südstadt",
    "Oststadt",
    "Weststadt",
    "Daxlanden",
    "Knielingen",
    "Durlach",
    "Mühlburg",
    "Nordstadt",
    "Rüppurr",
    "Eggenstein",
    "Rheinstetten",
    "Ettlingen",
    "Wörth am Rhein",
  ],

  // Cuisine categories ARE sourced ("Cuisine"). Individual dishes + prices
  // are NOT on the current homepage and must not be invented.
  menu: [
    { category: "Pizza", note: "Klassisch und Spezialitäten." },
    { category: "Pasta", note: "Italienische Nudelgerichte." },
    { category: "Burger", note: "Frisch zubereitet." },
    { category: "Calzone", note: "Gefüllt und gebacken." },
    { category: "Flammkuchen", note: "Dünn und knusprig." },
    { category: "Salate", note: "Frische Auswahl." },
    { category: "Meeresfrüchte", note: "Mediterran." },
    { category: "Gyros", note: "Mit Beilagen." },
    { category: "Mexikanische Tacos", note: "Würzig." },
    { category: "Desserts", note: "Zum Abschluss." },
  ],
} as const;

export type Pronto = typeof pronto;
