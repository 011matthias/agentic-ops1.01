// Content for praxis-uslu. Every field traces to
// workspace/projects/local-web/prospects/praxis-uslu/data.md.
// Unverified fields use the CHECK sentinel and render as [BITTE PRÜFEN].

export const CHECK = "[BITTE PRÜFEN]";

export const praxis = {
  name: "Praxis Dr. med. Sema Uslu",
  doctor: "Dr. med. Sema Uslu",
  role: "Fachärztin für Allgemeinmedizin",
  tagline:
    "Hausärztliche Versorgung in Mühlburg, die sich Zeit nimmt, schulmedizinisch und naturheilkundlich.",
  address: {
    street: "Peter-und-Paul-Platz 3",
    zip: "76185",
    city: "Karlsruhe",
    district: "Mühlburg",
  },
  phone: "+49 721 5966608",
  phoneHref: "tel:+497215966608",
  fax: "+49 721 9529808",
  email: CHECK,
  websiteOld: "praxis-uslu.de",

  specialisations: [
    "Allgemeinmedizin",
    "Notfallmedizin",
    "Naturheilverfahren",
    "Akupunktur",
  ],

  // Services sourced from medical directories (see data.md sources).
  services: [
    {
      title: "Hausärztliche Versorgung",
      body: "Kontinuierliche allgemeinmedizinische Betreuung für die ganze Familie, von der Akutsprechstunde bis zur Begleitung chronischer Erkrankungen.",
    },
    {
      title: "Naturheilverfahren & Akupunktur",
      body: "Naturheilkundliche Verfahren und Akupunktur ergänzend zur schulmedizinischen Behandlung, individuell abgestimmt.",
    },
    {
      title: "Hautkrebsscreening",
      body: "Strukturierte Früherkennungsuntersuchung der Haut zur rechtzeitigen Abklärung auffälliger Befunde.",
    },
    {
      title: "Sonographie / Ultraschall",
      body: "Ultraschalldiagnostik in der Praxis zur schnellen, strahlungsfreien Abklärung.",
    },
    {
      title: "Medizinische Rehabilitation",
      body: "Beratung und Begleitung im Rahmen medizinischer Rehabilitationsmaßnahmen.",
    },
    {
      title: "Psychosomatische Grundversorgung",
      body: "Ärztliche Gespräche und psychosomatische Grundversorgung als Teil der hausärztlichen Betreuung.",
    },
  ],

  hours: [
    { day: "Montag", times: ["08:00 – 12:00", "14:00 – 18:00"] },
    { day: "Dienstag", times: ["08:00 – 13:00"] },
    { day: "Mittwoch", times: ["07:00 – 13:00"] },
    { day: "Donnerstag", times: ["08:00 – 12:00", "14:00 – 18:00"] },
    { day: "Freitag", times: ["08:00 – 13:00"] },
    { day: "Samstag", times: [] },
    { day: "Sonntag", times: [] },
  ],

  // Unverified — must render as [BITTE PRÜFEN], never invented.
  team: CHECK,
  kassen: CHECK,
  languages: CHECK,

  emergency: {
    bereitschaft: "116 117",
    notruf: "112",
  },
} as const;

export type Praxis = typeof praxis;
