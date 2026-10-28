"use client";
import NextLink from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentProps } from "react";
import { spaPath, spaSlug } from "@/lib/spa-path";

export default function SpaLink(props: ComponentProps<typeof NextLink>): React.ReactElement {
  const slug = spaSlug(usePathname());
  const href = typeof props.href === "string" ? spaPath(props.href, slug) : props.href;
  return <NextLink {...props} href={href}/>;
}
