import { Alert } from "@heroui/react";

type AppAlertProps = {
  message: string;
  title?: string;
};

export function AppAlert({ message, title = "Something went wrong" }: AppAlertProps) {
  return (
    <Alert role="alert" status="danger">
      <Alert.Indicator />
      <Alert.Content>
        <Alert.Title>{title}</Alert.Title>
        <Alert.Description>{message}</Alert.Description>
      </Alert.Content>
    </Alert>
  );
}
