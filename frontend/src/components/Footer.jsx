import { Link } from "react-router-dom";
import { CONTACT, SOCIALS } from "../constants";

export default function Footer() {
  const waLink = CONTACT.whatsapp ? `https://wa.me/${CONTACT.whatsapp.replace(/\D/g, "")}` : "";
  return (
    <footer className="bg-brand-900 text-brand-100">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 md:grid-cols-3">
        <div>
          <p className="font-display text-xl font-bold text-white">Find a Skilled Worker Ghana</p>
          <p className="mt-2 max-w-xs text-brand-200">Connecting people in Ghana with plumbers, electricians, carpenters and other skilled workers.</p>
        </div>
        <div>
          <p className="font-display font-bold text-white">Explore</p>
          <ul className="mt-3 space-y-2">
            <li><Link className="hover:underline" to="/artisans">Browse artisans</Link></li>
            <li><Link className="hover:underline" to="/register?role=artisan">Join as an artisan</Link></li>
            <li><Link className="hover:underline" to="/pricing">Pricing for artisans</Link></li>
            <li><Link className="hover:underline" to="/about">About us</Link></li>
            <li><Link className="hover:underline" to="/contact">Contact</Link></li>
          </ul>
        </div>
        <div>
          <p className="font-display font-bold text-white">Get in touch</p>
          <ul className="mt-3 space-y-2">
            {CONTACT.email && <li><a className="hover:underline" href={`mailto:${CONTACT.email}`}>{CONTACT.email}</a></li>}
            {CONTACT.phone && <li><a className="hover:underline" href={`tel:${CONTACT.phone.replace(/\s/g, "")}`}>{CONTACT.phone}</a></li>}
            {waLink && <li><a className="hover:underline" href={waLink} target="_blank" rel="noreferrer">Chat on WhatsApp</a></li>}
            {!CONTACT.email && !CONTACT.phone && !waLink && <li><Link className="hover:underline" to="/contact">Send us a message</Link></li>}
            {SOCIALS.map((s) => (
              <li key={s.name}><a className="hover:underline" href={s.url} target="_blank" rel="noreferrer">{s.name}</a></li>
            ))}
          </ul>
        </div>
      </div>
      <div className="border-t border-brand-800 py-4 text-center text-sm text-brand-200">
        © {new Date().getFullYear()} Find a Skilled Worker Ghana
      </div>
    </footer>
  );
}
