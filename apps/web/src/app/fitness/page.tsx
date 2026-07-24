import { redirect } from "next/navigation";

export default function LegacyFitnessRedirect() {
  redirect("/steps");
}
