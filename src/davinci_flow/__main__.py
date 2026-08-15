"""Entrada de diagnóstico y planificación para DaVinci Flow."""

import argparse
import sys
from collections.abc import Sequence

from davinci_flow.application import plan_active_subtitles, scan_active_subtitles
from davinci_flow.errors import DaVinciFlowError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="davinci-flow",
        description="Lee una pista de subtítulos y planifica la generación dinámica de títulos.",
    )
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
        "--export-plan",
        type=str,
        default=None,
        metavar="PATH",
        help="Ruta de archivo JSON donde guardar el plan de generación calculado.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.track < 1:
        print("Error: --track debe ser igual o mayor que 1.", file=sys.stderr)
        return 2
    if args.limit < 0:
        print("Error: --limit no puede ser negativo.", file=sys.stderr)
        return 2

    try:
        if args.plan or args.export_plan:
            plan = plan_active_subtitles(
                track_index=args.track,
                theme_name=args.theme,
                profile_name=args.profile,
            )
            print(f"Proyecto: {plan.project_name}")
            print(f"Línea de tiempo: {plan.timeline_name}")
            print(f"Pista de subtítulos: {plan.track_index}")
            print(f"Tema: {plan.theme_name} | Perfil: {plan.profile_name}")
            print(f"Huella origen (SHA-256): {plan.source_hash[:16]}…")
            print(f"Total bloques: {plan.block_count} (Capas: {plan.layer_distribution})")

            visible_blocks = plan.blocks if args.limit == 0 else plan.blocks[: args.limit]
            for b in visible_blocks:
                layers_desc = f"[{b.start_frame:g}-{b.end_frame:g}] ({b.layer_count} capas / {b.intent})"
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

        scan = scan_active_subtitles(args.track)
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
