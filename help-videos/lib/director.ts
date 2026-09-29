/**
 * Director - drives a Playwright page the way a person would, for recording.
 *
 * Playwright's own mouse is invisible in recordings, so we inject a cursor
 * overlay that follows real `mousemove` events, and move the mouse along
 * eased, slightly curved paths instead of teleporting. Randomness is seeded
 * from the clip id so re-renders are repeatable.
 */

import type { BrowserContext, Locator, Page } from "playwright";

type Point = { x: number; y: number };

/** Injected into every document before any page script runs. */
const OVERLAY_SCRIPT = `
(() => {
  const install = () => {
    if (document.getElementById("__hv-cursor")) return;
    const style = document.createElement("style");
    style.textContent = \`
      #__hv-cursor { position: fixed; left: 0; top: 0; z-index: 2147483647;
        pointer-events: none; width: 24px; height: 24px;
        transform: translate(-100px, -100px); will-change: transform;
        filter: drop-shadow(0 1px 2px rgba(0,0,0,.45)); }
      .__hv-ripple { position: fixed; z-index: 2147483646; pointer-events: none;
        width: 36px; height: 36px; margin: -18px 0 0 -18px; border-radius: 50%;
        border: 3px solid rgba(34,139,84,.9); animation: __hv-ripple .5s ease-out forwards; }
      @keyframes __hv-ripple { from { transform: scale(.3); opacity: 1; }
                               to   { transform: scale(1.4); opacity: 0; } }
      #__hv-caption { position: fixed; left: 50%; bottom: 36px; z-index: 2147483645;
        pointer-events: none; transform: translate(-50%, 12px); opacity: 0;
        max-width: 80%; padding: 12px 22px; border-radius: 12px;
        background: rgba(17,24,39,.88); color: #fff; text-align: center;
        font: 600 22px/1.35 system-ui, -apple-system, "Segoe UI", sans-serif;
        transition: opacity .3s ease, transform .3s ease; }
      #__hv-caption.__hv-show { opacity: 1; transform: translate(-50%, 0); }
      .__hv-highlight { position: fixed; z-index: 2147483644; pointer-events: none;
        border: 3px solid #f59e0b; border-radius: 10px;
        box-shadow: 0 0 0 4px rgba(245,158,11,.25);
        animation: __hv-pulse 1s ease-in-out infinite alternate; }
      #__hv-title { position: fixed; inset: 0; z-index: 2147483643; pointer-events: none;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        gap: 14px; padding: 0 10%; text-align: center; color: #fff;
        background: linear-gradient(135deg, rgba(20,83,45,.96), rgba(17,24,39,.96));
        font-family: system-ui, -apple-system, "Segoe UI", sans-serif; transition: opacity .5s ease; }
      #__hv-title small { font-size: 18px; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; opacity: .75; }
      #__hv-title strong { font-size: 42px; font-weight: 700; line-height: 1.25; }
      @keyframes __hv-pulse { from { box-shadow: 0 0 0 2px rgba(245,158,11,.35); }
                              to   { box-shadow: 0 0 0 10px rgba(245,158,11,.05); } }
    \`;
    document.documentElement.appendChild(style);
    const cursor = document.createElement("div");
    cursor.id = "__hv-cursor";
    cursor.innerHTML = '<svg viewBox="0 0 24 24" width="24" height="24">' +
      '<path d="M3 2 L3 19 L7.5 14.8 L10.6 21.5 L13.4 20.2 L10.4 13.6 L16.6 13.6 Z" ' +
      'fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    document.documentElement.appendChild(cursor);
    window.addEventListener("mousemove", (e) => {
      cursor.style.transform = "translate(" + (e.clientX - 3) + "px," + (e.clientY - 2) + "px)";
    }, true);
    window.addEventListener("mousedown", (e) => {
      const r = document.createElement("div");
      r.className = "__hv-ripple";
      r.style.left = e.clientX + "px";
      r.style.top = e.clientY + "px";
      document.documentElement.appendChild(r);
      setTimeout(() => r.remove(), 600);
    }, true);
  };
  if (document.documentElement) install();
  else document.addEventListener("DOMContentLoaded", install);
})();
`;

