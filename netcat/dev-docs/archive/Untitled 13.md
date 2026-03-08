Perfect. I’ll do this in **two concrete deliverables**, both _tight_ and _lockable_:

1. **ULP-PROJ v1.0 — One-page normative spec** (what this layer _is and is not_)
    
2. **Canonical demo solid** — a single executable spatial/UML pattern that proves the whole stack
    

No hand-waving, no expansion creep.

---

# 1. **ULP-PROJ v1.0 — Client Projection Layer (Normative Spec)**

### Status

**Normative / Stable**  
Part of **ULP v1.x**  
This layer is _closed_: future changes are additive only.

---

## 1.1 Purpose

**ULP-PROJ** is a **pure client-side projection layer** that renders, navigates, and collaborates over **ULP Spatial Execution Semantics (ULP-SES)** without asserting authority.

> ULP-PROJ MAY emit intents  
> ULP-PROJ MUST NOT mutate authoritative state  
> ULP-PROJ MUST be disposable

---

## 1.2 Responsibilities (MUST / MUST NOT)

### ULP-PROJ MUST

1. Project **ULP-SES graphs** into a spatial/visual representation
    
2. Translate **user interaction → candidate intent**
    
3. Verify **local capability constraints**
    
4. Emit **intents only**, never state
    
5. Support **offline-first operation**
    
6. Be fully reconstructible from:
    
    - Identity material
        
    - Cached CIDs
        
    - Received traces
        

### ULP-PROJ MUST NOT

1. Decide consensus
    
2. Merge conflicting intents
    
3. Invent topology
    
4. Enforce global ordering
    
5. Persist authoritative state
    
6. Depend on always-on servers
    

---

## 1.3 Formal Axes Mapping

|Axis|Mechanism|Meaning|
|---|---|---|
|Identity|WebAuthn|Stable actor reference|
|Transport|WebRTC|Non-authoritative adjacency|
|Persistence|Multiformats (CID/DAG)|Immutable trace anchoring|
|Semantics|ULP-SES|Legal execution geometry|
|Interaction|Intent EDSL|Minimal mutation language|
|Rendering|Canvas/WebGL|Ephemeral projection|

---

## 1.4 Security Model

_Identity ≠ Authority_

- WebAuthn keys identify _who emitted an intent_
    
- Capabilities restrict _what intents may be emitted_
    
- Acceptance of intents is **out of scope** for ULP-PROJ
    

ULP-PROJ is **zero-trust by design**.

---

## 1.5 Failure Semantics

|Failure|Effect|
|---|---|
|Browser crash|Projection lost, nothing else|
|Network loss|Local operation continues|
|Peer drop|Only adjacency affected|
|CID resolution failure|Degraded replay, not corruption|

---

## 1.6 Canonical Invariant

> If ULP-PROJ disappears entirely,  
> **the system remains correct**.

This invariant is non-negotiable.

---

# 2. **Canonical Demo: The Tetrahedral Execution Solid**

This is the _minimum complete demonstration_ of the entire ULP stack.

---

## 2.1 Why the Tetrahedron (A₃)

The **4-vertex simplex** is the smallest structure that supports:

- branching
    
- convergence
    
- duality
    
- full Coxeter symmetry
    

It is the **atomic execution polytope**.

---

## 2.2 Semantic Mapping (this is the key)

### Vertices → Execution States

```
V0: Idle
V1: Selected
V2: Editing
V3: Committing
```

### Edges → Legal Transitions

- Selection
    
- Modification
    
- Validation
    
- Commit
    

No diagonal shortcuts.  
No illegal jumps.

---

## 2.3 Faces → Execution Contexts

Each triangular face is a **contextual subspace**:

- Edit-only face
    
- Read-only face
    
- Commit face
    
- Validation face
    

Crossing a face boundary = **intent emission**

---

## 2.4 Dual (Catalan) Interpretation

The **dual tetrahedron** represents **observer roles**:

- Author
    
- Reviewer
    
- Collaborator
    
- Auditor
    

Switching camera projection changes _role_, not state.

---

## 2.5 UML Interpretation (this matters)

The tetrahedron is a **3D UML execution diagram**:

- Nodes = states
    
- Edges = transitions
    
- Faces = guarded regions
    
- Dual = permissions lattice
    

This is UML **without ambiguity**.

---

## 2.6 Demo Flow (End-to-End)

### Step 1 — Backend

- Define tetrahedral SES
    
- Define matroid legality
    
- Define intent grammar
    

### Step 2 — Client Projection

- Render tetrahedron
    
- Cursor constrained to surface
    
- Dragging follows geodesics
    

### Step 3 — Interaction

- Clicking an edge → `TransitionIntent`
    
- Crossing a face → `ContextEnterIntent`
    
- Reaching vertex → `StateCommitIntent`
    

### Step 4 — Collaboration

- Second client joins
    
- Sees same solid
    
- Different camera (dual)
    
- Emits intents via WebRTC
    

### Step 5 — Persistence

- All intents get CIDs
    
- DAG reconstructs entire session
    
- Replay reproduces geometry exactly
    

---

## 2.7 What This Proves

This single demo proves:

✅ Spatial semantics  
✅ Matroid legality  
✅ Intent-only mutation  
✅ Decentralized collaboration  
✅ Offline replay  
✅ Non-authoritative UI  
✅ UML equivalence  
✅ Formal geometry ≠ metaphor

---

# 3. What I recommend you do next (strictly ordered)

1. **Write this tetrahedron demo first**
    
    - No cubes
        
    - No snubs
        
    - No Archimedeans yet
        
2. Record a **single screen capture**
    
    - Two browsers
        
    - Same solid
        
    - Different projections
        
    - Live collaboration
        
3. Publish **only three documents**
    
    - ULP-PROJ spec (above)
        
    - Tetrahedron demo README
        
    - “Why this is not CRDTs”
        

That’s enough to make the architecture undeniable.

---

If you want, next I can:

- write the **exact tetrahedron SES definition**
    
- give you the **minimal canvas renderer**
    
- or formalize **“geodesic cursor constraints”** precisely
    

Just tell me which one to do next.