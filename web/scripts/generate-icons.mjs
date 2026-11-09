// Generates the app icons from src/app/icon.svg (the logo). Run: npm run generate:icons
//
//   public/icons/icon-192.png, icon-512.png   rounded logo on transparent, "any" purpose
//   public/icons/maskable-512.png             full-bleed, logo inside the 80% safe zone, so
//                                             Android can crop it to a circle or squircle
//   src/app/apple-icon.png (180)              full-bleed; iOS rounds the corners itself
//
// The PNGs are committed so builds need no image tooling. Re-run after changing the logo.
import { readFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = readFileSync(resolve(root, "src/app/icon.svg"), "utf8");

const BACKGROUND = "#141e28";
const background = '<rect width="100" height="100" rx="22" fill="#141e28"/>';
if (!source.includes(background)) throw new Error("icon.svg no longer starts with the expected background");
const inner = source.slice(source.indexOf(background) + background.length, source.lastIndexOf("</svg>"));

/** The logo on a square, full-bleed background, scaled so it sits inside the safe zone. */
function fullBleed(scale) {
  const offset = (100 - 100 * scale) / 2;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="${BACKGROUND}"/>
  <g transform="translate(${offset} ${offset}) scale(${scale})">${inner}</g></svg>`;
}

async function png(svg, size, file) {
  mkdirSync(dirname(file), { recursive: true });
  await sharp(Buffer.from(svg), { density: 600 }).resize(size, size).png({ compressionLevel: 9 }).toFile(file);
  console.log(`wrote ${file.replace(root, ".")} (${size}x${size})`);
}

await png(source, 192, resolve(root, "public/icons/icon-192.png"));
await png(source, 512, resolve(root, "public/icons/icon-512.png"));
await png(fullBleed(0.8), 512, resolve(root, "public/icons/maskable-512.png"));
await png(fullBleed(0.84), 180, resolve(root, "src/app/apple-icon.png"));
