# Deploying BharatAo

Static Astro output — no server, no database, no adapter needed. Push to git, connect the repo, done.

## Option A: Vercel (recommended — simplest)

1. `vercel.com` → New Project → import the `bharatao` repo, root directory `site/`.
2. Framework preset: Astro (auto-detected). Build command `npm run build`, output `dist/`.
3. Add the custom domain (`bharatao.com`) in Project Settings → Domains once you own it.
4. Every push to `main` auto-deploys.

## Option B: Cloudflare Pages

1. `pages.cloudflare.com` → Create project → connect the repo, root directory `site/`.
2. Build command `npm run build`, output directory `dist`.
3. Add custom domain the same way.

## Publishing new content after deploy

`agents/a9_publisher.py --publish <slug>` writes into `site/src/content/articles/` and
`site/public/images/`. Commit + push those two paths (not `dist/`, not `node_modules/`) —
the host rebuilds automatically on push. This is the same "git push = new article live"
flow either host gives you for free.

## Not yet done

- Domain (`bharatao.com`) purchase status unknown — confirm before wiring DNS.
- No analytics (GA4) or sitemap wired up yet — add once a host is picked (Astro has an
  official `@astrojs/sitemap` integration, one command to add).
