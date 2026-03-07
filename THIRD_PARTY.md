# Third-Party Licensing Notes

## xpress

This project depends on `xpress` (`xpress>=9.8.0`) for optimization tooling.

`xpress` is proprietary/commercial software and is **not** covered by this
repository's MIT license.

Workshop default mode: **Xpress Community** when `community-xpauth.xpr` is
available.

Guidance:
- The workshop harness initializes `xpress` with the packaged
  `license/community-xpauth.xpr` file when present, which runs Xpress in
  Community mode.
- For unrestricted or production/commercial use, ensure you have an active,
  valid FICO Xpress license.
- If your environment does not provide the required capability level, use
  alternative open-source solvers/dependencies where available.
- Review your institution or organization's software licensing policy before distribution or production use.
