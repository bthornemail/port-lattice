# Port-Lattice Sync Contract (Fail-Closed)

This document specifies the minimal distributed sync contract for exchanging ULP trace segments as bytes.

Port-lattice is transport only:
- it MUST NOT interpret, canonicalize, merge, dedupe, or reorder events
- it MUST move NDJSON bytes unchanged (byte-preserving)

The kernel (ULP core invariant + port-matroid where applicable) is the only interpreter.

## Terms

- Trace: NDJSON of ULP events (see `ulp-core-invariant/docs/ULP-CONSTITUTION.md`).
- Checkpoint: an event type anchoring distributed sync ("Sabbath checkpoint").
- Segment: a bounded window of trace events exchanged between replicas, anchored to a known prior `(seq, hash)`.

## Protocol (Minimal)

The transport protocol is a thin wrapper around content-addressed segments.

### HELLO (capability + head advertisement)

Each peer advertises:
- supported ABI versions
- latest known checkpoint:
  - `seq`
  - `hash`
  - optional `snapshot_hash` (preimage digest) if available

Peers MUST refuse to sync if ABI is incompatible.

### REQUEST (bounded window)

Request a segment:
- `from_seq`, `from_hash` (anchor)
- `to_checkpoint_seq` (optional)
- hard caps:
  - `max_events`
  - `max_bytes`

### RESPONSE (bytes + digest)

Response includes:
- raw NDJSON bytes (segment)
- a digest of the exact bytes served (for re-pull and auditing)

### VERIFY (receiver side, fail-closed)

Receiver MUST validate before committing:
- strict schema (exact key-set)
- hash correctness (`hash == sha256(canonical_bytes(event))`)
- continuity:
  - first event `seq == from_seq + 1`
  - first event `prev == from_hash`
  - contiguous seq increments
  - `prev` chain matches prior `hash` within the segment
- checkpoint discipline (if syncing "between checkpoints"):
  - segment starts and ends with `Checkpoint`
  - checkpoints are proof-carrying and must be reproducible by replay
- size caps enforced

Commit rule:
- stage the segment
- validate as a whole
- append atomically
- on any failure: do not append any prefix; store the counterexample segment for debugging

## Stop Conditions (Mandatory)

Sync MUST stop (fail closed) on:
- schema mismatch (missing/extra keys)
- event hash mismatch
- `prev` chain break
- non-contiguous seq
- anchor mismatch (`from_seq/from_hash`)
- checkpoint mismatch (cannot be reconstructed)
- oversized segment (events/bytes)
- competing segments after same checkpoint (equivocation)

## Test Requirements

Transport invariants (port-lattice):
- served bytes MUST equal pulled bytes (byte-for-byte)
- must-reject fixtures MUST remain must-reject after transport

Kernel invariants:
- validating and replaying the same segment produces identical checkpoint/snapshot hashes
- segment acceptance is atomic (no partial prefixes)

