// Content for helmle-physio. Every field traces to
// workspace/projects/local-web/prospects/helmle-physio/data.md.
// Unverified fields use the CHECK sentinel and render as [BITTE PRÜFEN] (B4).

export const CHECK = "[BITTE PRÜFEN]";

export const helmle = {
  name: "Helmle & Helmle Physiotherapie",
  fullName: "Krankengymnastik- und Massagepraxis Helmle & Helmle",
  role: "Krankengymnastik- und Massagepraxis",
  tagline:
    "Krankengymnastik, Manuelle Therapie und Massagen in der Karlsruher Südweststadt: persönlich, mit Zeit für jeden Befund.",
  address: {
    street: "Karlstr. 86",
    zip: "76137",
    city: "Karlsruhe",
    district: "Südweststadt",
  },
  phone: "0721 3842525",
  phoneHref: "tel:+4972 13842525",
  mobile: "0152 53687646",
  email: "info@helmle-physio.de",
  bestReach: "Telefonisch am besten erreichbar von 08:30 bis 12:30 Uhr.",

  // Services verbatim from the practice (data.md). The treatment-journey
  // signature groups them, but every label here is sourced 1:1.
  services: [
    {
      title: "Krankengymnastik",
      body: "Aktive und passive Bewegungstherapie, abgestimmt auf den einzelnen Befund.",
    },
    {
      title: "Manuelle Therapie",
      body: "Gezielte Mobilisation von Gelenken und Wirbelsäule mit den Händen.",
    },
    {
      title: "Krankengymnastik nach Bobath",
      body: "Neurophysiologische Behandlung zur Wiederherstellung von Bewegung und Koordination.",
    },
    {
      title: "Krankengymnastik / PNF",
      body: "Propriozeptive neuromuskuläre Fazilitation: Bewegungsmuster gezielt anbahnen und kräftigen.",
    },
    {
      title: "Massagen",
      body: "Klassische Massagen zur Lösung von Verspannungen und zur Durchblutungsförderung.",
    },
    {
      title: "Lymphdrainagen",
      body: "Manuelle Lymphdrainage zur Entstauung bei Schwellungen und nach Operationen.",
    },
    {
      title: "Behandlungen bei Kiefergelenkstörungen",
      body: "Physiotherapie bei Beschwerden des Kiefergelenks (CMD), häufig mit Begleitsymptomen wie Kopfschmerz.",
    },
    {
      title: "Behandlungen im Schlingentisch",
      body: "Aufhängung der Gliedmaßen zur entlastenden, schmerzarmen Bewegung.",
    },
    {
      title: "Wärme-/Kältetherapie",
      body: "Wärme und Kälte gezielt eingesetzt zur Schmerzlinderung und Vorbereitung der Behandlung.",
    },
    {
      title: "Elektrotherapie / Ultraschall",
      body: "Reizstrom und Ultraschall zur Schmerzlinderung und Geweberegeneration.",
    },
    {
      title: "Naturfangopackungen",
      body: "Wärmepackungen aus Naturfango zur Lockerung der Muskulatur.",
    },
    {
      title: "Hausbesuche",
      body: "Behandlung bei Ihnen zu Hause, wenn der Weg in die Praxis nicht möglich ist.",
    },
  ],

  // Bespoke "Behandlungsreise": three calm stages along the spine.
  // Each stage references sourced service labels, no invented content.
  journey: [
    {
      phase: "Beschwerde",
      title: "Wir hören zu und befunden",
      body: "Erst zuhören und untersuchen: woher kommt der Schmerz, welche Bewegung fehlt. Das gilt für Rücken, Gelenke und auch das Kiefergelenk.",
    },
    {
      phase: "Behandlung",
      title: "Mit den Händen und gezielter Therapie",
      body: "Manuelle Therapie, Krankengymnastik, Massagen und Lymphdrainagen, ergänzt durch Schlingentisch, Wärme, Kälte oder Elektrotherapie, je nach Befund.",
    },
    {
      phase: "Erholung",
      title: "Beweglich bleiben",
      body: "Übungen für zu Hause, Naturfangopackungen und, wenn der Weg zu uns schwerfällt, Behandlung als Hausbesuch.",
    },
  ],

  hours: [
    { day: "Montag", times: ["07:00 – 19:00"] },
    { day: "Dienstag", times: ["07:00 – 14:00"] },
    { day: "Mittwoch", times: ["07:00 – 19:00"] },
    { day: "Donnerstag", times: ["08:30 – 15:30"] },
    { day: "Freitag", times: ["07:00 – 13:00"] },
    { day: "Samstag", times: [] },
    { day: "Sonntag", times: [] },
  ],

  // Unverified, must render as [BITTE PRÜFEN], never invented.
  kassen: CHECK,
  team: CHECK,
  prices: CHECK,
} as const;

export type Helmle = typeof helmle;