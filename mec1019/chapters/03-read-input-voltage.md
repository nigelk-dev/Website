# Read input voltage

Inside the microcontroller system in the
[project overview](../project-overview.qmd), the first step is **read input
voltage**: turn the scaled RES voltage on A0 into a number, and turn that number
back into the RES voltage. The second step is the **control decision**: is the
RES high enough to run the pump, or should the system switch to the battery?
This chapter covers both, using a potentiometer on the bench as a stand-in for
the RES.

```{=html}
<figure class="flow-diagram">
<figcaption>System overview · Read input voltage</figcaption>
<a class="fd-light" href="images/system-read-input-light.png"><img src="images/system-read-input-light.png" width="1600" height="370" alt="Project overview diagram with read input voltage, the 0–5 V input from voltage scaling and the control decision (RES or battery) highlighted; everything else is faded."></a>
<a class="fd-dark" href="images/system-read-input-dark.png"><img src="images/system-read-input-dark.png" width="1600" height="370" alt="Project overview diagram with read input voltage, the 0–5 V input from voltage scaling and the control decision (RES or battery) highlighted; everything else is faded."></a>
</figure>
```

## Learning outcomes

By the end of this chapter you should be able to:

- Read an analogue voltage with `analogRead` and convert the result to volts
- Make decisions from a voltage with `if`, `else if` and `else`
- Make the same decisions with whole numbers, and explain why that saves memory
- Recover the RES voltage from the divider reading
- Choose a switch-over threshold, and add hysteresis so the supply doesn't chatter

---

## 1. `analogRead`

The analogue pins (A0–A5) contain a **10-bit analogue-to-digital converter
(ADC)**: $2^{10} = 1024$ levels.

| Voltage on pin | `analogRead()` returns |
|---|---|
| 0 V | 0 |
| 2.5 V | ≈ 512 |
| 5 V | 1023 |

Convert back to volts with:

$$V = \frac{5}{1023}\times\text{reading}$$

Write the constants as `5.0` and `1023.0` (with decimal points) so C++ does
**floating-point** division: `5/1023` in whole numbers is 0!

Each step is about 4.9 mV at the pin. That is why [Voltage
regulation](01-voltage-regulation.md) scales the RES maximum to just under 5 V:
the whole range of 1024 steps is used.

---

## 2. The bench setup: a potentiometer

