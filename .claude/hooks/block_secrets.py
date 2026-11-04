#!/usr/bin/env python3
"""PreToolUse hook: impide que Claude lea secretos (.env, claves, entorno de contenedores...).

Lo que Claude lee con Read/Grep/Bash entra en su contexto y sale a la API. Este hook bloquea (exit 2)
los accesos habituales a secretos. Es una barrera de mejor esfuerzo, no una garantía: no sustituye
a no guardar secretos en ficheros que el agente pueda ver.
"""
import json
import re
import sys

# Rutas: .env y variantes (salvo .env.example), claves, certificados privados, credenciales.
SECRET_PATH = re.compile(
    r"""(?ix)
    (^|[/\\])\.env(\.(?!example\b|sample\b|template\b)[^/\\\s]*)?$        # .env, .env.prod, .env.local
    | \.(pem|key|p12|pfx|jks|keystore)$
    | (^|[/\\])(id_rsa|id_ed25519|id_ecdsa)(\.pub)?$
    | (^|[/\\])\.ssh([/\\]|$)
    | (^|[/\\])\.(aws|gnupg|netrc|npmrc|pypirc|pki)([/\\]|$)
    | (^|[/\\])credentials(\.json)?$
    | (^|[/\\])secrets?([/\\.]|$)
    | caddy[-_/]?(data|root)\S*(\.key)?$
    """
)

# Comandos Bash: leer .env, volcar entorno/secretos de contenedores, imprimir config resuelta.
SECRET_CMD = [
    (re.compile(r"(?<![\w.-])\.env(?![\w.-]|\.example|\.sample|\.template)"), "referencia a .env"),
    (re.compile(r"(^|[\s;&|(`])(printenv|env|export\s+-p|set)(\s*$|\s*[|;&>)])"), "volcado de variables de entorno"),
    (re.compile(r"docker(\s+compose\b|-compose\b).*\bconfig\b"), "docker compose config imprime los secretos resueltos"),
    (re.compile(r"docker\s+inspect\b"), "docker inspect expone variables de entorno"),
    (re.compile(r"docker\s+(compose\s+)?exec\b.*\b(env|printenv|/proc/\S*environ)\b"), "entorno de un contenedor"),
    (re.compile(r"/proc/[\w$*]+/environ"), "/proc/*/environ"),
    (re.compile(r"docker\s+volume\s+inspect\b"), "docker volume inspect expone opciones (p. ej. contraseña SMB)"),
    (re.compile(r"(^|[\s/])\.ssh(/|\s|$)|\bid_(rsa|ed25519|ecdsa)\b"), "claves SSH"),
    (re.compile(r"\bsecret-tool\b|\bpass\s+show\b|\bgpg\s+(-d|--decrypt)\b"), "gestor de secretos"),
]


def deny(reason: str) -> None:
    print(
        f"Bloqueado por el arnés de seguridad de CNC Guard: {reason}. "
        "No leas ni muestres secretos; pídele al usuario que lo haga él mismo si es imprescindible.",
        file=sys.stderr,
    )
    sys.exit(2)


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 — sin entrada válida no se decide nada
        sys.exit(0)
    tool = event.get("tool_name", "")
    args = event.get("tool_input") or {}

    paths = [args.get(k) for k in ("file_path", "path", "notebook_path") if isinstance(args.get(k), str)]
    for path in paths:
        if SECRET_PATH.search(path):
            deny(f"acceso a un fichero de secretos ({path})")

    if tool in ("Grep", "Glob"):
        for key in ("pattern", "glob"):
            value = args.get(key)
            if isinstance(value, str) and re.search(r"(^|[/*\\])\.env(?!\.example)", value):
                deny("búsqueda sobre ficheros .env")

    if tool == "Bash":
        command = args.get("command", "")
        if isinstance(command, str):
            for pattern, why in SECRET_CMD:
                if pattern.search(command):
                    deny(why)
    sys.exit(0)


if __name__ == "__main__":
    main()
