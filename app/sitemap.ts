import type { MetadataRoute } from "next";
import { getStudies } from "@/lib/study";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: "https://nulspec.com",
      changeFrequency: "weekly",
      priority: 1,
    },
    ...getStudies().map((study) => ({
      url: `https://nulspec.com/studies/${study.study_id}`,
      lastModified: new Date(study.as_of_utc),
      changeFrequency: "monthly" as const,
      priority: 0.9,
    })),
  ];
}
