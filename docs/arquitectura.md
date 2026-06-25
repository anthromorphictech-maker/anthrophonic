# Arquitectura / Architecture

## Grafo de audio / Audio graph

```
  apps (Chrome, etc.)
        │
        ▼
  [ null-sink "combinado" ]  ← salida por defecto / default sink
        │ .monitor
        ├── loopback ──(latency_msec=60)──▶  Bluetooth   (referencia / reference)
        ├── loopback ──(latency_msec=D_a)─▶  Analógico   (cable / wired)
        └── loopback ──(latency_msec=D_h)─▶  HDMI        (cable / wired)
```

- `module-null-sink` central: las apps reproducen aquí.
- Un `module-loopback` por salida activa, desde `combinado.monitor` al sink físico.
- `latency_msec` del loopback = retardo real añadido a esa rama.

## Modelo de sincronía / Sync model

El Bluetooth es la salida más lenta (referencia). Cada salida de cable se retrasa para
emitir al mismo tiempo que el BT:

```
D[cable] = (latencia_BT - latencia_cable) + extra[cable]
```

- `latencia_X` = lo que PipeWire reporta en `pw-dump` (`Latency.Input.maxNs`, ns→ms).
  El cable suele dar 0; el BT da el buffer A2DP (~140 ms).
- `extra[cable]` = retardo **oculto** que PipeWire no ve (decodificación + DAC del casco BT,
  ~190 ms típico). Se **aprende** cuando ajustas a mano:
  `extra = D_manual - (latencia_BT - latencia_cable)`.
- El BT mantiene `latency_msec=60` (keepalive: evita que el sink BT se suspenda en silencio).

Cada salida de cable guarda su propio `extra` (HDMI a TV suele diferir del analógico).

## Persistencia / Persistence

`~/.config/anthrophonic/`
- `delays.json`  — `{sink: ms}` retardo de loopback por salida.
- `offsets.json` — `{sink: ms}` extra aprendido por salida.
- `pulse.wav`   — tren de clics generado para afinar (con sustain anti-suspensión BT).

## Por qué no auto-total / Why not fully automatic

El retardo que domina vive **dentro del casco BT** (decodificación + DAC), y PipeWire no lo
expone. Medirlo acústicamente tampoco vale: el casco está en tus oídos, el micro no lo oye.
Por eso `extra` se aprende una vez por dispositivo (es constante por casco) y luego `auto`
ya clava el valor.

The dominant delay lives **inside the BT headset** and PipeWire doesn't expose it. Acoustic
measurement won't work either (the headset is on your ears, the mic can't hear it). So `extra`
is learned once per device (constant per headset); after that `auto` nails it.
