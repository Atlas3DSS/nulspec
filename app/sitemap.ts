import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: "https://nulspec.com",
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: "https://nulspec.com/studies/001",
      changeFrequency: "daily",
      priority: 0.9,
    },
  ];
}
