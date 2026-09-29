# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | yes |

## Reporting a vulnerability

Please don't open a public issue. Email **contact@ijazurrahim.com** with:

- what you found and how to reproduce it,
- the version of rttgap and the framework involved,
- whether you'd like to be credited.

You'll get a reply within 3 working days, and a fix or a plan within 14.

## Scope

In scope: anything that lets a client make a proxied connection read as direct
(beyond the documented limits: VPNs, measuring behind a CDN), crashes or resource
exhaustion triggered by a client, and header spoofing in the documented setups.

rttgap is one signal, not an authentication system. Don't block on it alone.
