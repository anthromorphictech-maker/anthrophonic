# Architecture

## Audio graph

```
  apps (Chrome, etc.)
        │
        ▼
  [ null-sink "combinado" ]  ← default sink
        │ .monitor
        ├── loopback ──(latency_msec=60)──▶  Bluetooth   (reference)
        ├── loopback ──(latency_msec=D_a)─▶  Analog      (wired)
        └── loopback ──(latency_msec=D_h)─▶  HDMI        (wired)
```

- A central `module-null-sink`: apps play here.
- One `module-loopback` per active output, from `combinado.monitor` to the physical sink.
- The loopback's `latency_msec` = real delay added to that branch.

## Sync model

Bluetooth is the slowest output (the reference). Each wired output is delayed so it emits at
the same time as BT:

```
D[wired] = (latency_BT - latency_wired) + extra[wired]
```

- `latency_X` = what PipeWire reports in `pw-dump` (`Latency.Input.maxNs`, ns→ms). Wired usually
  reports 0; BT reports its A2DP buffer (~140 ms).
- `extra[wired]` = the **hidden** delay PipeWire can't see (decode + DAC inside the BT headset,
  ~190 ms typical). It is **learned** when you tune by hand:
  `extra = D_manual - (latency_BT - latency_wired)`.
- BT keeps `latency_msec=60` (keepalive: stops the BT sink from suspending on silence).

Each wired output stores its own `extra` (HDMI to a TV often differs from analog).

## Persistence

`~/.config/anthrophonic/`
- `delays.json`  — `{sink: ms}` loopback delay per output.
- `offsets.json` — `{sink: ms}` learned extra per output.
- `pulse.wav`    — generated click train for tuning (with a faint sustain that keeps BT awake).

## Why not fully automatic

The dominant delay lives **inside the BT headset** (decode + DAC) and PipeWire doesn't expose
it. Acoustic measurement won't work either: the headset is on your ears, the mic can't hear it.
So `extra` is learned once per device (constant per headset); after that `auto` nails it.
