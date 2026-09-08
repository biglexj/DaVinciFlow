# 🎬 ¡Lanzamiento de DaVinci Flow v0.3.0!

Nos complace presentar **DaVinci Flow v0.3.0**, una gran evolución arquitectónica que reestructura por completo la suite bajo los principios de **Screaming Architecture** y el patrón desacoplado tipo **Tauri**, optimizando la automatización audiovisual en **DaVinci Resolve 21**.

---

### ✨ ¿Qué hay de nuevo en la v0.3.0?
**DaVinci Flow v0.3.0** separa nítidamente el motor de automatización de la interfaz gráfica moderna en **Flet**, consolidando la ejecución en un único entorno de alto rendimiento basado en **CPython 3.13** de 64 bits gestionado por **uv**.

---

### 🚀 Novedades Destacadas

1. **🏛️ Reestructuración Desacoplada (Patrón Tauri & Screaming Architecture)**:
   - Separación en dos raíces complementarias: un motor core headless (`src/davinci_flow/`) puro y comprobable, y una interfaz gráfica moderna (`src-flet/`) estructurada por dominios de usuario (`features/editor`, `features/catalog`, `features/library`, `features/settings`).

2. **⚡ Consolidación de Entorno Único con uv en CPython 3.13**:
   - Unificación de dependencias en un solo `.venv` oficial de 64 bits.
   - Eliminación total de fragmentaciones de intérpretes, logrando que la interfaz Flet y la API de DaVinci Resolve convivan de forma directa, rápida y estable.

3. **🔄 Lanzador No Bloqueante en DaVinci Resolve**:
   - Apertura fluida como proceso independiente desde **Área de trabajo → Secuencias de comandos → DaVinci Flow**, manteniendo el espacio de trabajo de DaVinci Resolve 100% responsivo sin congelamientos.

4. **🧪 Calidad y Robustez Verificada**:
   - 180 pruebas unitarias automatizadas superadas con éxito y scripts de lanzamiento directo (`scripts/start-desktop.ps1`).

---

### 📦 Instalación y Uso Rápido

1. Sincroniza e instala el lanzador en DaVinci Resolve:
   ```bash
   uv sync
   uv run davinci-flow --install
   ```
2. Inicia la aplicación desde la raíz:
   ```powershell
   .\scripts\start-desktop.ps1
   ```
3. O en **DaVinci Resolve**, accede desde el menú superior:
   **Área de trabajo -> Secuencias de comandos -> DaVinci Flow**.

---

### 🌐 Ecosistema & Donaciones
- **Launchpad Web**: [https://biglexj.com/desarrollo](https://biglexj.com/desarrollo)
- **Apoya el Desarrollo**: [https://biglexj.com/donaciones](https://biglexj.com/donaciones)
- **Código y Comunidad**: MIT License • Biglex J (2026)