A **potentiometer** across 5 V gives a voltage from 0 to 5 V that you can change
by hand: a safe stand-in for the RES while you write and test the code. (See
[Voltage measurement](01-voltage-regulation.md#potentiometers-an-adjustable-divider)
for how it works.)

![Turning a breadboard potentiometer](images/p6-04.png)

All the exercises use the same connection: the pot's outer pins to **5 V** and
**GND**, its wiper to **A1**. Each LED goes from an Arduino output pin, through a
220 Ω resistor and the LED, to ground.

![Exercise 7.4 circuit: 5 kΩ pot between 5 V and GND with the wiper on A1; red, green and blue LEDs on D11, D12 and D13, each through 220 Ω to ground](images/circuit-7-4-pot-three-leds.svg)

![Breadboard wiring for Exercise 7.4: Arduino Uno pins 11, 12 and 13 run to three 220 Ω resistors and red, green and blue LEDs; the 5 kΩ pot's outer legs go to the 5 V and GND rails and its middle leg to A1](images/breadboard-7-4-pot-three-leds.svg)

| Exercise | Task | LEDs (each through 220 Ω to GND) |
|---|---|---|
| **7.1** | Read the pot voltage and print it | none |
| **7.2** | Use the pot as a dimmer for a red LED | red on **D10** (a PWM pin) |
| **7.3** | Blue LED on above 2.5 V, off below | blue on **D13** |
| **7.4** | Red for 0–2 V, green for > 2–3.5 V, blue for > 3.5–5 V | red **D11**, green **D12**, blue **D13** |

> 🔧 **Try it:** [Potentiometer applet](applets/potentiometer.html) — turn the knob and switch between Exercises 7.1 to 7.4.

---

## 3. Exercise 7.1 — read the pot voltage

```cpp
/*
 * Exercise 7.1: Read the potentiometer voltage and print it.
 * Hardware: pot outer pins to 5 V and GND, wiper to A1.
 */

const uint8_t  kPotPin   = A1;       // pot wiper
const float    kAdcVref  = 5.0;      // analogRead reference voltage (V)
const float    kAdcMax   = 1023.0;   // largest analogRead value
const uint16_t kSampleMs = 500;      // time between readings (ms)

// Read an analogue pin and return the voltage on it (0 to 5 V).
float readVolts(uint8_t pin) {
  int reading = analogRead(pin);              // 0 to 1023
  return reading * (kAdcVref / kAdcMax);      // scale to volts
}

void setup() {
  Serial.begin(9600);                // start the Serial Monitor link
  // Analogue pins are inputs by default, so no pinMode() is needed.
}

void loop() {
  float vOut = readVolts(kPotPin);   // wiper voltage
  Serial.println(vOut);              // one value per line, ideal for the Serial Plotter
  delay(kSampleMs);
}
```

Open **Tools › Serial Monitor** (or **Serial Plotter** for a live graph) and turn
the knob.

- **`readVolts(pin)`** wraps the two steps (read, then convert) in a function that
  hands back the answer with `return`. It is reused in the exercises that follow.
- **No `pinMode()`**: analogue pins start up as inputs. A common mistake is
  `pinMode(vOut, INPUT)`, which passes the *voltage variable* instead of the *pin*.

> ▶️ **[Run it: Exercise 7.1 in the code runner](applets/code-runner.html#ex2d)** — turn the simulated pot and follow `readVolts()`.

---

## 4. Exercise 7.2 — dimmer switch

```cpp
/*
 * Exercise 7.2: Use the potentiometer as a dimmer for a red LED.
 * Hardware: pot wiper to A1; red LED + 220 Ω resistor on D10 (a PWM pin).
 */

const uint8_t kPotPin = A1;     // pot wiper
const uint8_t kRedPin = 10;     // must be a PWM (~) pin

void setup() {
  pinMode(kRedPin, OUTPUT);
}

void loop() {
  int reading    = analogRead(kPotPin);                // 0 to 1023
  int brightness = map(reading, 0, 1023, 0, 255);      // rescale to 0 to 255
  analogWrite(kRedPin, brightness);                    // set the LED brightness
}
```

- `analogRead` gives **0–1023** (10 bits), but `analogWrite` takes **0–255**
  (8 bits). `analogWrite` sets an average output voltage by switching the pin on
  and off quickly (PWM); [Pump drive type](05-pump-drive-type.md) explains it in
  full, because it is how the pump is ramped up.
- **`map(value, fromLow, fromHigh, toLow, toHigh)`** rescales a number from one
  range to another: 0 → 0, 1023 → 255, 512 → 127.
- There is **no `delay()`**, so the brightness follows the knob immediately.

> ▶️ **[Run it: Exercise 7.2 in the code runner](applets/code-runner.html#ex2d1)** — turn the simulated pot and watch `map()` set the LED brightness.

---

## 5. Exercise 7.3 — switch at 2.5 V

```cpp
/*
 * Exercise 7.3: Blue LED on above 2.5 V, off at or below 2.5 V.
 * Hardware: pot wiper to A1; blue LED + 220 Ω resistor on D13.
 */

const uint8_t  kPotPin    = A1;
const uint8_t  kBluePin   = 13;
const float    kThreshold = 2.5;      // switching voltage (V)
const float    kAdcVref   = 5.0;
const float    kAdcMax    = 1023.0;
const uint16_t kSampleMs  = 500;

float readVolts(uint8_t pin) {
  return analogRead(pin) * (kAdcVref / kAdcMax);
}

void setup() {
  Serial.begin(9600);
  pinMode(kBluePin, OUTPUT);
}

void loop() {
  float vOut = readVolts(kPotPin);
  Serial.println(vOut);

  if (vOut > kThreshold) {
    digitalWrite(kBluePin, HIGH);     // above 2.5 V: LED on
  } else {
    digitalWrite(kBluePin, LOW);      // 2.5 V or below: LED off
  }

  delay(kSampleMs);
}
```

- **`if (vOut > kThreshold)`** tests a condition. If it is true, the first block
  runs; otherwise the `else` block runs. Exactly one of the two always runs.
- **`kThreshold`** is a named constant, so changing the switching point means
  editing one number.
- **Common mistake:** writing the test the wrong way round (`vOut < kThreshold` →
  HIGH) lights the LED *below* 2.5 V instead of above it.

This **threshold** is exactly what the project uses for its control decision:
replace the blue LED with "use the RES".

> ▶️ **[Run it: Exercise 7.3 in the code runner](applets/code-runner.html#ex2d2)** — move the pot either side of 2.5 V and see which branch runs.

---

## 6. Exercise 7.4 — three voltage bands

```cpp
/*
 * Exercise 7.4: Show which voltage band the pot is in.
 *   0 to 2 V     -> red LED
 *   >2 to 3.5 V  -> green LED
 *   >3.5 to 5 V  -> blue LED
 * Hardware: pot wiper to A1; LEDs + 220 Ω resistors on D11, D12, D13.
 */

const uint8_t  kPotPin   = A1;
const uint8_t  kRedPin   = 11;
const uint8_t  kGreenPin = 12;
const uint8_t  kBluePin  = 13;
const float    kLowMax   = 2.0;       // top of the red band (V)
const float    kMidMax   = 3.5;       // top of the green band (V)
const float    kAdcVref  = 5.0;
const float    kAdcMax   = 1023.0;
const uint16_t kSampleMs = 500;

float readVolts(uint8_t pin) {
  return analogRead(pin) * (kAdcVref / kAdcMax);
}

// Turn each LED on (true) or off (false) in one call.
void setLeds(bool red, bool green, bool blue) {
  digitalWrite(kRedPin,   red   ? HIGH : LOW);
  digitalWrite(kGreenPin, green ? HIGH : LOW);
  digitalWrite(kBluePin,  blue  ? HIGH : LOW);
}

void setup() {
  Serial.begin(9600);
  pinMode(kRedPin, OUTPUT);
  pinMode(kGreenPin, OUTPUT);
  pinMode(kBluePin, OUTPUT);
}

void loop() {
  float vOut = readVolts(kPotPin);
  Serial.println(vOut);

  if (vOut <= kLowMax) {
    setLeds(true, false, false);      // 0 to 2 V: red only
  } else if (vOut <= kMidMax) {
    setLeds(false, true, false);      // above 2 V, up to 3.5 V: green only
  } else {
    setLeds(false, false, true);      // above 3.5 V: blue only
  }

  delay(kSampleMs);
}
```

- **`if ... else if ... else`** checks the conditions in order and runs **only the
  first one that is true**. By the time the `else if` is tested, we already know
  the voltage is above 2 V, so there is no need to test that again.
- Because only one branch runs, exactly one LED is ever lit.

| Operator | Meaning |
|---|---|
| `<`, `<=`, `>`, `>=` | less than, less or equal, greater, greater or equal |
| `==` | equal to (two `=`!) |
| `&&` | AND — both conditions true |
| `\|\|` | OR — either condition true |

> ▶️ **[Run it: Exercise 7.4 in the code runner](applets/code-runner.html#ex2e)** — move the pot through the three bands and watch the `else if` chain.

---

## 7. Do you need a `float`?

Exercise 7.4 converts every reading into volts (a `float`) and then compares the
volts with 2.0 and 3.5. The decision only needs to know **which band** the pot
is in, and that can be decided from the whole-number `analogRead` value. Convert
the two **thresholds** into `analogRead` values once, instead of converting
**every reading** into volts.

| Threshold | Volts | As an `analogRead` value ($V \times 1023 / 5$) |
|---|---|---|
| Top of the red band | 2.0 V | 409 |
| Top of the green band | 3.5 V | 716 |

```cpp
// Thresholds as analogRead values, in millivolts so the sums stay whole numbers.
// The compiler works these out once, when you press Verify.
const int kLowMax = 2000L * 1023 / 5000;    // 2.0 V -> 409
const int kMidMax = 3500L * 1023 / 5000;    // 3.5 V -> 716

void loop() {
  int reading = analogRead(kPotPin);        // 0 to 1023: no conversion
  if (reading <= kLowMax) {
    setLeds(true, false, false);
  } else if (reading <= kMidMax) {
    setLeds(false, true, false);
  } else {
    setLeds(false, false, true);
  }
  delay(kSampleMs);
}
```

**Why it is worth it.** The ATmega328P has no hardware for decimal maths. As soon
as a sketch uses a `float`, the compiler adds a library of software routines to
program memory, and every `float` sum runs many times slower than whole-number
maths. A `float` also takes 4 bytes of RAM where an `int` takes 2.

| Exercise | Flash used, `float` | Flash used, integer | Saved |
|---|---|---|---|
| 7.1 | 3 780 bytes | 2 690 bytes | **1 090 bytes** (29%) |
| 7.3 | 3 890 bytes | 2 648 bytes | **1 242 bytes** (32%) |
| 7.4 | 3 982 bytes | 2 726 bytes | **1 256 bytes** (32%) |

- **The `L`** makes 2000 a `long`, because 2000 × 1023 (about 2 million) is too
  big for a 2-byte `int` (maximum 32 767).
- Multiply **first**, then divide: `reading / 1023 * 5000` would throw the
  fraction away straight away and give only 0 or 5000.

> ✅ **Rule of thumb:** make decisions on whole numbers (`analogRead` values or
> millivolts). Use a `float` only when you really need a fraction, and convert to
> volts only when a person has to read the value.

> ▶️ **[Run it: the integer version in the code runner](applets/code-runner.html#ex2eint)** — the Variables panel shows the raw `reading` being compared with 409 and 716.

---

## 8. From the reading back to the RES voltage

On the project, A0 sees the RES voltage scaled down by the divider. To get the
real RES voltage, run the divider backwards: divide the pin voltage by the
divider's fraction $k = R_2/(R_1+R_2)$.

```cpp
/*
 * Measure the RES voltage through a voltage divider.
 * Divider: R1 = 22 kΩ (top), R2 = 10 kΩ (bottom); mid-point to A0.
 * The RES negative and the Arduino GND must be connected together.
 */

const uint8_t  kResPin   = A0;         // divider mid-point
const float    kR1       = 22000.0;    // top resistor (Ω)
const float    kR2       = 10000.0;    // bottom resistor (Ω)
const float    kRatio    = kR2 / (kR1 + kR2);   // fraction of the RES voltage at the pin: 0.3125
const float    kAdcVref  = 5.0;
const float    kAdcMax   = 1023.0;
const uint16_t kSampleMs = 200;

void setup() {
  Serial.begin(9600);
}

void loop() {
  int   reading = analogRead(kResPin);            // 0 to 1023
  float vPin    = reading * (kAdcVref / kAdcMax); // voltage at the A0 pin
  float vRes    = vPin / kRatio;                  // undo the divider: the real RES voltage

  Serial.print("A0: ");                  // prints e.g. "A0: 3.91 V   RES: 12.51 V"
  Serial.print(vPin);
  Serial.print(" V   RES: ");
  Serial.print(vRes);
  Serial.println(" V");
  delay(kSampleMs);
}
```

With the RES at 12.5 V as an example:

| Step | Line | Example |
|---|---|---|
| 1. The divider scales the RES voltage down | `kRatio = kR2 / (kR1 + kR2)` | 10 000 ÷ 32 000 = 0.3125, so the pin sees 12.5 × 0.3125 = 3.91 V |
| 2. The ADC turns the pin voltage into a number | `analogRead(kResPin)` | 3.91 ÷ 5 × 1023 ≈ 800 |
| 3a. Convert the number back to the pin voltage | `reading * (kAdcVref / kAdcMax)` | 800 × 5 ÷ 1023 = 3.91 V |
| 3b. Undo the divider | `vPin / kRatio` | 3.91 ÷ 0.3125 = 12.5 V |

**Share the ground.** The RES −ve and the Arduino GND must be connected. A
voltage is always measured *relative to* something: without a shared ground,
`analogRead` has no reference and returns meaningless values.

> ▶️ **[Run it in the code runner](applets/code-runner.html#p5res)** — move the RES voltage slider and follow the reading back to the source voltage.

### Measure the fraction

Resistor tolerances, or an adjustable divider
([Voltage measurement](01-voltage-regulation.md#setting-an-adjustable-divider-safely)),
mean the real fraction can differ from the calculated one. Measure it instead:

1. Apply a known voltage across the divider, e.g. 12.0 V from a bench supply,
   measured with a multimeter.
2. Measure the voltage at the divider's output (the analogue pin), e.g. 3.60 V.
3. $k = 3.60 / 12.0 = 0.300$. Put that in the code as `const float kRatio = 0.300;`.

If the divider uses a trimmer, measure again whenever it is moved.

---

## 9. The control decision: RES or battery

The decision is Exercise 7.3 with the LED replaced by the supply: if the RES is
high enough, use it; otherwise use the battery. The functions `useRes()` and
`useBattery()` switch the supplies; [Switching
circuitry](04-switching-circuitry.md) writes them for the relay module.

```cpp
if (vPin < kThresholdV) {
  useBattery();                // RES voltage has dropped
} else {
  useRes();                    // RES is fine
}
```

### Choosing the threshold

Start from the **minimum RES voltage the pump needs** to run properly, then scale
it through the divider to get the threshold at the pin:

$$V_{pin} = k\,V_{RES} \qquad\Longleftrightarrow\qquad V_{RES} = \frac{V_{pin}}{k}$$

With $R_1 = 2.172R_2$ ($k = 1/3.172$), a threshold of 2.5 V at the pin means the
system switches at $2.5 \times 3.172 \approx 7.9$ V at the RES. Setting the threshold
too close to 5 V (say 4.8 V) means the RES is used only when it is within about
4 % of its maximum, which wastes most of the renewable energy.

### Hysteresis: stop the chatter

If the RES voltage hovers right at the threshold (a gusty wind turbine, a cloud
passing the panel), a single threshold flips the supply back and forth on every
reading. Relays wear out, and the pump is repeatedly hit with a new supply. Use
two thresholds:

```cpp
const float kToBatteryV = 2.3;   // switch to the battery below this
const float kToResV     = 2.7;   // switch back to the RES only above this

void loop() {
  float vPin = readVolts(kResPin);

  if (vPin < kToBatteryV) {
    useBattery();                // clearly too low
  } else if (vPin > kToResV) {
    useRes();                    // clearly recovered
  }
  // Between 2.3 and 2.7 V neither branch runs, so the supply stays as it is.

  delay(kSampleMs);
}
```

- With one threshold at 2.5 V, a reading that wobbles 2.49 → 2.51 → 2.49 switches
  every time.
- With two thresholds there is a **dead band** from 2.3 V to 2.7 V. Inside it,
  nothing changes, so the pump stays on whichever supply it already had.
- This is the same idea as a home thermostat, which doesn't switch the heating on
  and off at exactly one temperature.

> 🔧 **Try it:** [RES battery-backup simulator](applets/res-backup.html) — tick "Gusty", put the wind around the threshold and watch the supply switch; then think about how hysteresis would help.

---

## Key points

- `analogRead` returns 0–1023 for 0–5 V; convert with `reading * (5.0 / 1023.0)`.
- `if / else if / else` turns a voltage into decisions; only the first true branch
  runs.
- Decide on whole-number `analogRead` values where you can: convert the thresholds
  once, and use `float` volts only for display. It saves over 1 KB of flash.
- Divide the pin voltage by the divider fraction $k$ to recover the RES voltage.
  Measure $k$ with a multimeter rather than trusting the resistor values.
- Choose the threshold from the pump's minimum voltage, scaled through the divider,
  and add **hysteresis** so the supply doesn't chatter.
