# Roadmap / Pendientes

## Antes de publicar en GitHub / Before publishing

- [ ] **Depurar / Debug**
  - [ ] Quitar rutas/hardcodes específicos de la máquina actual (nombres de sink ya se
        detectan dinámicos — revisar que no quede ninguno).
  - [x] i18n con detección de idioma (ES/EN) — hecho.
  - [ ] Probar en una máquina limpia (sin `~/.config/anthrophonic/` previo).
  - [ ] Manejar casos: sin BT, sin HDMI, BT que se desconecta mientras suena.
  - [ ] Errores claros si falta `numpy`, `paplay`, `pw-dump`.
  - [ ] Revisar fugas: procesos `paplay` del pulso al cerrar / al fallar.

- [ ] **Idioma / i18n**
  - [ ] Detectar idioma del sistema (`locale` / `$LANG`) y mostrar ES o EN.
  - [ ] Fallback a inglés si el idioma no está soportado.
  - [ ] Extraer todos los textos de la GUI a un diccionario `STRINGS = {"es": {...}, "en": {...}}`.

- [ ] **Empaquetado / Packaging**
  - [ ] `install.sh` robusto (comprobar dependencias, instalar `.desktop`).
  - [ ] Icono propio en vez de `audio-volume-high`.
  - [ ] Captura `docs/panel.png` para el README.

## Ideas futuras / Future ideas

- [ ] Recordar `extra` por dispositivo BT (MAC) para varios cascos.
- [ ] Sincronía por dispositivo display en HDMI (varias TVs).
- [ ] Modo bandeja / tray icon.
- [ ] Empaquetar como Flatpak o `.deb`.
