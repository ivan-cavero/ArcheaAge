const fs = require("fs");
const html = fs.readFileSync(process.argv[2] || __dirname + "/drive.html", "utf8");
const ids = [...new Set([...html.matchAll(/data-id="([^"]+)" data-selection-key="0"/g)].map((m) => m[1]))];
for (const id of ids) {
  const marker = `data-id="${id}" data-selection-key="0"`;
  const after = html.slice(html.indexOf(marker) + marker.length, html.indexOf(marker) + marker.length + 2500);
  const name = (after.match(/>([^<>]{2,80})</) || [])[1] || "?";
  const size = (after.match(/data-size="?(\d+)"?/) || [])[1] || "?";
  console.log(`${id}\t${size}\t${name.trim()}`);
}