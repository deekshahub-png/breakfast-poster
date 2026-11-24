# Fix: Daily Poster Job Sending Old Images

## Summary
The 6am cron job was sending outdated poster images instead of newly created ones. Two code bugs were fixed, but the **root cause** was that new posters were never committed and pushed to GitHub, so Vercel (which deploys from `origin/main`) never saw them.

---

## Bugs Fixed

### 1. `api/daily-poster.py`
- **Before:** Ran the dish photo through `generate_poster.py`'s template drawing (logo, gold panel, title text, etc.) before sending.
- **After:** Finds whatever image file lives in the matching `full dish photos/<folder>/` and sends that file directly, untouched.

### 2. `whatsapp_sender.py`
- **Before:** `upload_media()` hardcoded `image/jpeg` for every upload, regardless of actual file type. If exports (e.g. from Canva/Hallmark) were PNG, this mislabeling could cause Meta to reject or corrupt the upload.
- **After:** Detects the real MIME type from the file extension before uploading.

---

## Root Cause (Why Old Posters Kept Sending)
- Git history confirmed `full dish photos/` was never touched since the first commit.
- Working tree was clean and fully in sync with GitHub.
- **New posters were never actually saved into the project, committed, or pushed.**
- Vercel deploys straight from `origin/main` on GitHub — it has no way to know new files exist unless they're pushed there.
- Result: the 6am job kept finding and sending the only files that existed remotely — the old ones.

---

## Remaining Steps

1. **Add new poster files** to the matching subfolder under `full dish photos/`
   Example: `full dish photos/bread omlete/` for Bread Omelette.

2. **Delete old screenshot files** from each folder (or ensure the new file's name sorts alphabetically first) — the code grabs the *first* image file it finds in the folder, so leftover old files can still win.

3. **Commit and push:**
   ```bash
   git add "full dish photos" api/daily-poster.py whatsapp_sender.py
   git commit -m "Send finished poster designs directly instead of auto-generated template"
   git push
   ```

4. **Test immediately** once Vercel redeploys by opening:
   ```
   https://<your-project>.vercel.app/api/daily-poster
   ```
   This triggers the job on demand without waiting for 6am (see `DEPLOY_GUIDE_VERCEL.md`).

---

## Open Question
`main.py` (the old local/manual runner) was **not** updated to match, since it's not part of the live pipeline (Vercel doesn't use it). Decide whether to:
- Update it to match the new logic, or
- Leave it as dead code / remove it if unused.
