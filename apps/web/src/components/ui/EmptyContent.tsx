import { EmptyState, Typography } from "@heroui/react";

type EmptyContentProps = {
  description: string;
  icon?: string;
  title: string;
};

export function EmptyContent({ description, icon = "○", title }: EmptyContentProps) {
  return (
    <EmptyState className="py-10 text-center">
      <span className="text-2xl text-muted" aria-hidden="true">
        {icon}
      </span>
      <Typography weight="semibold">{title}</Typography>
      <Typography.Paragraph color="muted" size="sm">
        {description}
      </Typography.Paragraph>
    </EmptyState>
  );
}
