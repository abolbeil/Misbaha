# Security policy

## Supported versions

Only the latest release receives security fixes.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.
Use GitHub's private reporting instead: the repository's **Security** tab → **Report a vulnerability**.
You can expect a first reply within 7 days.

Useful details: Misbaha version (menu → About), Windows version, whether you run the exe or the source, and steps to reproduce.

## What Misbaha does on your PC

- Installs a low-level **mouse** hook to react to the buttons you bind. It does not record mouse positions.
- Registers keyboard **shortcuts** with Windows (`RegisterHotKey`). It never reads what you type.
- Makes **one optional network request** a day: `GET https://api.github.com/repos/<owner>/<repo>/releases/latest`
  (TLS verified, no redirects followed, response size capped, no personal data sent). It only *tells* you about a
  newer release and opens its page on github.com; it never downloads or installs anything. Off switch: Settings → System.
- Stores data only in `%APPDATA%\Misbaha\` (or a `misbaha-data` folder next to the exe).
- Release builds are produced by GitHub Actions from this repository, with hash-locked dependencies.
  Each release lists the SHA-256 of `Misbaha.exe` in `Misbaha.exe.sha256`.