/** Small seeded PRNG (mulberry32) so a clip moves the same way every render. */
function seededRandom(seed: string): () => number {
  let h = 1779033703 ^ seed.length;
  for (let i = 0; i < seed.length; i++) {
    h = Math.imul(h ^ seed.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  let a = h >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

function bezier(p0: Point, p1: Point, p2: Point, p3: Point, t: number): Point {
  const u = 1 - t;
  return {
    x: u * u * u * p0.x + 3 * u * u * t * p1.x + 3 * u * t * t * p2.x + t * t * t * p3.x,
    y: u * u * u * p0.y + 3 * u * u * t * p1.y + 3 * u * t * t * p2.y + t * t * t * p3.y,
  };
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export class Director {
  readonly page: Page;
  private readonly rand: () => number;
  private pos: Point;

  constructor(page: Page, seed: string) {
    this.page = page;
    this.rand = seededRandom(seed);
    const vp = page.viewportSize() ?? { width: 1280, height: 800 };
    this.pos = { x: vp.width * 0.62, y: vp.height * 0.55 };
  }

  /** Install the overlay on every page (context) or one page, before its scripts run. */
  static async install(target: BrowserContext | Page): Promise<void> {
    await target.addInitScript(OVERLAY_SCRIPT);
  }

  private between(min: number, max: number): number {
    return min + (max - min) * this.rand();
  }

  pause(ms: number): Promise<void> {
    return sleep(ms);
  }

  /** Put the cursor somewhere visible without animating (e.g. at clip start). */
  async placeCursor(x: number, y: number): Promise<void> {
    this.pos = { x, y };
    await this.page.mouse.move(x, y);
  }

  /** Move along a curved, eased path to a point. Timed against the wall clock. */
  async moveToPoint(target: Point): Promise<void> {
    const from = this.pos;
    const dx = target.x - from.x;
    const dy = target.y - from.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 2) return;

    // Control points bow the path sideways a little, as a wrist does.
    const bow = Math.min(120, dist * 0.25) * (this.rand() < 0.5 ? -1 : 1) * this.between(0.3, 1);
    const nx = -dy / dist;
    const ny = dx / dist;
    const c1 = { x: from.x + dx * 0.3 + nx * bow, y: from.y + dy * 0.3 + ny * bow };
    const c2 = { x: from.x + dx * 0.7 + nx * bow * 0.5, y: from.y + dy * 0.7 + ny * bow * 0.5 };

    // Long moves slightly overshoot, then correct.
    const overshoot = dist > 300
      ? { x: target.x + (dx / dist) * this.between(6, 14), y: target.y + (dy / dist) * this.between(6, 14) }
      : target;

    const duration = Math.max(320, Math.min(1100, 180 + 140 * Math.log2(1 + dist / 12)));
    await this.animate(from, c1, c2, overshoot, duration);
    if (overshoot !== target) {
      await this.animate(overshoot, overshoot, target, target, 140);
    }
    this.pos = target;
  }

  private async animate(p0: Point, p1: Point, p2: Point, p3: Point, duration: number): Promise<void> {
    const start = performance.now();
    for (;;) {
      const t = Math.min(1, (performance.now() - start) / duration);
      const p = bezier(p0, p1, p2, p3, easeInOut(t));
      await this.page.mouse.move(p.x, p.y);
      if (t >= 1) break;
      await sleep(12);
    }
  }

  /** Move to a slightly randomised spot inside the element. */
  async moveTo(locator: Locator): Promise<void> {
    await locator.scrollIntoViewIfNeeded();
    const box = await locator.boundingBox();
    if (!box) throw new Error(`No bounding box for ${locator}`);
    const x = box.x + box.width * this.between(0.35, 0.6);
    const y = box.y + box.height * this.between(0.4, 0.6);
    await this.moveToPoint({ x, y });
  }

  async hover(locator: Locator, dwell = 600): Promise<void> {
    await this.moveTo(locator);
    await sleep(dwell);
  }

  async click(locator: Locator, after = 450): Promise<void> {
    await this.moveTo(locator);
    await sleep(this.between(120, 240));
    await this.page.mouse.down();
    await sleep(this.between(60, 110));
    await this.page.mouse.up();
    await sleep(after);
  }

  /** Click into a field and type with human, uneven key timing. */
  async type(locator: Locator, text: string): Promise<void> {
    await this.click(locator, 250);
    for (const ch of text) {
      await this.page.keyboard.type(ch);
      const pause = ch === " " ? this.between(120, 260) : this.between(60, 160);
      await sleep(this.rand() < 0.06 ? pause + 280 : pause);
    }
    await sleep(400);
  }

  async press(key: string, after = 400): Promise<void> {
    await this.page.keyboard.press(key);
    await sleep(after);
  }

  /** Cover the page with a full-screen title card (shown off-camera, before the trim point). */
  async showTitle(section: string, question: string): Promise<void> {
    await this.page.evaluate(
      ([sec, q]) => {
        const el = document.createElement("div");
        el.id = "__hv-title";
        const small = document.createElement("small");
        small.textContent = sec;
        const strong = document.createElement("strong");
        strong.textContent = q;
        el.append(small, strong);
        document.documentElement.appendChild(el);
      },
      [section, question],
    );
  }

  /** Hold the title card, then fade it to reveal the page. */
  async dismissTitle(hold = 2200): Promise<void> {
    await sleep(hold);
    await this.page.evaluate(() => {
      const el = document.getElementById("__hv-title");
      if (el) el.style.opacity = "0";
      setTimeout(() => el?.remove(), 600);
    });
    await sleep(700);
  }

  /** Lower-third caption. Replaces any current caption; `hold` is how long to wait after showing. */
  async caption(text: string, hold = 2200): Promise<void> {
    await this.page.evaluate((t) => {
      let el = document.getElementById("__hv-caption");
      if (!el) {
        el = document.createElement("div");
        el.id = "__hv-caption";
        document.documentElement.appendChild(el);
      }
      el.textContent = t;
      void el.offsetWidth;
      el.classList.add("__hv-show");
    }, text);
    await sleep(hold);
  }

  async hideCaption(after = 300): Promise<void> {
    await this.page.evaluate(() => document.getElementById("__hv-caption")?.classList.remove("__hv-show"));
    await sleep(after);
  }

  /** Pulsing outline around an element for `ms`, then removed. */
  async highlight(locator: Locator, ms = 1800): Promise<void> {
    await locator.scrollIntoViewIfNeeded();
    const box = await locator.boundingBox();
    if (!box) throw new Error(`No bounding box for ${locator}`);
    await this.page.evaluate((b) => {
      const el = document.createElement("div");
      el.className = "__hv-highlight";
      el.style.left = `${b.x - 6}px`;
      el.style.top = `${b.y - 6}px`;
      el.style.width = `${b.width + 12}px`;
      el.style.height = `${b.height + 12}px`;
      document.documentElement.appendChild(el);
    }, box);
    await sleep(ms);
    await this.page.evaluate(() => document.querySelectorAll(".__hv-highlight").forEach((e) => e.remove()));
  }

  /** Wait for API calls and any Leaflet tiles to finish, so nothing is grey on camera. */
  async settle(timeout = 15000): Promise<void> {
    await this.page.waitForLoadState("networkidle", { timeout }).catch(() => undefined);
    await this.page
      .waitForFunction(() => document.querySelectorAll(".leaflet-tile-loading").length === 0, undefined, { timeout })
      .catch(() => undefined);
    await sleep(250);
  }
}
