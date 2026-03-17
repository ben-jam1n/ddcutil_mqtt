# Understanding Dell’s E8/E9 Multi‑Input Behavior

Dell’s multi‑input monitors (PiP/PbP modes) use two separate DDC/CI VCP codes to manage input configuration:

- **E8** — Encodes the *sub‑inputs* (slots 2, 3, and 4)
- **E9** — Selects the PiP/PbP *layout* (which windows are visible)

A key discovery is that **E8 does not encode the primary input**, and **E9 does not encode which inputs are active**. These two codes work together, but they control completely different aspects of the monitor.

This document explains how Dell actually handles multi‑input encoding, why E8 looks chaotic, and how to reliably set specific input combinations.

---

# 🔍 How the Monitor Actually Encodes Inputs

## ✔ The monitor *always* tracks three sub‑inputs internally
Even if you select a 2‑input layout, the monitor still assigns values to **all three** sub‑input slots (slots 2, 3, and 4). The layout simply hides the unused windows.

This means:

- **E8 always represents a 3‑input combination**, even in 2‑input mode
- **E9 only controls visibility**, not which inputs are active
- **The primary input is never included in E8**

### Example
These two configurations produce the *same* E8 value:

```
2 inputs: USB‑C + DP2
3 inputs: USB‑C + DP2 + HDMI2
```

Both return:

```
sh=0x4a, sl=0x53
```

Because internally, the monitor is still tracking three sub‑inputs — the layout just hides one of them.

---

# 🧠 What E8 Actually Represents

E8 is a **packed, combination‑dependent encoding** of:

- Sub‑input 2  
- Sub‑input 3  
- Sub‑input 4  

It does **not** encode:

- The primary input  
- The PiP/PbP layout  
- Window positions  
- Window sizes  
- USB routing  

This is why E8 values appear inconsistent or “random” — the encoding depends on:

- Which inputs are selected  
- How many sub‑inputs are active  
- The order of the sub‑inputs  
- Internal Dell firmware rules  

There is no formula to decode E8.  
The only reliable method is to **capture and replay** known‑good values.

---

# 🧩 What E9 Represents

E9 controls the **layout only**:

- 2‑input side‑by‑side  
- 3‑input grid  
- 4‑input quad  
- PiP small window positions  
- Etc.

E9 does **not** change the sub‑inputs.  
It only changes which windows are visible.

---

# 🛠 Setting Inputs Reliably

Because E8 always encodes all three sub‑inputs, the most reliable approach is:

1. **Choose the layout** using E9  
2. **Set all three sub‑inputs** using E8  
3. Let the layout hide the unused windows  

This guarantees:

- Stable E8 values  
- Predictable behavior  
- Accurate state detection  
- No “ghost” inputs  
- No layout‑dependent inconsistencies  

---

# 🔧 How to Set E8 Values (SH + SL)

`ddcutil` accepts a full 16‑bit value for VCP codes.

If the monitor reports:

```
sh=0x4a
sl=0x32
```

You combine them into a single 16‑bit hex value:

```
0x4a32
```

### Command format

```
ddcutil setvcp E8 0xSSLL
```

Where:

- `SS` = SH byte  
- `LL` = SL byte  

### Examples

#### Example 1 — USB‑C, HDMI2, HDMI1
```
sh=0x4a, sl=0x32
ddcutil setvcp E8 0x4a32
```

#### Example 2 — USB‑C, DP2, DP1
```
sh=0x49, sl=0xf3
ddcutil setvcp E8 0x49f3
```

#### Example 3 — USB‑C, USB‑C, DP1, HDMI2
```
sh=0x49, sl=0xfb
ddcutil setvcp E8 0x49fb
```

---

# 📦 Why This Matters

Because the monitor always encodes three sub‑inputs:

- **2‑input mode is just a layout that hides one window**
- **3‑input mode is the same encoding as 2‑input mode**
- **E8 is stable across layouts**
- **Primary input changes do not affect E8**
- **There are exactly 125 possible sub‑input combinations**  
  (5 inputs × 5 inputs × 5 inputs)

This makes it possible to build a complete preset system by capturing and replaying E8/E9 pairs.

---

# 🎯 Summary

- **E8 = sub‑input combination (slots 2–4)**  
- **E9 = layout (visibility only)**  
- **Primary input is separate**  
- **E8 always encodes 3 inputs, even in 2‑input mode**  
- **Use `ddcutil setvcp E8 0xSSLL` to set SH+SL**  
- **Build presets by capturing known‑good E8 values**  

This model is fully consistent with all observed behavior and allows complete, reliable automation of Dell PiP/PbP input control.