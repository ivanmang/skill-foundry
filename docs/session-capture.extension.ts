/**
 * skill-capture — auto-run skill-foundry's session capture at session end.
 *
 * On `session_shutdown` with reason "quit" (Ctrl+C/D, `exit`, SIGHUP/SIGTERM —
 * i.e. the pi process is actually exiting), spawns
 * `./harness capture-session --session <file> --apply` detached, so the
 * reusable findings of an interactive session get drafted into
 * learnings/recent.md without any manual step.
 *
 * Opt out with:  export SKILL_CAPTURE_ON_EXIT=0
 * Override harness: export SKILL_FOUNDRY_HARNESS=/path/to/skill-foundry/harness
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

export default function (pi: ExtensionAPI) {
  pi.on("session_shutdown", async (event, ctx) => {
    // Only the real process exit; /new, /resume, /fork, /reload keep running.
    if (event.reason !== "quit") return;
    if (process.env.SKILL_CAPTURE_ON_EXIT === "0") return;

    const sessionFile = ctx.sessionManager.getSessionFile();
    if (!sessionFile) return; // ephemeral session, nothing to scan

    const harness = process.env.SKILL_FOUNDRY_HARNESS || join(homedir(), "skill-foundry", "harness");
    if (!existsSync(harness)) return;

    // Detached + unref: pi exits immediately; capture (which may call `pi -p`)
    // finishes in the background and writes to learnings/recent.md.
    const child = spawn(
      "bash",
      [harness, "capture-session", "--session", sessionFile, "--apply"],
      { detached: true, stdio: "ignore" },
    );
    child.unref();
  });
}
