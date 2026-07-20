import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

// Schema mirrors the strict-JSON contract the AI writer agents produce
// (agents/prompts/news_v1.md + agents/lib/validator.py). A9 Publisher writes
// an approved draft here as a JSON file once a human has signed off --
// nothing lands in this collection unreviewed.
const articles = defineCollection({
  loader: glob({ pattern: "**/*.json", base: "./src/content/articles" }),
  schema: z.object({
    title: z.string(),
    slug: z.string(),
    meta_description: z.string().max(160),
    html_body: z.string(),
    faq: z.array(z.object({ q: z.string(), a: z.string() })).min(3).max(5),
    tags: z.array(z.string()),
    category: z.enum(["News", "Sarkari", "Ghumo", "Tools", "Gyaan", "Paisa"]),
    fact_sources: z.array(z.object({ claim: z.string(), source_url: z.string() })),
    image: z.string().optional(),
    published_at: z.string().datetime().or(z.string()),
  }),
});

export const collections = { articles };
