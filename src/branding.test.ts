import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const legacyInternalName = ["bovi", "sta"].join("");
const legacyDisplayName = ["pashu", "swasthya"].join("");

describe("project branding", () => {
  it("contains no legacy project names in tracked files", () => {
    const trackedFiles = execFileSync("git", ["ls-files", "-z"], {
      encoding: "utf8",
    })
      .split("\0")
      .filter(Boolean);

    const offenders = trackedFiles.filter((file) => {
      const content = readFileSync(file, "utf8").toLowerCase();
      return (
        content.includes(legacyInternalName) ||
        content.includes(legacyDisplayName)
      );
    });

    expect(offenders).toEqual([]);
  });

  it("uses PashuMitra in the browser shell and login screen", () => {
    expect(readFileSync("index.html", "utf8")).toContain("<title>PashuMitra</title>");
    expect(readFileSync("src/screens/LoginGate.tsx", "utf8")).toContain("PashuMitra");
  });
});
