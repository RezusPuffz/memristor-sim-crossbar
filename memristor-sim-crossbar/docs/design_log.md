# Design Log

How the readout chain was designed, made buildable, laid out and verified, including the mistakes. All numbers are from Spectre/PVS/Quantus runs on gpdk045 unless marked as an estimate.

---

## 1. The problem: a floating bitline breaks the multiply

Each cell's current is (V_WL − V_BL) · G, and KCL sums the currents on the bitline. That only works if V_BL is pinned. If the bitline floats, it rises as current grows. Every cell then sees less voltage, the effective weights shrink with the input, and the MAC goes nonlinear.

So the whole readout has one job: **hold the bitline at a fixed virtual ground (300 mV) while copying out the current flowing into it.**

## 2. How the clamp evolved

| Step | Idea | Why it wasn't enough / what it fixed |
|---|---|---|
| 1 | Diode-connected device or resistor | V_BL rises with current: no clamp |
| 2 | Amplifier drives the mirror gate (feedback clamp) | Error ≈ input / loop gain, and loop gain ≈ gm·Rout |
| 3 | Long channels (L = 4 µm) | Rout ≈ 61 MΩ, gm·Rout ≈ 38 per stage |
| 4 | Cascodes (NMOS in readout, PMOS in column mirror) | Output resistance ≈ 2.3 GΩ, ~40× stiffer |
| 5 | Two-stage Miller OTA (`ota3`) | Gain from stage 1, swing from stage 2 |
| 6 | 2 pF Miller cap + ~10 MΩ shunt damper (bitline → ref) | Pole splitting + damping of the slow bitline node |

## 3. Turning ideal parts into real ones

Every ideal element in a schematic has to become a kit device before LVS can pass.

**Damping resistor → MOS resistor.**
- **Why the kit resistor wouldn't do:** the best one (poly, 650 Ω/sq) would need about 4,900 µm² for 10 MΩ.
- **What replaced it:** an NMOS (2u/4u) biased by a diode-connected replica of itself, giving R = U_T / I.
- **Characterised at 27 °C:** 10.06 MΩ at 3.2 nA. That's 24% above the ideal prediction because of DIBL/CLM on the replica.
- **Over temperature (0 / 27 / 85 °C):** R = 9.43 / 10.06 / 11.34 MΩ.
- **Damping stability:** R·gm drifts only −8% across that range, against −24% for a fixed resistor, so the MOS resistor damps about 3× more steadily.
- **Final bias:** 3.58 nA, which gives about 9 MΩ. Accepted, because replica mismatch alone is ±10–20%.

**Ideal capacitor → MIM capacitor.**
- **Construction:** 54 units of 5.555 × 5.555 µm, about 1.999 pF in total.
- **Orientation:** top plate on the sensitive high-impedance node, bottom plate on the low-impedance output.
- **Check:** the stability test was re-run with the real cap and was unchanged.

**Layout-driven schematic split.**
- **The change:** the OTA devices were split into 2 µm unit fingers so they could be interleaved.
- **The effect:** "electrically identical", but the bitline still moved by 0.19 mV.
- **Lesson:** layout-driven schematic edits still need a re-simulation.

## 4. A kit finding: length is a bad sizing knob in subthreshold

- **What two independent length changes showed:** current scaled as **I ∝ L^−0.4**, not L^−1. This is the reverse short-channel effect: longer devices have a lower threshold voltage, which partly cancels the extra length.
- **Width, by contrast:** current scaled almost linearly with width (13% narrow-width effect at 640 nm).
- **Rule I followed afterwards:** size subthreshold currents with W, and build ratios from identical unit devices.

## 5. Stability

Three transient cases on `readout4` (2 pF Miller cap, MOS damper):

| Case | Bitline load | Step | Result |
|---|---|---|---|
| Easy | 1 pF / 50 MΩ | ~1 nA | Settles ~2 ms, a few small cycles |
| Long bitline | 10 pF / 50 MΩ | ~1 nA | Settles ~3 ms |
| Hard | 10 pF / 5 MΩ | ~10 nA | ~90% overshoot, settles 2.5–3.5 ms |

- **The hard case with an ideal 10 MΩ ringed the same way.** So the ringing belongs to the loop under heavy load, not to the MOS resistor.
- **Decision:** keep the 2 pF Miller cap. Shrinking it to save area would thin an already small phase margin.

## 6. Layout

**Matching**
- **OTA input pair and load mirror:** interleaved `ABBAABBA` on a 4.92 µm pitch, so both centroids land in the same place and linear gradients cancel.
- **1:4 bias ratio:** built from five identical 4u/2u devices (`BBABB`), so the ratio is set by counting, not by W/L.

**Wells and taps**
- **One shared n-well** for all PMOS, with tap strips (n-well tap = vdd rail, substrate tap = ground rail).
- **Strips rather than full guard rings,** to keep the high-impedance wires short.

**Routing convention**
- **Layer directions:** Metal2 horizontal, Metal3 vertical, so nets cross without touching.
- **Bias lines:** kept away from the high-impedance nodes (bitlines, mirror gates, `sum`).
- **MIM caps:** sit between Metal10 and Metal11, with coarse spacing rules (≥ 1.25 µm). Running DRC before routing turned that into a one-number fix.

**Hierarchy**
- **`colout3` mirrors its two `readout4`** so their mirror stacks face a shared PMOS cascode mirror in the centre.
- **The 2 pF caps sit on the outer edges.** They are most of the area.

## 7. Bugs LVS caught that DRC didn't

DRC checks geometry against rules. It has no idea which net a shape belongs to. Every real wiring bug in this project was DRC-clean.

| Cell | Bug | Symptom | Fix |
|---|---|---|---|
| practice mirror | Three drain/gate wiring errors | LVS mismatch, DRC clean | Rewired; one label per net so LVS has to prove the metal |
| `ota3` | N-well tap never wired to vdd | All PMOS bodies on an unnamed floating net | Metal from tap to vdd rail |
| `ota3` | PMOS sources split | PVS saw series stacks instead of parallel devices | Joined sources |
| `ota3` | One input-pair finger's source not on tail | Pair 3:4 instead of 4:4, would unbalance the OTA | Connected the finger |
| `ota3` | Pins without text labels | PVS reported missing nets | Labels on the pin layer, on the metal |
| `readout4` | New Metal2 gate bus crossed the OTA's Metal2 ground drop | gate shorted to ground | Metal3 bridge over the crossing |
| `colout3` | Two instance substrate strips not joined at top level | Soft-connect warnings on ground | Metal1 bridge between strips |
| `colout3` | Labels clicked onto instance metal | Label attached to the wrong object | Pins and labels on top-level metal stubs |

## 8. Post-layout verification

Parasitics were extracted with Quantus (C-only, coupled), and the extracted views were simulated through a config view.

- **`readout4` transients:** all three cases match schematic behaviour: easy ~2 ms, long bitline ~3 ms in both views, hard 2.8 ms against 2.5–3.5 ms.
- **2×2 array DC with extracted `colout3`:** within **11 pA** of schematic at every point, with the same supply sensitivity.
- **Why it matches so closely:**
  - At DC, parasitic capacitance carries no current.
  - Wire resistance (ohms) is negligible next to megaohm nodes.
  - Transients settle in milliseconds, so femtofarads of extra capacitance don't move the loop.

## 9. What I'd do differently

- **Set the cell pitch and rail positions before placement,** so columns can be tiled by abutment instead of routed.
- **Run LVS after every routed net,** not just at the end. Each bug above was cheap to fix once found and expensive to find late.
- **Keep a numbered run log from day one.** Some early results had to be reconstructed because they weren't logged.
