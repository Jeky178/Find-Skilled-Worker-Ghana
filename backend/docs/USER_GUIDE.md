# User guide

How to use Find a Skilled Worker Ghana, for customers, artisans and administrators.

## For customers

### Find an artisan
1. On the home page choose a profession and an area, then press **Search**. (Or open **Browse artisans**.)
2. Narrow the results with the filters: profession, area, **Available now** and **Verified only**. Sort by recommended, highest rated, most experienced, lowest price or newest.
3. Open a profile to see the bio, prices, areas, photos of previous work and reviews from real customers. A blue **Verified** badge means our team checked the artisan's ID. **Premium** artisans appear higher in results.

### Request a service
1. On a profile press **Request this artisan** (you must be logged in).
2. Say what you need, describe the problem, choose where the job is, and optionally a preferred date and up to 5 photos.
3. Press **Send request**. The artisan is notified straight away.
4. Follow it under **My requests**. The status moves through *Awaiting response → Accepted → In progress → Completed*. You can **cancel** before the work starts, and mark the job **completed** once it is done.
5. Once an artisan accepts, use **WhatsApp** or **Call** on the request page to arrange details. Agree the price and the work **before** it starts.

### Review and report
- After a job is completed, give 1 to 5 stars and a comment on the request page. Your review shows as, for example, "Abena M." and updates the artisan's rating.
- If something is wrong, use **Report this profile** (on a profile) or **Report a problem with this job**. Reports are private, and you are told the outcome.

### Notifications
The bell in the top menu shows unread updates: request accepted, work started, job completed, and replies to your reports. Open **Notifications** to read them.

## For artisans

### Set up
1. **Sign up** as **I am a worker**, choose your trade and main area. A starter profile is created.
2. Open **Dashboard → Edit my profile** and complete it: profile photo, headline, a description of your experience, years of experience, your WhatsApp and phone numbers, your price range, the areas you work in, and photos of your finished work. The progress bar shows what is missing. Switch **available for new jobs** off when you are fully booked.

### Handle requests
1. New requests appear under **My requests** and in your notifications, with the customer's description and photos.
2. **Accept** the jobs you want, or **Decline** with a short reason. After you accept, you see the customer's phone number and a WhatsApp link.
3. Press **Start work**, then **Mark as completed** when finished. If you must cancel, give the customer a reason.
4. Reviews appear on your profile and under **My reviews**.

### Get verified
Open **Dashboard → Get verified**, choose your ID type, upload a clear photo of the ID (and optionally a trade certificate), and submit. Your documents are private: only administrators can see them. You are notified when the decision is made. If it is rejected, the reason is shown and you can apply again. (If a verification fee is set, you pay it first on the same page.)

### Plans and billing
**Dashboard → Plans and billing** shows your plan and payments.
- **Free:** profile, 5 portfolio photos, requests and reviews.
- **Premium:** priority in search, a Premium badge and 30 photos. Buy 1 month or 12 months. Renewing adds time.
- **Sponsored listing:** be featured at the top of results and on the home page for 7 or 30 days.
- Pay with **Mobile Money** or **card**. You return to the site and see "Payment confirmed". If you see "Waiting for confirmation", press **Check again**. If money left your account but nothing changed, contact us with the payment reference.

If you see "Online payments are not switched on yet", paid plans are not available yet.

## For administrators

Log in and open **Admin** in the top menu. Sections:

- **Overview:** key numbers and a **Needs your attention** list (pending verifications, open reports, unread messages).
- **Verifications:** press **Review documents**, compare the ID with the artisan, then **Approve and verify** or **Reject** (a reason is required and is shown to the artisan).
- **Users:** search and filter people. **Suspend** (with a reason) signs someone out and hides them from the directory instantly; **Reinstate** reverses it. For artisans: **Feature** (optionally until a date), and **Give Premium** or **Set to Free** (a gift: it records no payment). Administrator accounts cannot be suspended.
- **Requests:** read-only view of every job. Open one to see details.
- **Reports:** handle complaints. Mark as reviewing, **Resolve** or **Dismiss** with an outcome note (the reporter is told), and suspend the reported person from the same card.
- **Messages:** the Contact page inbox. Mark messages as read.
- **Payments:** confirmed revenue and every payment. Only the payment provider can confirm a payment: you cannot mark one as paid. Watch for "NOT DELIVERED" and old "Unconfirmed" rows.
- **Categories:** add, rename, describe or hide trades. Hiding removes a category from search and sign-up; existing profiles stay.
- **Activity:** newest sign-ups, jobs, reviews, reports and admin actions. Every admin action is recorded with who did it and when.

### Admin account tools
- Create or reset the admin: `python create_admin.py` (in the backend folder).
- Remove sample data: `python seed.py --remove-demo`.

## Troubleshooting

| Problem | What to do |
|---|---|
| "Cannot reach the server" | The backend is not running. Start it and open `/api/health` |
| "Incorrect email or password" | Check the exact email. Admins: run `python create_admin.py` to reset |
| "Too many failed attempts" | Wait 15 minutes, or restart the backend |
| White page | Press F12, read the **Console** tab for the error |
| Photos do not upload | Use JPG, PNG or WebP under 5 MB |
| Premium did not activate after paying | Open Billing and press the payment's **Check again**, or ask an admin to look at **Admin → Payments** |
