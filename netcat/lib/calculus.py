#!/usr/bin/env python3
"""
ULP v2: Pure Type Composition Calculus
No pattern syntax, no baked-in meanings, pure algebra.
"""

import base64
import hashlib
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass(frozen=True)
class Atom:
    """Basis element generator."""

    name: str
    arity: int = 1
    description: str = ""


@dataclass
class Monomial:
    """Coefficient * Atom."""

    coefficient: int
    atom: Atom

    def __str__(self) -> str:
        sign = "+" if self.coefficient >= 0 else "-"
        return f"{sign}{abs(self.coefficient)}*{self.atom.name}"


@dataclass
class Polynomial:
    """Type expression as sum of monomials."""

    monomials: List[Monomial] = field(default_factory=list)

    def normalize(self) -> "Polynomial":
        """Combine like terms, remove zero coefficients."""
        combined: Dict[str, int] = defaultdict(int)
        for mono in self.monomials:
            combined[mono.atom.name] += mono.coefficient

        monomials: List[Monomial] = []
        for atom_name, coeff in sorted(combined.items()):
            if coeff != 0:
                monomials.append(Monomial(coeff, Atom(atom_name)))

        return Polynomial(monomials)

    def degree(self) -> int:
        """Sum of absolute coefficients."""
        return sum(abs(m.coefficient) for m in self.monomials)

    def atoms(self) -> Set[str]:
        """Set of atom names used."""
        return {m.atom.name for m in self.monomials}

    def __add__(self, other: "Polynomial") -> "Polynomial":
        return Polynomial(self.monomials + other.monomials).normalize()

    def __sub__(self, other: "Polynomial") -> "Polynomial":
        negated = Polynomial([
            Monomial(-m.coefficient, m.atom) for m in other.monomials
        ])
        return self + negated

    def __str__(self) -> str:
        if not self.monomials:
            return "0"
        normalized = self.normalize()
        return " ".join(str(m) for m in normalized.monomials)


@dataclass
class Constraint:
    """Constraint on polynomial compositions."""

    name: str
    condition: str  # Example: "degree <= 5", "atoms subset scope,order"
    description: str = ""


@dataclass
class Manifest:
    """Universe definition with constraints."""

    name: str
    atoms: List[Atom] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    composition_rules: List[str] = field(default_factory=list)

    def validate_polynomial(self, poly: Polynomial) -> bool:
        """Check if polynomial satisfies all constraints."""
        normalized = poly.normalize()

        for constraint in self.constraints:
            if not self._check_constraint(normalized, constraint):
                return False

        return True

    def _check_constraint(self, poly: Polynomial, constraint: Constraint) -> bool:
        """Evaluate a single constraint."""
        cond = constraint.condition

        if cond.startswith("degree <= "):
            max_degree = int(cond.split("<= ")[1])
            return poly.degree() <= max_degree

        if cond.startswith("atoms subset "):
            allowed = set(cond.split("subset ")[1].split(","))
            return poly.atoms().issubset({a.strip() for a in allowed})

        if cond.startswith("no atom "):
            forbidden = cond.split("no atom ")[1]
            return forbidden not in poly.atoms()

        if cond.startswith("coefficient "):
            # Example: "coefficient scope = 1"
            atom_name, expected = cond.split("coefficient ")[1].split(" = ")
            expected_val = int(expected)
            for mono in poly.monomials:
                if mono.atom.name == atom_name:
                    return mono.coefficient == expected_val
            return expected_val == 0

        return True


@dataclass
class Procedure:
    """Container type as polynomial."""

    name: str
    polynomial: Polynomial
    manifest_name: str

    def can_bind(self, interrupt: "Interrupt") -> bool:
        """Check if interrupt can bind to this procedure."""
        _combined = self.polynomial + interrupt.polynomial
        return True


@dataclass
class Interrupt:
    """Coefficient offer."""

    name: str
    polynomial: Polynomial
    compatible_procedures: List[str] = field(default_factory=list)


