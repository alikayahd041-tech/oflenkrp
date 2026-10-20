# OF LENK RP Forum starter

## Included
- Turkish and Arabic language entry points (KSA page direction and headings; full translation still needs extending)
- User registration/login with hashed passwords
- Complaint and application forms
- Comments and review statuses
- Rules editor for administrator roles
- Role assignment panel
- Organization pages for government departments and gangs

## Deploy to Render
1. Upload these files to a GitHub repository.
2. In Render choose New > Blueprint and connect the repository containing `render.yaml`, or create a Web Service with build command `pip install -r requirements.txt` and start command `gunicorn app:app`.
3. Add environment variables `ADMIN_USERNAME` and `ADMIN_PASSWORD` in Render. Use a unique, strong password.
4. Run the one-time CLI command `flask --app app bootstrap-admin` in Render Shell if available. If Shell is unavailable, bootstrap the first admin locally or add a controlled one-time setup flow before public launch.
5. Use a persistent disk mounted at `/var/data` so SQLite data survives restarts.

## Important limitations before public launch
- This is a functional starter, not a fully audited production forum.
- Google sign-in is not included; it requires Google OAuth credentials and callback setup.
- The site uses sessions; change secrets and add CSRF protection, rate limiting, email verification, and moderation/privacy policies before opening to the public.
- The admin bootstrap command must be run once after deployment to create the first Project Manager account.
- For leader-only posting, assign leader permissions in a future admin extension; this starter intentionally does not let ordinary users self-assign leadership.
- Do not ask users to submit sensitive personal data unless needed; application forms can contain personal details, so restrict access and define retention rules.
- 
