import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "LifeStats — Private Health Dashboard",
  description: "Private Google Health overview and sleep dashboard",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html className="dark" data-scroll-behavior="smooth" data-theme="dark" lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
