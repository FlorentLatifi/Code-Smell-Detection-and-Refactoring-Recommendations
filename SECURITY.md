# Security policy

## Supported versions

Only the latest release gets security fixes. Older images stay published, but they
are not patched.

| Version | Supported |
|---|---|
| 1.0.x (latest) | yes |
| older | no |

## What JavaSmell is built to resist

JavaSmell runs on your own machine. It has no login, so it must never listen on a network
address that other people can reach. Every documented command publishes it on
`127.0.0.1` only. Within that setup:

- **Other websites in your browser.** Every page you open can send requests to
  `127.0.0.1`. The server refuses a foreign `Host` header (DNS rebinding) and a POST
  from a foreign `Origin`, and it cannot be embedded in another site's frame.
- **Paths.** Analysis is confined to the folder you mount or choose. A path outside
  it, or a symlink that escapes it, is refused.
- **Your source code.** Rewrites are offered as a patch. They are written to disk only
  when you press *Apply*, and only inside a clean git repository, so `git restore .`
  undoes them.
- **Resource limits.** File count, total size, and analysis time are capped, so one
  request cannot occupy the server indefinitely.
- **Code under analysis is never run.** It is parsed and compiled with `javac`, never
  executed.

Running JavaSmell on a public or shared address is outside this model and not
supported.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Report it privately through
**Security → Report a vulnerability** on this repository's GitHub page. Include the
version (`/api/health` shows it), the steps to reproduce, and what you expected to
happen.

You should get a first answer within 7 days. A confirmed problem is fixed in a patch
release and listed in `CHANGELOG.md`.
