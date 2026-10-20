export interface ListPage<T> {
  items: T[];
  hasMore: boolean;
  nextOffset: number | null;
}

export function listPage<T>(items: T[], response: Response | undefined, limit: number, offset: number): ListPage<T> {
  // Conservative fallback for an older proxy which strips metadata: a full
  // page never claims to be the whole list. An extra empty read is harmless.
  const hasMore = response?.headers.get("X-Has-More") === "true" ||
    (!response?.headers.has("X-Has-More") && items.length === limit);
  return { items, hasMore, nextOffset: hasMore ? offset + limit : null };
}
