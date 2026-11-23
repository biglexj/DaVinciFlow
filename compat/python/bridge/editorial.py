"""Adaptador transitorio de IA y escritura de Resolve, tras revisión nativa."""
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from dataclasses import replace
from protocol import read_request


def execute(operation, arguments):
    if operation not in {'generate', 'generate_decisions', 'apply', 'undo', 'clean_tracks', 'validate', 'batch_next'}:
        raise ValueError('Operación editorial no admitida.')
    from davinci_flow.editorial import resolve_bridge
    if operation == 'undo':
        result = resolve_bridge.undo()
        return result.to_dict() if hasattr(result, 'to_dict') else result
    if operation == 'clean_tracks':
        result = resolve_bridge.clean_tracks()
        return result if isinstance(result, dict) else {'deleted_count': int(result or 0)}
    from davinci_flow.editorial.model import EditorialConflictError, Proposal
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
        if operation == 'generate_decisions':
            from davinci_flow.ai.decision_client import DecisionClient
            from davinci_flow.editorial.decision_planner import propose_with_decisions
            corrected = replace(proposal.snapshot, cues=tuple(replace(cue, text=decision.main)
                for cue, decision in zip(proposal.snapshot.cues, proposal.decisions)))
            result, _traces = propose_with_decisions(
                corrected, proposal.templates, DecisionClient(), options=proposal.options
            )
            result = replace(result, snapshot=proposal.snapshot, decisions=tuple(
                replace(decision, edit_note=original.edit_note)
                for decision, original in zip(result.decisions, proposal.decisions)))
            result.validate()
            return result.to_dict()
        if operation == 'batch_next':
            from davinci_flow.editorial.batch_run import EditorialBatchStore, generate_next_batch
            from davinci_flow.editorial.preferences import Preferences
            from davinci_flow.ai.model_catalog import capability_for
            preferences = Preferences.load()
            batch_size = str(arguments.get('batch_size') or preferences.batch_size or '20')
            store = EditorialBatchStore()
            corrected = replace(proposal.snapshot, cues=tuple(replace(cue, text=decision.main)
                for cue, decision in zip(proposal.snapshot.cues, proposal.decisions)))
            run, message = store.create_or_resume(corrected, proposal.templates, proposal.options)
            capability = capability_for(preferences.provider, preferences.model)
            start, end, _ = generate_next_batch(
                run, batch_size, preferences.provider, preferences.model,
                bool(preferences.long_context_enabled and capability.long_context),
                capability, store=store,
            )
            decisions = []
            for idx, orig_decision in enumerate(proposal.decisions):
                batch_d = run.decisions[idx]
                if batch_d is not None:
                    decisions.append(replace(batch_d, cue_index=idx, edit_note=orig_decision.edit_note or batch_d.edit_note))
                else:
                    decisions.append(orig_decision)
            merged = replace(
                proposal,
                decisions=tuple(decisions),
                model=f'{preferences.provider}/{preferences.model}',
            )
            merged.validate()
            return {
                'proposal': merged.to_dict(),
                'processed': run.processed,
                'total': run.total,
                'complete': run.complete,
                'next_number': run.next_subtitle_number,
                'start': start,
                'end': end,
                'message': message,
            }
        proposal.validate(require_review=True)
        try:
            result = resolve_bridge.apply(proposal)
            payload = result.to_dict() if hasattr(result, 'to_dict') else result
            return {'applied': True, 'record': payload}
        except EditorialConflictError as err:
            return {
                'applied': False,
                'conflicts': [
                    {
                        'cue_index': int(c.cue_index),
                        'cue_text': str(c.cue_text),
                        'track_name': str(c.track_name),
                        'track_index': int(c.track_index),
                        'clip_name': str(c.clip_name),
                        'start_frame': float(c.start_frame),
                        'end_frame': float(c.end_frame),
                    }
                    for c in err.conflicts
                ],
            }


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
