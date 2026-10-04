/**
 * Frame capture via the Chrome DevTools screencast, which delivers frames at
 * device-pixel resolution (Playwright's recordVideo is CSS-pixel VP8). Frames
 * arrive only when something changes, so each one is held until the next.
 */

import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { join } from "node:path";
import type { CDPSession, Page } from "playwright";

interface Frame {
  file: string;
  /** Seconds since the epoch, from the compositor. */
  timestamp: number;
}

export class Screencast {
  private session: CDPSession | null = null;
  private readonly frames: Frame[] = [];
  private stoppedAt = 0;

  constructor(
    private readonly page: Page,
    private readonly dir: string,
    private readonly size: { width: number; height: number },
  ) {}

  async start(): Promise<void> {
    const session = await this.page.context().newCDPSession(this.page);
    this.session = session;
    session.on("Page.screencastFrame", ({ data, metadata, sessionId }) => {
      const file = join(this.dir, `f${String(this.frames.length).padStart(6, "0")}.jpg`);
      writeFileSync(file, Buffer.from(data, "base64"));
      this.frames.push({ file, timestamp: metadata.timestamp ?? Date.now() / 1000 });
      session.send("Page.screencastFrameAck", { sessionId }).catch(() => undefined);
    });
    await session.send("Page.startScreencast", {
      format: "jpeg",
      quality: 92,
      maxWidth: this.size.width,
      maxHeight: this.size.height,
    });
  }

  async stop(): Promise<void> {
    this.stoppedAt = Date.now() / 1000;
    await this.session?.send("Page.stopScreencast");
    await this.session?.detach();
  }

  /** Encode the captured frames to a constant-frame-rate H.264 MP4. */
  encode(mp4: string): void {
    if (this.frames.length === 0) throw new Error("No frames captured");
    const lines: string[] = [];
    this.frames.forEach((f, i) => {
      const next = this.frames[i + 1]?.timestamp ?? this.stoppedAt;
      lines.push(`file '${f.file}'`, `duration ${Math.max(0.001, next - f.timestamp).toFixed(4)}`);
    });
    // The concat demuxer ignores the last duration unless the file repeats.
    lines.push(`file '${this.frames[this.frames.length - 1].file}'`);
    const list = join(this.dir, "frames.txt");
    writeFileSync(list, lines.join("\n") + "\n");
    execFileSync("ffmpeg", [
      "-y", "-loglevel", "error",
      "-f", "concat", "-safe", "0", "-i", list,
      "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30",
      "-c:v", "libx264", "-preset", "slow", "-crf", "20",
      "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
      mp4,
    ]);
  }
}
