// Ghana locations for artisan registration, search and service-area selection.
// Entries are grouped by region for easier maintenance; LOCATIONS remains a flat
// list so existing filters and profile components continue to work.
export const REGION_LOCATIONS = {
  "Ahafo": ["Goaso", "Bechem", "Duayaw Nkwanta", "Kenyasi", "Hwidiem", "Mim", "Kukuom", "Asunafo", "Sankore"],
  "Ashanti": ["Kumasi", "Obuasi", "Ejisu", "Mampong", "Konongo", "Bekwai", "Offinso", "Ejura", "Juaben", "Agogo", "Tepa", "Mankranso", "Nkawie", "Kwadaso", "Suame", "Tafo", "Asokwa", "Oforikrom", "Asokore Mampong", "M Ejisu", "Atonsu", "Abuakwa", "Bantama", "Adum", "Asafo", "Ahodwo", "Santasi", "Ayigya", "KNUST", "Dichemso"],
  "Bono": ["Sunyani", "Berekum", "Dormaa Ahenkro", "Wenchi", "Jaman South", "Sampa", "Drobo", "Nsoatre", "Odumase", "Chiraa", "Fiapre"],
  "Bono East": ["Techiman", "Kintampo", "Atebubu", "Nkoranza", "Yeji", "Prang", "Tuobodom", "Jema", "Amantin"],
  "Central": ["Cape Coast", "Kasoa", "Winneba", "Mankessim", "Agona Swedru", "Saltpond", "Elmina", "Apam", "Dunkwa-on-Offin", "Assin Fosu", "Ajumako", "Awutu Breku", "Gomoa Fetteh", "Buduburam", "Moree", "Abura Dunkwa", "Komenda", "Nyanyano"],
  "Eastern": ["Koforidua", "Nsawam", "Suhum", "Nkawkaw", "Akosombo", "Mpraeso", "Aburi", "Akim Oda", "Akim Swedru", "Akwatia", "Somanya", "Odumase Krobo", "Asamankese", "Kibi", "Begoro", "Donkorkrom", "Maame Krobo", "Oda", "Tafo", "Abetifi", "Bunso"],
  "Greater Accra": [
    "Accra", "Accra Central", "Osu", "Labone", "Cantonments", "Airport Residential", "Roman Ridge", "Dzorwulu", "North Ridge", "West Ridge", "East Legon", "East Legon Hills", "Adjiringanor", "American House", "Shiashie", "Okponglo", "Madina", "La Nkwantanang", "Adenta", "Frafraha", "Ashiyie", "Ogbojo", "Dome", "Westlands", "Haatso", "Atomic", "Kwabenya", "Ashongman", "Pokuase", "Amasaman", "Ofankor", "Achimota", "Abeka", "Tesano", "Alajo", "Abossey Okai", "Kaneshie", "Dansoman", "Sakaman", "Odorkor", "Darkuman", "Awoshie", "Anyaa", "Ablekuma", "Mallam", "Gbawe", "Weija", "McCarthy Hill", "Bortianor", "Teshie", "Nungua", "Sakana", "La", "Labadi", "Spintex", "Baatsona", "Sakumono", "Community 1", "Community 2", "Community 3", "Community 4", "Community 5", "Community 6", "Community 7", "Community 8", "Community 9", "Community 10", "Tema", "Tema New Town", "Ashaiman", "Kpone", "Prampram", "Ningo", "Dawhenya", "Afienya", "Dodowa", "Shai Hills", "Ada Foah", "Sege", "Kasseh", "Oyibi", "Pantang", "Oyarifa", "Ayi Mensah", "Taifa", "Ofankor Barrier", "Bubuashie", "Mamprobi", "Chorkor", "James Town", "Ussher Town", "Korle Gonno", "Gbegbeise", "North Kaneshie", "New Achimota", "Abelemkpe", "Legon", "University of Ghana", "Madina Zongo", "Nmai Dzorn", "Gbetsile", "Michel Camp", "Klagon", "Lashibi", "Jelukope", "Kokomlemle", "Nima", "Maamobi", "New Town", "Pig Farm", "Kanda", "Adabraka", "Asylum Down", "Tudu", "Jamestown", "Mamponse", "Lartebiokorshie"
  ],
  "North East": ["Nalerigu", "Gambaga", "Walewale", "Bunkpurugu", "Chereponi", "Yagaba", "Langbinsi"],
  "Northern": ["Tamale", "Yendi", "Savelugu", "Tolon", "Kumbungu", "Gushegu", "Bimbilla", "Wulensi", "Karaga", "Zabzugu", "Tatale", "Kpandai", "Saboba", "Mion"],
  "Oti": ["Dambai", "Kete Krachi", "Jasikan", "Nkwanta", "Kadjebi", "Worawora", "Kpassa", "Chinderi", "Brewaniase"],
  "Savannah": ["Damongo", "Bole", "Salaga", "Sawla", "Buipe", "Daboya", "Tuna", "Larabanga"],
  "Upper East": ["Bolgatanga", "Bawku", "Navrongo", "Zebilla", "Sandema", "Paga", "Bongo", "Zuarungu", "Fumbisi", "Garu", "Tempane", "Widana"],
  "Upper West": ["Wa", "Tumu", "Lawra", "Jirapa", "Nandom", "Kaleo", "Lambussie", "Funsi", "Gwollu", "Hamile", "Wechiau"],
  "Volta": ["Ho", "Hohoe", "Keta", "Aflao", "Anloga", "Sogakope", "Kpando", "Kpeve", "Akatsi", "Dzodze", "Denu", "Adidome", "Abor", "Peki", "Kpetoe", "Aveyime", "Tsiame", "Agbozume", "Klikor", "Weta"],
  "Western": ["Sekondi", "Takoradi", "Sekondi-Takoradi", "Tarkwa", "Axim", "Half Assini", "Prestea", "Bogoso", "Shama", "Agona Nkwanta", "Dixcove", "Essiama", "Elubo", "Mpohor", "Manso Amenfi", "Apowa", "Kwesimintsim", "Anaji", "Fijai", "Effia"],
  "Western North": ["Sefwi Wiawso", "Bibiani", "Enchi", "Juaboso", "Bodi", "Sefwi Bekwai", "Akontombra", "Dadieso", "Asawinso"]
};

// Sort locations alphabetically within each region
Object.values(REGION_LOCATIONS).forEach((locations) => {
  locations.sort((a, b) => a.localeCompare(b));
});

// Sort regions and all locations alphabetically
export const REGIONS = Object.keys(REGION_LOCATIONS).sort((a, b) => a.localeCompare(b));

export const LOCATIONS = [...new Set(Object.values(REGION_LOCATIONS).flat())]
  .sort((a, b) => a.localeCompare(b));

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
