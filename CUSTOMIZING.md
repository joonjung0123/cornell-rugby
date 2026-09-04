# CUSTOMIZING.md — Cornell Rugby Website Guide

This guide is written for **non-developers**. You do not need to know Python or web programming to customize the site. All common tasks are covered below.

> **Tip:** Every spot you need to edit in the template files is marked with a comment like `<!-- CUSTOMIZE: ... -->` so you can search for it easily.

---

## Table of Contents

1. [Replacing the Team Logo](#1-replacing-the-team-logo)
2. [Adding or Editing Players](#2-adding-or-editing-players)
3. [Adding or Editing Coaches](#3-adding-or-editing-coaches)
4. [Updating the Schedule](#4-updating-the-schedule)
5. [Editing the Recruit Page Text](#5-editing-the-recruit-page-text)
6. [Adding Merchandise Links](#6-adding-merchandise-links)
7. [Embedding Social Media Feeds](#7-embedding-social-media-feeds)
8. [Changing Colors or Fonts](#8-changing-colors-or-fonts)
9. [Editing the Home Page Tagline and Descriptions](#9-editing-the-home-page-tagline-and-descriptions)
10. [Editing Social Links in the Footer](#10-editing-social-links-in-the-footer)

---

## 1. Replacing the Team Logo

**File to edit:** `static/images/logo.png`

1. Prepare your logo image (PNG with transparent background works best).
2. Recommended size: **200 × 200 px** or larger (the site will scale it down automatically).
3. Rename your file to `logo.png`.
4. Replace the existing file at `static/images/logo.png` with your new file.
5. Save and refresh the browser — the new logo appears in the header and on the home page hero.

> If you want to use a different filename (e.g. `cornell-rugby-logo.png`), you also need to update the `src` in `templates/base.html` and `templates/home.html` — search for `logo.png` in both files.

---

## 2. Adding or Editing Players

The easiest way is through the **admin panel**:

1. Start the app locally: `python app.py`
2. Open your browser to: `http://127.0.0.1:5000/admin/`
3. Click **Men's Players** or **Women's Players**.
4. To add a player: click **+ Add Player**, fill in the form, upload a photo, click **Add Player**.
5. To edit a player: click **Edit** next to their name, update the fields, click **Edit Player**.
6. To delete a player: click **Delete** and confirm.

**Field descriptions:**

| Field | What to enter |
|---|---|
| Full Name | Player's full name, e.g. `John Smith` |
| Jersey Number | Just the number, e.g. `7` |
| Position | e.g. `Flanker`, `Prop`, `Scrum-half` |
| Year / Class | e.g. `Junior`, `Senior`, `Sophomore` |
| Hometown | e.g. `Buffalo, NY` |
| Bio | A short paragraph (2–4 sentences) about the player |
| Photo | Upload a jpg/png/gif/webp image. Recommended: portrait orientation, at least 300×400 px |

**To add a player photo manually (without the admin panel):**
1. Place the image file in `static/images/men/` or `static/images/women/`.
2. Open the relevant `data/men/players.json` or `data/women/players.json`.
3. Set the `"photo"` field to `"images/men/your-filename.jpg"`.

---

## 3. Adding or Editing Coaches

Same steps as players, but click **Men's Coaches** or **Women's Coaches** in the admin panel.

**Field descriptions:**

| Field | What to enter |
|---|---|
| Full Name | Coach's full name |
| Role / Title | e.g. `Head Coach`, `Forwards Coach`, `Skills Coach` |
| Bio | Short paragraph about the coach |
| Photo | Same requirements as player photos |

---

## 4. Updating the Schedule

1. Go to the admin panel: `http://127.0.0.1:5000/admin/`
2. Click **Men's Schedule** or **Women's Schedule**.
3. To add a game: click **+ Add Game**, fill in the form, click **Add Game**.
4. To edit a game (e.g. to add a result after it's played): click **Edit**, fill in the Result field (e.g. `W 34-12`), click **Edit Game**.
5. To delete a game: click **Delete** and confirm.

**Result format:**
- Win: `W 34-12`
- Loss: `L 10-21`
- Leave blank for upcoming games — the site will show "Upcoming" automatically.

**Games are automatically sorted by date** after every add or edit.

---

## 5. Editing the Recruit Page Text

**File to edit:** `templates/team/recruit.html`

1. Open the file in any text editor (e.g. Notepad, VS Code, TextEdit).
2. Find the section labeled `<!-- CUSTOMIZE: Edit the tagline below -->`.
3. The text between the `<p>` and `</p>` tags is what appears on the page — edit it directly.
4. To change the program highlights bullet list, find the `<ul class="recruit-highlights">` section and edit or add `<li>` items.

**Example — changing a bullet point:**
```html
<!-- Before -->
<li>Competitive Ivy League schedule with passionate, driven teammates</li>

<!-- After -->
<li>National-caliber competition with a tight-knit team family</li>
```

The recruit form automatically sends emails to `cornellrugby@cornell.edu`. To change this address, search for `cornellrugby@cornell.edu` in `templates/team/recruit.html` and update it.

---

## 6. Adding Merchandise Links

**File to edit:** `templates/team/fan.html`

1. Open the file in a text editor.
2. Find the section between `<!-- MERCH LINKS START -->` and `<!-- MERCH LINKS END -->`.
3. Each button looks like this:
   ```html
   <a href="#" target="_blank" rel="noopener" class="btn btn-primary">Shop Jerseys</a>
   ```
4. Replace the `#` with your actual store URL, and change the button label text as needed.
5. To add a new button, copy an existing `<a>` line and paste it below, then update the URL and label.

**Example:**
```html
<a href="https://store.example.com/cornell-rugby" target="_blank" rel="noopener" class="btn btn-primary">Shop Now</a>
```

---

## 7. Embedding Social Media Feeds

**File to edit:** `templates/team/fan.html`

### Instagram

1. Go to your Instagram post or profile page on the web.
2. Click the **…** (three dots) menu and choose **Embed**.
3. Copy the embed code provided.
4. Open `templates/team/fan.html` and find the comment `<!-- PASTE INSTAGRAM EMBED HERE -->`.
5. Paste the embed code directly below that comment, replacing the placeholder `<p>` link if desired.

### X (Twitter) Timeline

1. Go to [publish.twitter.com](https://publish.twitter.com/).
2. Paste your Twitter/X profile URL and choose **Embedded Timeline**.
3. Copy the generated code.
4. In `templates/team/fan.html`, find `<!-- PASTE X/TWITTER EMBED HERE -->` and paste the code there.

> **Note:** Social media embeds require an internet connection to display. They will not appear when running the app offline.

---

## 8. Changing Colors or Fonts

**File to edit:** `static/css/style.css`

Open the file and look at the very top — you'll see a block of CSS variables:

```css
:root {
  --color-primary:   #B31B1B;   /* Cornell Red — main color */
  --color-primary-dark: #8a1515;
  --color-accent:    #FFFFFF;
  --color-dark:      #1a1a1a;
  ...
  --font-base: -apple-system, "Segoe UI", system-ui, sans-serif;
}
```

- To change the **primary color** (used in headers, buttons, nav highlights): edit `--color-primary`.
- To change the **background** of the dark nav bar and footer: edit `--color-dark`.
- To change the **font**: replace the value of `--font-base` with your preferred font stack.

Colors use hex codes. You can find hex codes at [htmlcolorcodes.com](https://htmlcolorcodes.com/color-picker/).

---

## 9. Editing the Home Page Tagline and Descriptions

**File to edit:** `templates/home.html`

1. Open the file.
2. Find `<!-- CUSTOMIZE: Edit the tagline below -->` — the `<p>` tag right below it contains the hero tagline.
3. Find `<!-- CUSTOMIZE: Edit this description for the men's program -->` for the Men's section blurb.
4. Find `<!-- CUSTOMIZE: Edit this description for the women's program -->` for the Women's section blurb.
5. Edit the text between the tags and save.

---

## 10. Editing Social Links in the Footer

**File to edit:** `templates/base.html`

1. Open the file.
2. Find the section with `<!-- CUSTOMIZE: Update social links below -->`.
3. Replace the `href="#"` values with your actual Instagram, X, and other URLs.
4. Change the link label text if needed (e.g. "Instagram" → "@cornellrugby").

**Example:**
```html
<!-- Before -->
<a href="#" target="_blank" rel="noopener">Instagram</a>

<!-- After -->
<a href="https://instagram.com/cornellrugby" target="_blank" rel="noopener">@cornellrugby on Instagram</a>
```

---

## Need More Help?

- For code questions, open an issue on GitHub or reach out to your developer.
- For hosting/deployment questions, see `README.md`.
