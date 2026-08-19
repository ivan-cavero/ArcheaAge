// Extrae id/nombre/tamaño de los archivos de una carpeta pública de Google Drive.
// Uso: node parse-drive.js [URL_CARPETA]
// No commitees el HTML: este script descarga la página en vivo.
const FOLDER = process.argv[2] || "https://drive.google.com/drive/folders/1_pIBVHIm1YFal-nteGaVuXjTv3Yrsv4Q";

const html = await (await fetch(FOLDER)).text();

// Las filas de archivos son <tr data-selectable data-id="ID" ...>
// (Google varía los saltos de línea entre atributos según la variante de página)
const rowRe = /<tr\s+data-selectable\s+data-id="([^"]+)"/g;
for (const m of html.matchAll(rowRe)) {
  const row = html.slice(m.index, m.index + 6000);
  const aria = [...row.matchAll(/aria-label="([^"]+)"/g)].map((x) => x[1]);
  const size = (aria.find((a) => a.startsWith("Size:")) || "").replace(/\n.*/, "");
  console.log(`${m[1]}\t${size}\t${aria[0] || "?"}`);
}