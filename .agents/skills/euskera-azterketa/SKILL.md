---
name: euskera-azterketa
description: Evalúa el nivel de euskera de la documentación del proyecto (README.md, ENUNTZIATUA.md, etc.): estima el nivel (B1/B2/C1) y revisa léxico, gramática, sintaxis, ortografía y coherencia lanzando subagentes en paralelo. Úsala cuando pidan revisar, corregir o puntuar el euskera de la documentación, o "¿qué nivel de euskera tiene el README?".
---

# Revisión del nivel de euskera

Revisa prosa en euskera (Batua). Es un proceso de **solo lectura**: informa y propone correcciones, pero no edita nada salvo que el usuario lo pida después.

## Alcance
- Por defecto: `README.md`, `ENUNTZIATUA.md`, `streamlit/README.md` y cualquier otro `*.md` versionado que tenga prosa en euskera (`git ls-files '*.md'`).
- Si el usuario indica ficheros o secciones, limítate a ellos.
- Ignora bloques de código, comandos, nombres de ficheros/servicios/variables, URLs y tablas de valores: solo cuenta la prosa. Las partes escritas en español o inglés (como `AGENTS.md`) quedan fuera.

## Procedimiento
1. **Inventario**: lista los ficheros del alcance y estima las palabras de prosa de cada uno (`wc -w` sirve como aproximación). Si hay muchos ficheros o un fichero muy largo (>1500 palabras), reparte el trabajo por trozos de secciones al lanzar cada subagente.
2. **Lanza los 5 subagentes en paralelo** (una sola respuesta con 5 llamadas a `Agent`, `subagent_type: "general-purpose"`, solo lectura). Cada uno recibe la lista de ficheros, su dimensión y el formato de salida de [agentes.md](agentes.md), que contiene el prompt de cada uno:
   - **lexikoa**: erdarakadak, calcos, léxico no estándar, términos técnicos, registro, repeticiones.
   - **gramatika**: declinación, ergativo, concordancia verbal, auxiliares, postposiciones, determinante.
   - **sintaxia**: orden de la oración, subordinadas, frases demasiado largas o rotas, conectores, puntuación.
   - **ortografia**: ortografía de Euskaltzaindia, palabras compuestas, guiones, mayúsculas, números, declinación de siglas y nombres técnicos.
   - **koherentzia**: terminología unificada en todo el documento, tratamiento (zu/hi), tono, claridad, coherencia con el código/README real.
3. **Consolida** los informes:
   - Deduplica hallazgos que coincidan (mismo fichero y línea).
   - Verifica por tu cuenta una muestra de los hallazgos de mayor gravedad leyendo la línea citada; descarta los falsos positivos (p. ej., formas dialectales correctas, tecnicismos admitidos).
   - Calcula la densidad de errores: errores confirmados por cada 100 palabras de prosa, por dimensión y total.
4. **Asigna el nivel** con la tabla siguiente, combinando densidad de errores y complejidad (variedad de subordinadas, léxico, precisión técnica). Si ambos criterios discrepan, toma el menor y explícalo.

| Nivel (MCER / HABE-IVAP) | Densidad de errores | Rasgos |
|---|---|---|
| A2 / B1 bajo | > 10 por 100 palabras | Frases simples; fallos frecuentes de declinación y auxiliares; muchos calcos |
| B1 | 5–10 | Texto comprensible; subordinadas básicas; fallos repetidos de ergativo/verbo; léxico limitado o calcado |
| B2 | 2–5 | Texto fluido; subordinadas variadas; errores puntuales de morfología y léxico |
| C1 | 0,5–2 | Léxico preciso y natural; sintaxis rica; fallos casi solo de estilo u ortografía fina |
| C2 | < 0,5 | Indistinguible de un texto editado profesionalmente |

## Informe final
Responde en español (el usuario escribe en español) con este orden y sin relleno:
1. **Nivel estimado** y una frase de justificación.
2. **Tabla por dimensión**: errores confirmados, densidad, nota breve.
3. **Los 10 hallazgos más importantes**: `fichero:línea`, cita literal, problema, corrección propuesta.
4. **Patrones recurrentes** (los 3-5 errores que más se repiten; arreglarlos sube más el nivel).
5. **Qué falta para el siguiente nivel**.
6. Ofrece aplicar las correcciones; si el usuario acepta, edita con `Edit` fichero a fichero y enséñale el `git diff` al terminar.

## Reglas
- Las correcciones propuestas deben ser formas correctas y comprobables en Batua (Euskaltzaindia, Hiztegi Batua, Elhuyar, UZEI). Si dudas, marca el hallazgo como `dudoso` en vez de afirmarlo.
- Nunca "corrijas" nombres propios, identificadores técnicos ni la forma de declinar siglas que ya sea coherente en todo el documento (p. ej. `Kafka-n`, `NiFi-k`).
- No inventes cifras: la densidad sale de los hallazgos confirmados y del recuento de palabras real.
