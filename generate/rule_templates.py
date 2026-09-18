"""
CircuitMind - Generate Module: rule-based fallback
generate/rule_templates.py

Keyword-matched circuit templates, used when the LLM path is unavailable.
Extracted from the original generate.py — logic unchanged.
"""

_RULES = [
    # ── Digital Logic Circuits ──────────────────────────────────────────────────
    (["odd parity", "odd_parity"],              "Odd Parity Generator",    ["input_a", "input_b", "input_c", "xor1", "xnor2", "parity_output"], ["input_a -> xor1 -> xnor2 -> parity_output", "input_b -> xor1", "input_c -> xnor2"], "3-bit odd parity generator circuit"),
    (["even parity", "even_parity"],            "Even Parity Generator",   ["input_a", "input_b", "input_c", "xor1", "xor2", "parity_output"], ["input_a -> xor1 -> xor2 -> parity_output", "input_b -> xor1", "input_c -> xor2"], "3-bit even parity generator circuit"),
    # Use full phrases here — matching is substring OR, so ["half", "adder"]
    # would also fire on "half subtractor" (and vice versa) because of "half".
    (["half subtractor", "half-subtractor", "half_subtractor", "halfsubtractor"],
                                               "Half Subtractor Circuit",  ["input_a", "input_b", "xor", "not", "and", "diff_output", "borrow_output"], ["input_a -> xor -> diff_output", "input_b -> xor", "input_a -> not -> and -> borrow_output", "input_b -> and"], "Half subtractor circuit computing difference and borrow"),
    (["full subtractor", "full-subtractor", "full_subtractor", "fullsubtractor"],
                                               "Full Subtractor Circuit",  ["input_a", "input_b", "bin", "xor1", "xor2", "not1", "and1", "not2", "and2", "or", "diff_output", "borrow_output"], ["input_a -> xor1 -> xor2 -> diff_output", "input_b -> xor1", "bin -> xor2", "input_a -> not1 -> and1 -> or -> borrow_output", "input_b -> and1", "xor1 -> not2 -> and2 -> or", "bin -> and2"], "Full subtractor circuit with borrow-in"),
    (["half adder", "half-adder", "half_adder", "halfadder"],
                                               "Half Adder Circuit",       ["input_a", "input_b", "xor", "and", "sum_output", "carry_output"], ["input_a -> xor -> sum_output", "input_b -> xor", "input_a -> and -> carry_output", "input_b -> and"], "Half adder circuit computing sum and carry"),
    (["full adder", "full-adder", "full_adder", "fulladder"],
                                               "Full Adder Circuit",       ["input_a", "input_b", "cin", "xor1", "xor2", "and1", "and2", "or", "sum_output", "cout"], ["input_a -> xor1 -> xor2 -> sum_output", "input_b -> xor1", "cin -> xor2", "input_a -> and1 -> or -> cout", "input_b -> and1", "xor1 -> and2 -> or", "cin -> and2"], "Full adder circuit with carry-in"),
    (["multiplexer", "mux"],                    "2-to-1 Multiplexer",      ["input_a", "input_b", "sel", "not", "and1", "and2", "or", "output"], ["input_a -> and1 -> or -> output", "sel -> not -> and1", "input_b -> and2 -> or", "sel -> and2"], "2-to-1 multiplexer circuit"),
    (["demultiplexer", "demux"],                "1-to-2 Demultiplexer",    ["input_din", "sel", "not", "and1", "and2", "output_y0", "output_y1"], ["input_din -> and1 -> output_y0", "sel -> not -> and1", "input_din -> and2 -> output_y1", "sel -> and2"], "1-to-2 demultiplexer circuit"),
    (["decoder"],                               "2-to-4 Decoder",          ["input_a", "input_b", "not_a", "not_b", "and0", "and1", "and2", "and3", "y0", "y1", "y2", "y3"], ["input_a -> not_a -> and0 -> y0", "input_b -> not_b -> and0", "input_a -> and1 -> y1", "input_b -> not_b -> and1", "input_a -> not_a -> and2 -> y2", "input_b -> and2", "input_a -> and3 -> y3", "input_b -> and3"], "2-to-4 line decoder circuit"),
    (["comparator"],                            "1-Bit Comparator",        ["input_a", "input_b", "not_a", "not_b", "xnor", "and_gt", "and_lt", "eq_out", "gt_out", "lt_out"], ["input_a -> xnor -> eq_out", "input_b -> xnor", "input_a -> and_gt -> gt_out", "input_b -> not_b -> and_gt", "input_a -> not_a -> and_lt -> lt_out", "input_b -> and_lt"], "1-bit magnitude comparator"),
    (["xor", "xnor"],                           "XOR / XNOR Circuit",       ["input_a", "input_b", "xor", "output"],                ["input_a -> xor -> output", "input_b -> xor"], "2-input XOR gate circuit"),
    (["logic gate", "logic circuit"],           "Logic Gate Circuit",       ["input_a", "input_b", "and", "or", "output"],          ["input_a -> and -> or -> output", "input_b -> and", "input_b -> or"], "Combinational logic gate circuit"),
    # ── Analog / IC Circuits ─────────────────────────────────────────────────────
    (["led", "light"],                         "LED Circuit",              ["battery", "resistor", "led"],                          ["battery -> resistor -> led"],                        "Basic LED circuit with current-limiting resistor"),
    (["motor"],                                "Motor Circuit",            ["battery", "switch", "dc_motor"],                       ["battery -> switch -> dc_motor"],                     "Basic DC motor circuit with on/off switch"),
    (["buzzer"],                               "Buzzer Circuit",           ["battery", "resistor", "buzzer"],                       ["battery -> resistor -> buzzer"],                     "Buzzer circuit with resistor for sound output"),
    (["fan"],                                  "Fan Circuit",              ["battery", "switch", "capacitor", "dc_motor"],          ["battery -> switch -> capacitor -> dc_motor"],        "Fan circuit with capacitor for smooth startup"),
    (["temperature", "sensor"],                "Temperature Sensor",       ["battery", "thermistor", "resistor", "microcontroller"],["battery -> thermistor -> resistor -> microcontroller"],"Temperature sensing circuit using thermistor"),
    (["solar"],                                "Solar Charging Circuit",   ["solar_cell", "diode", "charge_controller", "battery"],["solar_cell -> diode -> charge_controller -> battery"],"Solar panel battery charging circuit"),
    (["555", "timer"],                         "555 Timer Circuit",        ["battery", "555_timer", "resistor", "capacitor", "led"],["battery -> 555_timer -> resistor -> capacitor -> led"],"555 timer astable multivibrator"),
    (["rc", "filter"],                         "RC Filter Circuit",        ["power_supply", "resistor", "capacitor"],              ["power_supply -> resistor -> capacitor -> ground"],    "RC low-pass filter circuit"),
]


def generate_with_rules(prompt: str) -> dict:
    p = prompt.lower()
    for keywords, name, components, connections, description in _RULES:
        if any(kw in p for kw in keywords):
            return {
                "circuit_name": name,
                "components":   components,
                "connections":  connections,
                "confidence":   "high",
                "description":  description,
                "source":       "rule-based",
            }
    return {
        "circuit_name": "Unknown",
        "components":   [],
        "connections":  [],
        "confidence":   "low",
        "description":  "Circuit not recognised. Try: led, motor, buzzer, fan, temperature, solar, 555 timer, rc filter.",
        "source":       "rule-based",
    }
