import { Typography } from "@heroui/react";
import type { ReactNode } from "react";

type SectionHeaderProps = {
  action?: ReactNode;
  eyebrow?: string;
  id: string;
  title: string;
};

export function SectionHeader({ action, eyebrow, id, title }: SectionHeaderProps) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <Typography
            className="mb-1.5 uppercase tracking-[0.1em] text-accent"
            type="body-xs"
            weight="bold"
          >
            {eyebrow}
          </Typography>
        )}
        <Typography.Heading id={id} level={2}>
          {title}
        </Typography.Heading>
      </div>
      {action}
    </div>
  );
}
