# Evening Poster Sender — How It Works

Every evening the Vercel cron calls `/api/daily_poster`, which sends the poster for
**tomorrow's** breakfast to WhatsApp with the caption
"Good Evening! 🤗 Tomorrow's Healthy Breakfast: <dish>. Have a great evening!".

## Why it wasn't sending (fixed 2026-11-26)
1. **No `vercel.json` → no cron.** Nothing ever triggered the function. Added a cron at
   `30 12 * * *` (12:30 UTC = 6:00 pm IST).
2. **Plain image messages are blocked outside WhatsApp's 24-hour window.** The API can accept
   the call but WhatsApp won't deliver a business-initiated free-form message unless the
   recipient messaged the business number in the last 24 h. Set `WHATSAPP_TEMPLATE_NAME`
   to an approved template with an IMAGE header to send at any time.
3. **Empty recipient by default** (`RECIPIENT_PHONE_NUMBER` defaulted to `""`). Now it fails with a
   clear message; multiple comma-separated numbers are supported.
4. **Errors were hidden.** Meta's real error message is now returned in the JSON response.
5. **Fragile dish matching** ("bread omelette" did not match folder "bread omlete"). Now
   normalised with aliases.
6. **Sent a plain food photo, not the poster.** `full dish photos/*/poster_N.png` are raw photos.
   The designed posters are now rendered into `posters/` and sent first.

## Vercel environment variables
| Name | Example | Required |
|---|---|---|
| `WHATSAPP_PHONE_NUMBER_ID` | `1234567890` | yes |
| `WHATSAPP_ACCESS_TOKEN` | permanent System User token | yes |
| `RECIPIENT_PHONE_NUMBER` | `919876543210,919812345678` | yes |
| `TOMORROW_DISH` | `ragi dosa` (legacy `TODAY_DISH` also works) | yes |
| `WHATSAPP_TEMPLATE_NAME` | `tomorrow_breakfast` | strongly recommended |
| `WHATSAPP_TEMPLATE_LANG` | `en` | optional |
| `CRON_SECRET` | random string (Vercel sends it automatically to crons) | optional |

## Changing the poster design
Edit `breakfast_poster_template.html`, then run `python render_posters.py` (uses Chrome/Edge)
and commit + push the `posters/` folder.

## Testing
Open `https://<your-project>.vercel.app/api/daily_poster?dish=ragi%20dosa` — the JSON shows
what was sent or the exact WhatsApp error. (If `CRON_SECRET` is set, this needs the
`Authorization: Bearer <secret>` header.)
