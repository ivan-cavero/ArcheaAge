// Extracts id/name/size of the files in a public Google Drive folder.
// Usage: node parse-drive.js [FOLDER_URL]
// Do not commit the HTML: this script downloads the page live.
const FOLDER =
  process.argv[2] ||
  "https://drive.google.com/drive/folders/1_pIBVHIm1YFal-nteGaVuXjTv3Yrsv4Q";

const html = await (await fetch(FOLDER)).text();

// File rows are <tr data-selectable data-id="ID" ...>
// (Google varies the line breaks between attributes across page variants)
const rowRe = /<tr\s+data-selectable\s+data-id="([^"]+)"/g;
for (const m of html.matchAll(rowRe)) {
  const row = html.slice(m.index, m.index + 6000);
  const aria = [...row.matchAll(/aria-label="([^"]+)"/g)].map((x) => x[1]);
  const size = (aria.find((a) => a.startsWith("Size:")) || "").replace(
    /\n.*/,
    "",
  );
  console.log(`${m[1]}\t${size}\t${aria[0] || "?"}`);
}
