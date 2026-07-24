import { redirect } from "next/navigation";

export default function LegacyHealthRedirect() {
  redirect("/water-intake");
}
