import { EmptyState, Typography } from "@heroui/react";
import { CircleDashed } from "lucide-react";
import type { ReactNode } from "react";

type EmptyContentProps = {
  description: string;
  icon?: ReactNode;
  title: string;
};

export function EmptyContent({
  description,
  icon = <CircleDashed className="size-6" />,
  title,
}: EmptyContentProps) {
  return (
    <EmptyState className="py-10 text-center">
      <span className="grid place-items-center text-muted" aria-hidden="true">
        {icon}
      </span>
      <Typography weight="semibold">{title}</Typography>
      <Typography.Paragraph color="muted" size="sm">
        {description}
      </Typography.Paragraph>
    </EmptyState>
  );
}
