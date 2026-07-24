"use client";

import {
  Description,
  Input,
  type InputProps,
  Label,
  TextField,
  type TextFieldProps,
} from "@heroui/react";

type AppTextFieldProps = Omit<TextFieldProps, "children" | "className"> & {
  className?: string;
  description?: string;
  inputProps?: Omit<InputProps, "className" | "fullWidth" | "variant">;
  label: string;
};

export function AppTextField({
  className = "",
  description,
  inputProps,
  label,
  ...props
}: AppTextFieldProps) {
  return (
    <TextField className={`min-w-0 ${className}`} fullWidth {...props}>
      <Label>{label}</Label>
      <Input fullWidth variant="secondary" {...inputProps} />
      {description && <Description>{description}</Description>}
    </TextField>
  );
}
