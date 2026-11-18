"""Adaptador transitorio de IA y escritura de Resolve, tras revisión nativa."""
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from dataclasses import replace
from protocol import read_request


def execute(operation, arguments):
    if operation not in {'generate', 'apply', 'undo', 'validate'}:
        raise ValueError('Operación editorial no admitida.')
    from davinci_flow.editorial import resolve_bridge
    if operation == 'undo':
        result = resolve_bridge.undo()
        return result.to_dict() if hasattr(result, 'to_dict') else result
    from davinci_flow.editorial.model import Proposal
    with TemporaryDirectory(prefix='davinciflow-gpui-review-') as directory:
        path = Path(directory) / 'proposal.json'
        path.write_text(json.dumps(arguments['proposal'], ensure_ascii=False, allow_nan=False), encoding='utf-8')
        proposal = Proposal.load(path)
        if operation == 'validate':
            proposal.validate(require_review=arguments.get('require_review', False))
            return {'valid': True}
        if operation == 'generate':
            from davinci_flow.editorial.preferences import Preferences
            from davinci_flow.ai.providers.factory import build_text_provider
            from davinci_flow.editorial.planner import propose
            preferences = Preferences.load()
            provider = build_text_provider(preferences.provider, preferences.model)
            corrected = replace(proposal.snapshot, cues=tuple(replace(cue, text=decision.main)
                for cue, decision in zip(proposal.snapshot.cues, proposal.decisions)))
            result = propose(corrected, proposal.templates, provider, options=proposal.options)
            result = replace(result, snapshot=proposal.snapshot, decisions=tuple(
                replace(decision, edit_note=original.edit_note)
                for decision, original in zip(result.decisions, proposal.decisions)))
            result.validate()
            return result.to_dict()
        proposal.validate(require_review=True)
        result = resolve_bridge.apply(proposal)
        return result.to_dict() if hasattr(result, 'to_dict') else result


def main():
    try:
        with redirect_stdout(sys.stderr):
            operation, arguments = read_request()
            result = execute(operation, arguments)
        response = {'ok': True, 'result': result}
    except Exception as error:
        response = {'ok': False, 'error': str(error)}
    print('DAVINCI_FLOW_GPUI=' + json.dumps(response, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
