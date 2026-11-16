// Areas shown in dropdowns. Artisans can add others when they set their service areas.
export const LOCATIONS = [
  "Madina", "Adenta", "Dome", "East Legon", "Haatso", "Achimota", "Kasoa",
  "Accra Central", "Tema", "Spintex", "Kwabenya", "Teshie",
];

export const CONTACT = {
  email: import.meta.env.VITE_CONTACT_EMAIL || "",
  phone: import.meta.env.VITE_CONTACT_PHONE || "",
  whatsapp: import.meta.env.VITE_CONTACT_WHATSAPP || "",
};

export const SOCIALS = [
  { name: "Facebook", url: import.meta.env.VITE_FACEBOOK_URL || "" },
  { name: "Instagram", url: import.meta.env.VITE_INSTAGRAM_URL || "" },
  { name: "X", url: import.meta.env.VITE_X_URL || "" },
].filter((s) => s.url);

export const CONTACT_TOPICS = [
  "General question", "I need a worker", "I am an artisan", "Report a problem", "Partnership or advertising",
];
