"""Entrada de diagnóstico, planificación, instalación y generación para DaVinci Flow."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from davinci_flow.application import (
    align_and_correct_subtitles,
    generate_from_active_timeline,
    insert_ai_timeline_markers,
    plan_active_subtitles,
    reconcile_active_timeline,
    scan_active_subtitles,
)
from davinci_flow.errors import DaVinciFlowError
from davinci_flow.installer import (
    install_resolve_launcher,
    uninstall_resolve_launcher,
)
from davinci_flow.ai.aligner import parse_glossary_str
from davinci_flow.ui import open_davinci_flow_ui


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="davinci-flow",
        description="DaVinci Flow — Automatización de subtítulos dinámicos multicapa, guion y SFX.",
    )
    parser.add_argument("--editorial-ui", action="store_true", help="Abre el editor LLM sin conectar con Resolve.")
    parser.add_argument("--track", type=int, default=1, help="Índice de pista, comenzando en 1.")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Cantidad máxima de bloques que se muestran; usa 0 para mostrarlos todos.",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Ejecuta la clasificación determinista en capas y muestra el plan de generación.",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Genera las capas de títulos y SFX en pistas dedicadas de la línea de tiempo.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la generación y muestra los clips que se crearían sin modificar Resolve.",
    )
    parser.add_argument(
        "--no-sfx",
        action="store_true",
        help="Desactiva la propuesta e inserción de efectos sonoros (SFX).",
    )
    parser.add_argument(
        "--theme",
        type=str,
        default="ely",
        choices=["ely", "aurora"],
        help="Tema visual para la generación (por defecto: ely).",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="natural",
        choices=["reflexivo", "natural", "dinamico", "educativo", "video_corto"],
        help="Perfil editorial (por defecto: natural).",
    )
    parser.add_argument(
        "--script",
        type=str,
        default="",
        metavar="PATH_OR_TEXT",
        help="Guion original para comparar y corregir los subtítulos transcritos.",
    )
    parser.add_argument(
        "--glossary",
        type=str,
        default="",
        metavar="GLOSSARY_KV",
        help="Glosario de reemplazos de marcas/jergas (ej: 'biglex: Biglex J, resolve: DaVinci').",
    )
    parser.add_argument(
        "--gemini-key",
        type=str,
        default=None,
        metavar="KEY",
        help="Clave API de Google Gemini (o usar variable de entorno GEMINI_API_KEY).",
    )
    parser.add_argument(
        "--gemini-model",
        type=str,
        default="gemini-3.6-flash",
        metavar="MODEL",
        help="Modelo de Google Gemini a utilizar (por defecto: gemini-3.6-flash).",
    )
    parser.add_argument(
        "--correct-ai",
        action="store_true",
        help="Habilita la alineación y corrección contextual con Google Gemini.",
    )
    parser.add_argument(
        "--add-markers",
        action="store_true",
        help="Inserta marcadores en puntos clave importantes en la línea de tiempo de Resolve.",
    )
    parser.add_argument(
        "--srt",
        type=str,
        default=None,
        metavar="SRT_PATH",
        help="Ruta a un archivo .srt para procesar subtítulos directamente.",
    )
    parser.add_argument(
        "--export-plan",
        type=str,
        default=None,
        metavar="PATH",
        help="Ruta de archivo JSON donde guardar el plan de generación calculado.",
    )

    parser.add_argument(
        "--reconcile",
        type=str,
        default=None,
        metavar="PLAN_PATH",
        help="Compara los subtítulos actuales contra un plan JSON previo para regeneración selectiva.",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Instala DaVinci Flow en el menú Scripts de DaVinci Resolve.",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Desinstala DaVinci Flow del menú Scripts de DaVinci Resolve.",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Abre la ventana gráfica de DaVinci Flow en DaVinci Resolve.",
    )
    parser.add_argument(
        "--about",
        action="store_true",
        help="Muestra información de versión, autoría y enlaces de apoyo oficial.",
    )
    return parser


def _load_script_text(script_arg: str) -> str:
    """Carga el texto del guion desde un archivo en disco o lo toma como texto plano directo."""
    if not script_arg or not script_arg.strip():
        return ""
    p = Path(script_arg.strip())
    if p.is_file():
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            pass
    return script_arg.strip()


def print_about() -> None:
    """Muestra información del proyecto y enlaces oficiales."""
    print("╔═════════════════════════════════════════════════════════════╗")
    print("║                       DaVinci Flow                          ║")
    print("║   Subtítulos Dinámicos, Guion & Asistente IA (Gemini Engine)║")
    print("║                     Versión 0.1.0 • MIT                     ║")
    print("╚═════════════════════════════════════════════════════════════╝")
    print("👤 Autor: biglexj (2026)")
    print("🌐 Web Oficial & Donaciones: https://www.biglexj.com/donaciones")
    print("☕ Buy Me a Coffee: https://buymeacoffee.com/biglexj")
    print("🐙 GitHub: https://github.com/biglexj\n")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.editorial_ui:
        from davinci_flow.ui.editorial_window import open_editorial_window
        open_editorial_window()
        return 0

    if args.about:
        print_about()
        return 0

    if args.install:
        launcher_path = install_resolve_launcher()
        print(f"✅ ¡DaVinci Flow instalado con éxito en DaVinci Resolve!")
        print(f"📁 Ubicación del lanzador: {launcher_path}")
        print("💡 Para abrir la pestaña interna:")
        print("   1. Abre DaVinci Resolve.")
        print("   2. En la barra superior, ve a: Espacio de trabajo -> Scripts -> DaVinci Flow")
        return 0

    if args.uninstall:
        removed = uninstall_resolve_launcher()
        if removed:
            print("✅ DaVinci Flow ha sido desinstalado del menú Scripts de DaVinci Resolve.")
        else:
            print("ℹ️ No se encontró ningún lanzador previo en la carpeta de scripts de Resolve.")
        return 0

    if args.ui:
        open_davinci_flow_ui()
        return 0

    if args.track < 1:
        print("Error: --track debe ser igual o mayor que 1.", file=sys.stderr)
        return 2
    if args.limit < 0:
        print("Error: --limit no puede ser negativo.", file=sys.stderr)
        return 2

    script_text = _load_script_text(args.script)
    glossary = parse_glossary_str(args.glossary)
    use_ai = args.correct_ai or bool(script_text or glossary or args.gemini_key)

    try:
        # Modo Reconciliación
        if args.reconcile:
            diff = reconcile_active_timeline(args.reconcile, track_index=args.track)
            print(f"Comparando contra plan previo: {diff.previous_plan_id}")
            if diff.is_identical:
                print("✅ Idempotencia: Los subtítulos son 100% idénticos. No se requieren cambios.")
            else:
                print(f"📊 Diferencias detectadas:")
                print(f"  - Bloques sin cambios: {len(diff.unchanged_blocks)}")
                print(f"  - Bloques modificados: {len(diff.modified_blocks)}")
                print(f"  - Bloques agregados: {len(diff.added_blocks)}")
                print(f"  - Bloques eliminados: {len(diff.deleted_block_ids)}")
            return 0

        # Modo Generación
        if args.generate or args.dry_run:
            record = generate_from_active_timeline(
                track_index=args.track,
                theme_name=args.theme,
                profile_name=args.profile,
                enable_sfx=not args.no_sfx,
                dry_run=args.dry_run,
                original_script=script_text,
                glossary=glossary,
                api_key=args.gemini_key,
                model_name=args.gemini_model,
                use_ai_correction=use_ai,
                insert_markers=args.add_markers,
                srt_path=args.srt,
            )
            mode_label = "SIMULACIÓN (Dry-Run)" if args.dry_run else "GENERACIÓN"
            print(f"[{mode_label}] Ejecución: {record.execution_id}")
            print(f"Proyecto: {record.project_name} | Línea de tiempo: {record.timeline_name}")
            item_label = "planificados" if args.dry_run else "creados"
            print(f"Total elementos {item_label}: {record.item_count} (Estado: {record.status})")
            for item in record.items[:15]:
                print(f"  [{item.track_name} / {item.role}] f:{item.start_frame:g}-{item.end_frame:g} -> {item.content_text}")
            if record.item_count > 15:
                print(f"… {record.item_count - 15} elementos adicionales.")
            return 0

        # Modo Planificación / Exportación
        if args.plan or args.export_plan:
            plan, corr = plan_active_subtitles(
                track_index=args.track,
                theme_name=args.theme,
                profile_name=args.profile,
                enable_sfx=not args.no_sfx,
                original_script=script_text,
                glossary=glossary,
                api_key=args.gemini_key,
                model_name=args.gemini_model,
                use_ai_correction=use_ai,
                srt_path=args.srt,
            )
            print(f"Proyecto: {plan.project_name}")
            print(f"Línea de tiempo: {plan.timeline_name}")
            print(f"Pista de subtítulos: {plan.track_index}")
            print(f"Tema: {plan.theme_name} | Perfil: {plan.profile_name}")
            print(f"Huella origen (SHA-256): {plan.source_hash[:16]}…")
            print(f"Total bloques: {plan.block_count} (Capas: {plan.layer_distribution})")

            if corr:
                print(f"✨ Correcciones IA: {corr.total_corrections} modificados | Marcadores detectados: {corr.total_markers}")
                if corr.corrections:
                    for c in corr.corrections[:5]:
                        print(f"   • [{c.start_frame:g}-{c.end_frame:g}] '{c.original_text}' -> '{c.corrected_text}' ({c.reason})")

            visible_blocks = plan.blocks if args.limit == 0 else plan.blocks[: args.limit]
            for b in visible_blocks:
                sfx_tag = f" [SFX: {b.sfx_proposal}]" if b.sfx_proposal else ""
                layers_desc = f"[{b.start_frame:g}-{b.end_frame:g}] ({b.layer_count} capas / {b.intent}){sfx_tag}"
                parts = []
                if b.context_text:
                    parts.append(f"[C: {b.context_text}]")
                parts.append(f"[M: {b.main_text}]")
                if b.accent_text:
                    parts.append(f"[A: {b.accent_text}]")
                print(f"  {layers_desc} {' '.join(parts)}")

            hidden_count = plan.block_count - len(visible_blocks)
            if hidden_count > 0:
                print(f"… {hidden_count} bloque(s) adicional(es).")

            if args.export_plan:
                plan.save_to_file(args.export_plan)
                print(f"\n✅ Plan exportado exitosamente a: {args.export_plan}")
            return 0

        # Modo Escaneo Básico
        scan = scan_active_subtitles(args.track, srt_path=args.srt)

    except DaVinciFlowError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Proyecto: {scan.project_name}")
    print(f"Línea de tiempo: {scan.timeline_name}")
    print(f"Pista de subtítulos: {scan.track_index}")
    print(f"Bloques encontrados: {len(scan.cues)}")

    visible_cues = scan.cues if args.limit == 0 else scan.cues[: args.limit]
    for cue in visible_cues:
        print(f"[{cue.start_frame:g}-{cue.end_frame:g}] {cue.text}")

    hidden_count = len(scan.cues) - len(visible_cues)
    if hidden_count > 0:
        print(f"… {hidden_count} bloque(s) adicional(es).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
