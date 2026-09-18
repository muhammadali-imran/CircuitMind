# Diagnose Module — CircuitMind

The Diagnose Module takes a circuit in JSON format as input, runs a series of electrical checks, and returns clear error and warning messages if any issues are found.

## How It Fits in the Pipeline

```
User message → Gateway Agent (agent/) → generate_circuit_tool → Circuit JSON → diagnose_circuit_tool → Diagnosis JSON
```

Previously reached via its own `/diagnose` REST route; now reached only through the agent's `diagnose_circuit_tool` (see `agent/tools.py`), which reads the current circuit from session state instead of requiring it as an argument.

## File

```
diagnose/
└── diagnose_module.py
```

## What It Does

| # | Check | Type |
|---|-------|------|
| 1 | Missing power source | Error |
| 2 | LED/Diode without current-limiting component | Warning |
| 3 | No connections defined | Error |
| 4 | Short circuit (power reaches ground with no load) | Error |
| 5 | Floating (disconnected) components | Warning |
| 6 | Capacitor polarity not indicated | Info |

## Input Format

```json
{
  "circuit_name": "LED Circuit",
  "components": ["battery", "resistor", "led"],
  "connections": ["battery -> resistor -> led"]
}
```

## Output Format

```python
{
  "circuit_name": "LED Circuit",
  "issues": [],          # list of error/warning strings
  "passed": True         # True if no issues found
}
```

### Issue Prefixes

| Prefix | Meaning |
|--------|---------|
| `Error:` | Critical problem — circuit will not work |
| `Warning:` | Potential problem — circuit may be damaged |
| `Info:` | Suggestion — good practice to follow |

## Supported Components

**Power Sources:** `battery`, `power_supply`, `solar_cell`
**Current Limiters:** `resistor`, `potentiometer`, `mosfet`, `transistor`, `npn_transistor`, `pnp_transistor`
**Components Needing Current Limit:** `led`, `diode`, `zener_diode`

## Usage

```python
from diagnose.diagnose_module import diagnose_circuit

circuit = {
    "circuit_name": "LED Circuit",
    "components": ["battery", "led"],
    "connections": ["battery -> led"]
}

result = diagnose_circuit(circuit)
print(result)
```

## How Short Circuit Detection Works

Uses a **BFS (Breadth-First Search)** algorithm to detect short circuits across paths of any length:

```
battery -> ground              ✅ detected (2 nodes)
battery -> wire -> ground      ✅ detected (3 nodes)
battery -> n1 -> n2 -> gnd    ✅ detected (4+ nodes)
```

Pure wire/net labels (`wire`, `node`, `net`, `trace`) are not counted as load components.

## Consistency with Explain Module

This module shares the same component knowledge base as `explain/explain_module.py`, via `utils/component_resolver.py`:

```python
POWER_SOURCES       = {"battery", "power_supply", "solar_cell"}
NEEDS_CURRENT_LIMIT = {"led", "diode", "zener_diode"}
CURRENT_LIMITERS    = {"resistor", "potentiometer", "mosfet", "transistor",
                       "npn_transistor", "pnp_transistor"}
```

Component names use **underscore** format: `op_amp`, `npn_transistor`, `power_supply`.
