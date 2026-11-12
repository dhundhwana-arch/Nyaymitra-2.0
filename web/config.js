/* NYAYMITRA 2.0 — deployment configuration for the static frontend.
 *
 * apiBase: origin of the backend API, WITHOUT a trailing slash and WITHOUT "/api/v1".
 *   ""                                  -> same origin (the backend serves this website itself)
 *   "https://your-backend.example.com"  -> frontend and backend are separate websites
 *
 * When the two are separate you must ALSO:
 *   1. list this website's origin in the backend's NYAYMITRA_ALLOWED_ORIGINS (CORS), and
 *   2. allow the backend origin in web/_headers (connect-src).
 * `python scripts/configure_frontend.py --api-base https://...` does 2 and edits this file.
 */
window.NYAYMITRA_CONFIG = { apiBase: "" };
