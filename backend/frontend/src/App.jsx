import { Route, Routes } from "react-router-dom";
import MainLayout from "./layouts/MainLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import BrowseArtisans from "./pages/BrowseArtisans";
import ArtisanDetails from "./pages/ArtisanDetails";
import ArtisanProfile from "./pages/ArtisanProfile";
import CreateRequest from "./pages/CreateRequest";
import MyRequests from "./pages/MyRequests";
import RequestDetails from "./pages/RequestDetails";
import Reviews from "./pages/Reviews";
import Notifications from "./pages/Notifications";
import VerificationPage from "./pages/VerificationPage";
import AdminLayout from "./pages/admin/AdminLayout";
import Overview from "./pages/admin/Overview";
import Verifications from "./pages/admin/Verifications";
import Users from "./pages/admin/Users";
import AdminRequests from "./pages/admin/Requests";
import Reports from "./pages/admin/Reports";
import Categories from "./pages/admin/Categories";
import Messages from "./pages/admin/Messages";
import Activity from "./pages/admin/Activity";
import AdminPayments from "./pages/admin/Payments";
import Billing from "./pages/Billing";
import BillingCallback from "./pages/BillingCallback";
import Pricing from "./pages/Pricing";
import About from "./pages/About";
import Contact from "./pages/Contact";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/artisans" element={<BrowseArtisans />} />
        <Route path="/artisans/:id" element={<ArtisanDetails />} />
        <Route path="/about" element={<About />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/dashboard/profile" element={<ProtectedRoute roles={["artisan"]}><ArtisanProfile /></ProtectedRoute>} />
        <Route path="/artisans/:id/request" element={<ProtectedRoute roles={["customer"]}><CreateRequest /></ProtectedRoute>} />
        <Route path="/requests" element={<ProtectedRoute roles={["customer", "artisan"]}><MyRequests /></ProtectedRoute>} />
        <Route path="/requests/:id" element={<ProtectedRoute><RequestDetails /></ProtectedRoute>} />
        <Route path="/reviews" element={<ProtectedRoute roles={["customer", "artisan"]}><Reviews /></ProtectedRoute>} />
        <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/dashboard/billing" element={<ProtectedRoute roles={["artisan"]}><Billing /></ProtectedRoute>} />
        <Route path="/billing/callback" element={<ProtectedRoute roles={["artisan"]}><BillingCallback /></ProtectedRoute>} />
        <Route path="/dashboard/verification" element={<ProtectedRoute roles={["artisan"]}><VerificationPage /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute roles={["admin"]}><AdminLayout /></ProtectedRoute>}>
          <Route index element={<Overview />} />
          <Route path="verifications" element={<Verifications />} />
          <Route path="users" element={<Users />} />
          <Route path="requests" element={<AdminRequests />} />
          <Route path="reports" element={<Reports />} />
          <Route path="categories" element={<Categories />} />
          <Route path="messages" element={<Messages />} />
          <Route path="payments" element={<AdminPayments />} />
          <Route path="activity" element={<Activity />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