@dataclass
class Binding:
    """Result of successful composition."""

    procedure: Procedure
    interrupt: Interrupt
    resulting_polynomial: Polynomial
    trace_id: str

    def to_json(self) -> dict:
        return {
            "type": "binding",
            "procedure": self.procedure.name,
            "interrupt": self.interrupt.name,
            "result": str(self.resulting_polynomial),
            "trace_id": self.trace_id,
            "hash": self.compute_hash(),
        }

    def compute_hash(self) -> str:
        """Deterministic hash of binding."""
        data = f"{self.procedure.name}:{self.interrupt.name}:{self.resulting_polynomial}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class Universe:
    """Complete ULP universe with all definitions."""

    def __init__(self, base_path: str):
        self.base_path = base_path
        self.atoms: Dict[str, Atom] = {}
        self.manifests: Dict[str, Manifest] = {}
        self.procedures: Dict[str, Procedure] = {}
        self.interrupts: Dict[str, Interrupt] = {}

        self._load_universe()

    def _load_universe(self) -> None:
        """Load all definition files."""
        atoms_dir = os.path.join(self.base_path, "atoms")
        if os.path.exists(atoms_dir):
            for filename in os.listdir(atoms_dir):
                if filename.endswith(".atom"):
                    self._load_atom(os.path.join(atoms_dir, filename))

        manifests_dir = os.path.join(self.base_path, "manifests")
        if os.path.exists(manifests_dir):
            for filename in os.listdir(manifests_dir):
                if filename.endswith(".manifest"):
                    self._load_manifest(os.path.join(manifests_dir, filename))

        procedures_dir = os.path.join(self.base_path, "procedures")
        if os.path.exists(procedures_dir):
            for filename in os.listdir(procedures_dir):
                if filename.endswith(".procedure"):
                    self._load_procedure(os.path.join(procedures_dir, filename))

        interrupts_dir = os.path.join(self.base_path, "interrupts")
        if os.path.exists(interrupts_dir):
            for filename in os.listdir(interrupts_dir):
                if filename.endswith(".interrupt"):
                    self._load_interrupt(os.path.join(interrupts_dir, filename))

    def _load_atom(self, filepath: str) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip().split("\n")
        name = content[0].replace("atom ", "")
        arity = 1
        desc = ""

        for line in content[1:]:
            if line.startswith("arity:"):
                arity = int(line.split("arity:")[1].strip())
            elif line.startswith("description:"):
                desc = line.split("description:")[1].strip()

        self.atoms[name] = Atom(name, arity, desc)

    def _parse_polynomial(self, lines: List[str]) -> Polynomial:
        """Parse polynomial from lines like '+1*scope +2*order'."""
        monomials: List[Monomial] = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            for part in parts:
                if "*" in part:
                    coeff_str, atom_name = part.split("*", 1)
                    coeff = int(coeff_str.replace("+", ""))

                    if atom_name not in self.atoms:
                        self.atoms[atom_name] = Atom(atom_name)

                    monomials.append(Monomial(coeff, self.atoms[atom_name]))

        return Polynomial(monomials)

    def _load_manifest(self, filepath: str) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip().split("\n")
        name = content[0].replace("manifest ", "")

        manifest = Manifest(name)
        current_section: Optional[str] = None

        for line in content[1:]:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.endswith(":"):
                current_section = line[:-1]
            elif current_section == "atoms":
                if line.startswith("- "):
                    atom_name = line[2:].strip()
                    if atom_name not in self.atoms:
                        self.atoms[atom_name] = Atom(atom_name)
                    manifest.atoms.append(self.atoms[atom_name])
            elif current_section == "constraints":
                if line.startswith("- "):
                    constraint_text = line[2:].strip()
                    manifest.constraints.append(
                        Constraint(
                            f"constraint_{len(manifest.constraints)}",
                            constraint_text,
                        )
                    )
            elif current_section == "composition-rules":
                if line.startswith("- "):
                    rule = line[2:].strip()
                    manifest.composition_rules.append(rule)

        self.manifests[name] = manifest

    def _load_procedure(self, filepath: str) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip().split("\n")
        name = content[0].replace("procedure ", "")

        polynomial_lines: List[str] = []
        manifest_name = "default"

        for line in content[1:]:
            line = line.strip()
            if line.startswith("polynomial:"):
                continue
            if line.startswith("manifest:"):
                manifest_name = line.split("manifest:")[1].strip()
            elif line and not line.startswith("#"):
                polynomial_lines.append(line)

        polynomial = self._parse_polynomial(polynomial_lines)

        self.procedures[name] = Procedure(name, polynomial, manifest_name)

    def _load_interrupt(self, filepath: str) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip().split("\n")
        name = content[0].replace("interrupt ", "")

        polynomial_lines: List[str] = []
        compatible: List[str] = []

        for line in content[1:]:
            line = line.strip()
            if line.startswith("polynomial:"):
                continue
            if line.startswith("compatibility:"):
                compat_text = line.split("compatibility:")[1].strip()
                if compat_text.startswith("["):
                    compat_text = compat_text[1:-1]
                    compatible = [p.strip() for p in compat_text.split(",") if p.strip()]
                else:
                    compatible = [compat_text.strip()]
            elif line and not line.startswith("#"):
                polynomial_lines.append(line)

        polynomial = self._parse_polynomial(polynomial_lines)

        self.interrupts[name] = Interrupt(name, polynomial, compatible)

    def evaluate_binding(
        self, procedure_name: str, interrupt_name: str
    ) -> Optional[Binding]:
        """Evaluate if interrupt binds to procedure, return binding if successful."""
        if procedure_name not in self.procedures:
            print(f"Procedure not found: {procedure_name}")
            return None

        if interrupt_name not in self.interrupts:
            print(f"Interrupt not found: {interrupt_name}")
            return None

        procedure = self.procedures[procedure_name]
        interrupt = self.interrupts[interrupt_name]

        if interrupt.compatible_procedures and (
            procedure_name not in interrupt.compatible_procedures
        ):
            print(f"Interrupt {interrupt_name} not compatible with {procedure_name}")
            return None

        manifest = self.manifests.get(procedure.manifest_name)
        if not manifest:
            print(f"Manifest not found: {procedure.manifest_name}")
            return None

        combined = procedure.polynomial + interrupt.polynomial
        normalized = combined.normalize()

        if not manifest.validate_polynomial(normalized):
            print(f"Combined polynomial violates manifest constraints: {normalized}")
            return None

        trace_id = (
            f"trace_{procedure_name}_{interrupt_name}_"
            f"{hashlib.md5(str(normalized).encode()).hexdigest()[:8]}"
        )

        return Binding(procedure, interrupt, normalized, trace_id)

    def export_trace(self, binding: Binding, output_dir: str = "traces") -> str:
        """Export binding as self-describing trace."""
        os.makedirs(output_dir, exist_ok=True)

        trace_data = {
            "version": "ulp-calculus-1.0",
            "binding": binding.to_json(),
            "universe_snapshot": {
                "atoms": {
                    name: {
                        "arity": atom.arity,
                        "description": atom.description,
                    }
                    for name, atom in self.atoms.items()
                },
                "manifests": list(self.manifests.keys()),
                "procedures": list(self.procedures.keys()),
                "interrupts": list(self.interrupts.keys()),
            },
            "files": self._capture_files(),
        }

        filename = os.path.join(output_dir, f"{binding.trace_id}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2)

        print(f"Trace written to: {filename}")
        return filename

    def _capture_files(self) -> Dict[str, str]:
        """Capture all definition files as base64."""
        files: Dict[str, str] = {}

        for dir_name in ["atoms", "manifests", "procedures", "interrupts"]:
            dir_path = os.path.join(self.base_path, dir_name)
            if os.path.exists(dir_path):
                for filename in os.listdir(dir_path):
                    if filename.endswith(f".{dir_name[:-1]}"):
                        filepath = os.path.join(dir_path, filename)
                        with open(filepath, "rb") as f:
                            content = f.read()
                        files[f"{dir_name}/{filename}"] = base64.b64encode(
                            content
                        ).decode("ascii")

        return files
