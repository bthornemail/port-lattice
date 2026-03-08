# Introduction

Lattice Runtime is a POSIX-native control loop for declaring and maintaining
FIFO-first topologies. A lattice board defines ports, transports, and processes,
and Lattice materializes FIFOs, attaches transport projections, and supervises
processes. It continuously probes health and heals failed resources.

Key ideas:

- **Board as authority**: the filesystem is the source of truth.
- **Deterministic reconcile**: same board => same runtime state.
- **FIFO-first**: ports are structural FIFOs; transports are projections.
- **Trace-sovereign**: every action is logged to an append-only trace log and
  encoded as ULP polynomials.

Data plane projections are provided by lattice-netcat for TCP/UDP/SSL/Unix.
