import { Separator, Typography } from "@heroui/react";
import type { ReactNode } from "react";

type PageHeaderProps = {
  actions?: ReactNode;
  eyebrow?: string;
  title: string;
};

export function PageHeader({ actions, eyebrow, title }: PageHeaderProps) {
  return (
    <header className="grid gap-5">
      <div className="flex items-end justify-between gap-6 max-md:flex-col max-md:items-stretch">
        <div className="min-w-0">
          {eyebrow && (
            <Typography
              className="mb-2 uppercase tracking-[0.11em] text-accent"
              type="body-xs"
              weight="bold"
            >
              {eyebrow}
            </Typography>
          )}
          <Typography.Heading level={1}>{title}</Typography.Heading>
        </div>
        {actions && (
          <div className="flex shrink-0 items-end justify-end gap-2 max-sm:flex-wrap">
            {actions}
          </div>
        )}
      </div>
      <Separator />
    </header>
  );
}
