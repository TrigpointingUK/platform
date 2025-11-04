import { useQuery } from "@tanstack/react-query";
import * as yaml from "js-yaml";

interface NewsItem {
  id: number;
  date: string;
  title: string;
  summary: string;
  link?: string | null;
}

export function useNews() {
  return useQuery<NewsItem[]>({
    queryKey: ["news"],
    queryFn: async () => {
      const response = await fetch("/news.yaml");
      if (!response.ok) {
        throw new Error("Failed to fetch news");
      }
      const text = await response.text();
      return yaml.load(text) as NewsItem[];
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

