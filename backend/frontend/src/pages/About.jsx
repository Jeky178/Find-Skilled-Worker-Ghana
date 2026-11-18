import { Link } from "react-router-dom";

export default function About() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-3xl font-bold">About Find a Skilled Worker Ghana</h1>
      <div className="mt-6 space-y-4 text-lg text-slate-700">
        <p>Finding a reliable plumber, electrician or carpenter in Ghana often depends on who you happen to know. We want to make it simple for anyone to find a skilled worker nearby and for good artisans to be found.</p>
        <p>Customers can compare profiles, send a service request and speak to the artisan on WhatsApp. Artisans get a professional profile to show their experience, prices and finished work.</p>
        <p>We are starting in Accra, in areas like Madina, Adenta, Dome, East Legon, Haatso, Achimota and Kasoa, and plan to grow across the country.</p>
      </div>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link to="/register" className="btn-accent">Create an account</Link>
        <Link to="/contact" className="btn-outline">Contact us</Link>
      </div>
    </section>
  );
}
