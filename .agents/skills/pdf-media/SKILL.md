---
name: pdf-media
description: Extrae las imágenes de un PDF, las guarda en docs/media/<nombre-del-pdf>/ del proyecto y las referencia desde un documento Markdown. Úsala cuando pasen un PDF (enunciado, informe, presentación) y pidan sacar sus imágenes/figuras, subirlas al proyecto o incluirlas en la documentación.
---

# PDF → imágenes del proyecto (`docs/media/`)

Las imágenes se guardan **dentro del repo** en `docs/media/<slug>/`, donde `<slug>` es el nombre del PDF en minúsculas y sin acentos (`Erronka1 Txostena.pdf` → `erronka1-txostena`). Así se versionan junto al texto que las usa y los enlaces relativos no se rompen.

## Procedimiento
1. **Localiza el PDF**: ruta dada por el usuario. Si es relativa o no existe, búscalo (`git ls-files '*.pdf'`, `ls ~/Downloads`). No lo copies al repo salvo que lo pidan.
2. **Extrae**, desde la raíz del repo:
   ```bash
   python3 -I .claude/skills/pdf-media/extract_pdf_media.py <ruta.pdf>
   ```
   Opciones: `--slug` (otro nombre de carpeta), `--min-size 80` (descarta iconos y filetes menores de 80 px), `--render-pages 3,5-6` (renderiza páginas completas a `--dpi 150` cuando las figuras son vectoriales: diagramas, gráficas exportadas, capturas hechas con formas), `--out` (otra carpeta base).
   El script descarta máscaras, imágenes pequeñas y duplicadas (logos repetidos en cada página), y escribe `docs/media/<slug>/manifest.json` con página, tamaño y tipo de cada fichero. Nombres: `<slug>-pNN-MM.png` (imagen MM de la página NN) y `<slug>-pNN-page.png` (página renderizada).
3. **Mira las imágenes** con `Read` (muestra primero las de mayor tamaño o las de páginas con figuras) y decide cuáles aportan algo: elimina las decorativas o sin contenido (`rm`) y actualiza `manifest.json` para que no cite ficheros borrados. Si el script dice "Sin imágenes raster", extrae el texto con `pdftotext -layout` para localizar las figuras y vuelve a lanzarlo con `--render-pages`.
4. **Referencia en Markdown**: solo si el usuario indica el documento destino (o pide "inclúyelas"). Si no, propón el destino en lugar de elegirlo:
   - Ruta **relativa al .md** que las contiene: `README.md` → `docs/media/<slug>/x.png`; `streamlit/README.md` → `../docs/media/<slug>/x.png`.
   - Alt text real, en el idioma del documento (euskera en `README.md`/`ENUNTZIATUA.md`), describiendo lo que muestra, no el nombre del fichero: `![CNC makinen alerta-panela Kibana-n](docs/media/erronka1-txostena/erronka1-txostena-p05-01.png)`.
   - Si el PDF tiene pie de figura, úsalo (`pdftotext -f N -l N -layout`) como alt o leyenda. Colócalas en la sección que habla de ellas, no todas juntas al final.
5. **Resume** al usuario: cuántas imágenes se guardaron y dónde, cuántas descartaste y por qué, y qué ficheros `.md` editaste. No hagas commit salvo que lo pida.

## Reglas
- Nunca sobrescribas imágenes de otro PDF: cada PDF tiene su carpeta. Si `docs/media/<slug>/` ya existe, avisa antes de repetir la extracción (el script reemplaza ficheros con el mismo nombre).
- Pesos: si un PNG supera ~1 MB y el usuario va a commitearlo, menciónalo y sugiere reducirlo (`convert x.png -resize 1600x x.png`).
- PDFs con datos sensibles o credenciales: mira las imágenes antes de referenciarlas y avisa si ves algo que no debería subirse al repo.
- Para PDFs escaneados (solo texto en imagen) no hay "figuras" que extraer: usa `--render-pages` solo si el usuario quiere las páginas.
