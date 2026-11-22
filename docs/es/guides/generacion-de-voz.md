# Generación de voz con Aurora

Estado: integración multiproveedor implementada. La aceptación de síntesis remota y la importación del audio en Resolve se verifican por separado del catálogo y del despliegue.

## Recorrido de la app

1. En **Ajustes → Cuenta de Aurora**, inicia sesión mediante Google o Discord. El navegador autentica y vuelve a Ajustes.
2. La cuenta muestra el acceso y los créditos disponibles; el acceso interno verificado no consume créditos. Abre **Generación de voz** para elegir proveedor/modelo y después su voz. Si falta iniciar sesión, **Ir a Ajustes** abre la cuenta. La prueba gratuita usa el saldo existente; DaVinci Flow no concede una cantidad fija de créditos.
3. Escribe el guion y elige una voz. La estimación usa la tarifa activa de Aurora. El servidor vuelve a comprobar cuenta, suscripción o prueba y saldo antes de generar.
4. Pulsa **Generar voz**. El audio se guarda en disco y puede escucharse sin salir de la app.
5. Pulsa **Importar a Resolve** para incorporarlo al Media Pool del proyecto activo, en **DaVinci Flow · Voces**. No se coloca automáticamente en la línea de tiempo.

Si se pierde la respuesta, **Recuperar generación** busca esa misma solicitud; no inicia otra síntesis ni repite el cobro. Un fallo de importación conserva el audio. **Seleccionar audio** permite traer un archivo descargado previamente de Voice Studio.

**Voice Studio web** sigue disponible como acceso complementario. El diseño principal es la generación dentro de la app.

## Cuenta y retorno nativo

El adaptador Python conserva el contrato de login Provider/PKCE utilizado por Ely Intelligence y Aurora Hub: navegador del sistema, prueba criptográfica, canje de un solo uso, identidad verificada y renovación serializada. La bóveda Windows usa DPAPI; no existe respaldo de tokens en texto plano.

| Entorno | Retorno web base | Esquema de retorno |
| --- | --- | --- |
| Instalado | `https://biglexj.com/auth/native-return?app=davinciflow` | `davinciflow://auth/callback` |
| Desarrollo | `https://biglexj.com/auth/native-return?app=davinciflow-dev` | `davinciflow-dev://auth/callback` |

Cada intento añade `flow=<nonce>` al retorno. El puente entrega únicamente `code` y `flow`; la app rechaza otro entorno, intentos anteriores, tokens en URL, parámetros duplicados y pruebas caducadas. Los dos retornos con `flow` deben estar admitidos por la configuración del proveedor antes de la aceptación real. No registrar un dominio nuevo como `davinciflow.com` ni reutilizar el identificador de otra aplicación.

Al comenzar el login, Windows registra únicamente el protocolo del entorno actual, bajo el usuario actual. El proceso de retorno despierta la instancia correspondiente al mismo checkout. La sesión y los datos de desarrollo permanecen separados de la instalación estable.

El cierre de sesión limpia guion, selección de voz, reproductor y credenciales de esta app; conserva los audios exportados. Si falla la revocación remota, la app distingue ese fallo del borrado local.

## Acceso y consumo en Aurora

La operación preparada es `/api/creador/voice-studio/native`:

- `GET ?action=config`: configuración pública de autenticación, sin claves privilegiadas.
- `GET ?action=access`: identidad, prueba/suscripción, saldo y catálogo versión 2, con motores, tarifas por motor, voces y disponibilidad real del servicio.
- `POST`: solicitud con UUID, guion, proveedor, voz y límite de consumo aceptado. No acepta identidad, permisos ni precios del cliente como autoridad.
- `GET ?action=result&request_id=...`: recupera exclusivamente una solicitud del usuario autenticado.

Se consultan en servidor las tablas actuales de cuenta, suscripciones, planes, tarifas y créditos de Aurora. La prueba admite cuentas gratuitas activas con saldo existente; una suscripción de Creador vigente da el acceso correspondiente. Un rol de Creador guardado sin suscripción vigente no lo sustituye. Las excepciones internas se deciden con el rol administrativo verificado en servidor.

