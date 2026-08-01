import type { MetadataRoute } from "next";
import { armEvidenceUrl, getStudies } from "@/lib/study";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const studies = getStudies();
  return [
    {
      url: "https://nulspec.com",
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: "https://nulspec.com/papers",
      changeFrequency: "daily",
      priority: 0.9,
    },
    ...studies.map((study) => ({
      url: `https://nulspec.com/studies/${study.study_id}`,
      lastModified: new Date(study.as_of_utc),
      changeFrequency: "monthly" as const,
      priority: 0.9,
    })),
    ...studies.flatMap((study) =>
      study.arms.map((arm) => ({
        url:
          "https://nulspec.com" +
          armEvidenceUrl(study.study_id, arm.arm_id),
        lastModified: new Date(study.as_of_utc),
        changeFrequency: "monthly" as const,
        priority: 0.7,
      })),
    ),
  ];
}
