"use client";

import { Button, type ButtonProps } from "@heroui/react";

type ButtonTone = "primary" | "secondary" | "danger" | "quiet";

type AppButtonProps = Omit<ButtonProps, "className" | "variant"> & {
  className?: string;
  tone?: ButtonTone;
};

const variants: Record<ButtonTone, ButtonProps["variant"]> = {
  primary: "primary",
  secondary: "secondary",
  danger: "danger-soft",
  quiet: "ghost",
};

export function AppButton({
  className = "",
  tone = "primary",
  ...props
}: AppButtonProps) {
  return (
    <Button
      className={`min-h-10 whitespace-nowrap ${className}`}
      variant={variants[tone]}
      {...props}
    />
  );
}
