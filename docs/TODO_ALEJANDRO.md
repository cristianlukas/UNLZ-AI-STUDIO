# TODO Alejandro Navas - Instalabilidad y Funcionamiento de Modulos

Fecha: 2026-05-23

## Objetivo
Garantizar que la app se pueda instalar y ejecutar de forma reproducible en un entorno limpio, y que cada modulo principal funcione en su flujo minimo esperado.

## Criterio de Aprobacion General
- [ ] Instalacion completa sin pasos manuales ocultos.
- [ ] Arranque de app (UI normal y web) sin errores bloqueantes.
- [ ] Cada modulo del alcance con smoke test en estado `OK` o `OK con observaciones`.
- [ ] Todo error grave queda con owner y accion concreta.

## Bloque A - Instalabilidad (Prioridad Maxima)

## A1. Preflight de entorno
- [ ] Definir entorno de prueba limpio (sin dependencias previas del proyecto).
- [ ] Verificar prerequisitos documentados (Python/Node/drivers/GPU segun aplique).
- [ ] Confirmar permisos de escritura en rutas usadas por modelos y logs.

## A2. Instalacion base
- [ ] Ejecutar instalacion principal (`install.bat`) y registrar resultado.
- [ ] Validar creacion de archivos/carpetas esperadas de runtime.
- [ ] Verificar que no falle por dependencias faltantes no documentadas.

## A3. Arranque de aplicaciones
- [ ] Probar arranque UI normal (`start_normal_ui.bat`).
- [ ] Probar arranque UI web (`start_web_ui.bat` y `system/run_web_ui.bat`).
- [ ] Confirmar que ambos modos levantan sin crash inicial.

## A4. Consistencia de perfiles/modelos
- [ ] Validar modelo bajo/CPU en `readme.md`, `system/runtime_profiles.py`, `system/process_manager.py`.
- [ ] Confirmar que la referencia final sea consistente con `Qwen2.5-Coder-7B-Instruct`.
- [ ] Verificar comandos de instalacion y rutas de GGUF probados en entorno limpio.

## A5. Higiene de repo para instalabilidad
- [ ] Quitar artefactos generados del versionado (`.next`, `__pycache__`, `.pyc`, `.lnk` no-release).
- [ ] Ajustar `.gitignore` para prevenir reingreso.
- [ ] Confirmar que un clon nuevo no arrastre basura de build.

## Bloque B - Funcionamiento por Modulo

## B0. Regla de prueba por modulo
Para cada modulo:
- [ ] Abre correctamente desde la UI.
- [ ] Ejecuta una accion principal de punta a punta.
- [ ] Maneja error esperable sin romper la app.
- [ ] Queda evidencia (log corto + resultado).

## B1. monitor
- [ ] Verificar estado de servicios y deteccion de modelo recomendado.
- [ ] Confirmar feedback claro cuando falta modelo/dependencia.

## B2. llm_frontend
- [ ] Cargar GGUF valido y responder un prompt simple.
- [ ] Confirmar compatibilidad con perfil bajo/CPU.

## B3. vlm_frontend
- [ ] Cargar modulo y ejecutar inferencia visual minima.
- [ ] Verificar mensajes de error legibles si falta backend.

## B4. model_3d
- [ ] Probar arranque del modulo y flujo minimo (estado/tarea).
- [ ] Validar que no bloquee la UI ante fallos de descarga.

## B5. ml_sharp
- [ ] Ejecutar flujo minimo y comprobar salida esperada.
- [ ] Validar fallback cuando faltan dependencias.

## B6. neutts
- [ ] Generar audio de prueba desde texto.
- [ ] Verificar integracion de `view.py` con `neutts_espeak.py`.

## B7. spotedit
- [ ] Probar flujo principal de edicion/procesamiento.
- [ ] Confirmar manejo de errores de entrada/salida.

## B8. hy_motion
- [ ] Ejecutar accion principal del modulo.
- [ ] Validar estabilidad de UI durante el proceso.

## B9. hyworld
- [ ] Ejecutar accion principal del modulo.
- [ ] Validar estabilidad de UI durante el proceso.

## B10. cyberscraper
- [ ] Probar flujo minimo de consulta/extraccion.
- [ ] Verificar respuesta controlada ante fallo de red/fuente.

## B11. scenema_audio
- [ ] Verificar presencia en `system/installed_modules.json`.
- [ ] Validar integracion desktop/web (`system/studio_gui.py`, `system/web_bridge.py`).
- [ ] Probar vista web `system/web_ui/src/app/modules/scenema_audio/page.tsx` y enlace externo.

## Bloque C - Cierre y Entrega

## C1. Reporte de estado por modulo
- [ ] Registrar por modulo: `OK | OK con observaciones | Bloqueado`.
- [ ] Para bloqueados: owner, causa raiz, siguiente accion, ETA.

## C2. Criterio de cierre
- [ ] Sin bloqueantes de instalacion.
- [ ] Sin modulos criticos en estado `Bloqueado`.
- [ ] Documentacion de instalacion actualizada y validada con prueba real.
