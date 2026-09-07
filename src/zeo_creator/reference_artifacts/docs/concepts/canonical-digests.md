# Canonical digests

Approval and artifact bindings use SHA-256 over
[RFC 8785 JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785)
bytes. This is a cross-language protocol, not an implementation detail.

## Canonical value rules

1. Pydantic models exclude their `content_digest` field before serialization.
2. Object keys follow JCS ordering; arrays retain their declared order because
   tuple order is semantic in every ZEO Creator contract.
3. Numbers use the ECMAScript/JCS representation. Values outside the JCS number
   domain fail rather than silently changing representation.
4. Every datetime must contain an offset. It is normalized to UTC and serialized
   as `YYYY-MM-DDTHH:MM:SS.ffffffZ` before JCS serialization.
5. Strings are preserved as Unicode. Canonically equivalent but byte-distinct
   Unicode strings are not normalized implicitly.
6. The digest is lowercase `sha256:` followed by 64 hexadecimal characters.

Golden vectors live in `reference/digest-vectors.json`. The Python suite and the
Node/TypeScript-consumer proof both verify those same bytes and hashes.

Changing any rule is a breaking cross-runtime contract change.