La tarifa procede del servicio de cada motor: `voice_piper`, `voice_pocket_tts`, `voice_gemini_cloud`, `voice_xtts_clone` o `voice_minimax`, con su unidad activa de 100 o 200 caracteres. No se mantiene una tabla local de precios. Si la tarifa supera el límite estimado aceptado por el cliente, se detiene antes de sintetizar y se pide actualizar el acceso. Un motor sin tarifa activa queda bloqueado para cuentas externas; una cuenta interna verificada puede usarlo sin consumo. No se crea una tarifa de MiniMax por semejanza con otro proveedor.

La interfaz separa **Proveedor / modelo** y **Voz**. Aurora devuelve Piper, Pocket TTS, Gemini Cloud, Qwen y MiniMax, usando el catálogo de Voice Studio. El segundo selector muestra únicamente voces compatibles y preparadas del motor elegido; los motores no disponibles se indican y no permiten generar. El modelo concreto de síntesis lo decide el servicio, sin una lista independiente de modelos inventada por el cliente. Las voces clonadas privadas se consultan y leen exclusivamente para su propietario; la prueba gratuita no las habilita. Si el almacenamiento privado no está configurado, se informa sin bloquear los otros motores. Al cerrar sesión se vacían ambas selecciones.

**Voces del sistema · Gratis** utiliza las voces realmente instaladas de Windows mediante System.Speech y exporta un WAV local. No carga motores de IA en el arranque ni consume créditos de Aurora. Conserva el mismo recorrido de escucha e importación y requiere una cuenta iniciada. El catálogo remoto se consulta al abrir o actualizar la sección; un servidor antiguo que solo devuelve Gemini se identifica explícitamente.

Cada UUID reserva un registro en `voice_synthesis_jobs` antes de llamar al proveedor. Tras validar el WAV y la identidad del proveedor y la voz se usa `deduct_user_credits`, sin fallback de escritura de saldo. El ledger identifica la solicitud y permite recuperar un débito de respuesta incierta. El archivo de una solicitud no se revela al cliente antes del consumo confirmado. No hay cambios silenciosos de proveedor; la recuperación conserva el motor y la voz incluso tras reiniciar la app.

Se reutilizan el almacenamiento TTS y el historial de Aurora. En el cliente, audios y registros locales quedan bajo el directorio aislado de datos, separados por cuenta.

Fuentes: [Acceso y seguridad de Aurora](../../../../Aurora---Blog/docs/es/auth/acceso-y-seguridad.md), [Catálogo comercial y créditos](../../../../Aurora---Blog/docs/es/servicios/catalogo-y-creditos.md) y [autenticación nativa Core](../../../../Docs/features/authentication/native-desktop-auth.md).

## Habilitación pendiente

El estado y la evidencia del despliegue se registran en [VALIDATION](../../../process/active/2026-11-10_voz-aurora-login/VALIDATION.md). La duración permitida del despliegue debe cubrir la síntesis y el guardado; las pruebas locales no acreditan ese límite remoto, especialmente para solicitudes largas de Qwen.

La ruta canónica antigua de Voice Core continúa teniendo su contrato para otros consumidores. Antes de abrir monetización pública debe coordinarse su paso a operaciones con medición, evitando dejar una ruta alternativa sin consumo. No se modifica de forma incidental el comportamiento de Ely Intelligence o Aurora Hub durante esta entrega.

Las pruebas con datos simulados no acreditan síntesis remota, cobro real ni importación nativa en Resolve. La consulta del catálogo con una sesión real y la exportación local de Windows se registran aparte. No se ha publicado ni instalado una actualización estable de DaVinci Flow.

## Tipografías de los títulos

Los títulos siguen el [branding y la regla de producción Core](../../../../Docs/guides/cross-platform/editors/davinci-resolve-produccion.md). Kefa queda reservada para karaoke; los nuevos diseños Ely usan Thunder para principal, Open Sans para contexto y Tilt Warp para acentos. Las referencias existentes conservan su diseño hasta preparar explícitamente una copia adaptada.
