"""Entrada de diagnóstico para la primera integración con Resolve."""

import argparse
import sys
from collections.abc import Sequence

from davinci_flow.application import scan_active_subtitles
from davinci_flow.errors import DaVinciFlowError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="davinci-flow",
        description="Lee una pista de subtítulos de la línea de tiempo activa sin modificarla.",
    )
    parser.add_argument("--track", type=int, default=1, help="Índice de pista, comenzando en 1.")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Cantidad máxima de bloques que se muestran; usa 0 para mostrarlos todos.",
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
