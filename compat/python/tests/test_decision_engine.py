"""Pruebas del modo experimental: API de decisiones y motor editorial por decisiones."""

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import urllib.error

from davinci_flow.ai.decision_client import DecisionClient, DecisionUsage
from davinci_flow.editorial.decision_planner import (
    LAYER_ACCENT,
    LAYER_CONTEXT,
    LAYER_MAIN,
    LAYER_NONE,
    propose_with_decisions,
)
from davinci_flow.editorial.experiment import audit_proposal, compare_proposals
from davinci_flow.editorial.model import Decision, EditorialError, EditorialOptions, Proposal
from davinci_flow.editorial.sources import basic_titles, from_srt

FIXTURE = "process/active/2026-11-11_experimento-gemini-decision-1/casos/casos-editoriales.srt"


def _answer(**kwargs):
    """Construye una respuesta con la misma forma que devuelve el cliente real."""
    probabilities = kwargs.get("probabilities") or {}
    if kwargs.get("type") == "noul":
        probabilities = {"sí": kwargs.get("noul", 0.0), "no": 1 - kwargs.get("noul", 0.0)}
    return SimpleNamespace(
        type=kwargs.get("type", "noul"),
        noul=kwargs.get("noul"),
        choice=kwargs.get("choice"),
        score=kwargs.get("score"),
        probabilities=probabilities,
        confidence=kwargs.get("confidence", 0.0),
        legend=kwargs.get("legend") or {},
        probability=probabilities.get(kwargs.get("choice") or "sí", 0.0),
    )


class _FakeDecisionClient:
    """Cliente de decisiones simulado con respuestas por clave."""

    model_name = "gemini-decision-1"

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def decide(self, input_text, questions):
        self.calls.append((input_text, questions))
        return {key: self.answers.get(key) for key in questions if key in self.answers}, DecisionUsage()


class DecisionClientTests(unittest.TestCase):
    """Verifica el contrato HTTP del cliente de la API de decisiones."""

    def _client(self):
        with patch("davinci_flow.ai.decision_client.get_gemini_api_key", return_value="clave"):
            return DecisionClient()

    def test_reads_answers_and_usage(self):
        body = {
            "answers": {
                "q": {
                    "type": "noul",
                    "noul": 0.9,
                    "confidence": 0.9,
                    "probabilities": {"sí": 0.9, "no": 0.1},
                }
            },
            "usage": {"total_input_tokens": 120, "total_output_tokens": 0},
        }
        response = MagicMock()
        response.read.return_value = json.dumps(body).encode("utf-8")
        response.__enter__.return_value = response
        with patch("davinci_flow.ai.decision_client.urllib.request.urlopen", return_value=response):
            answers, usage = self._client().decide("texto", {"q": {"type": "noul", "instructions": "¿?"}})
        self.assertEqual(answers["q"].noul, 0.9)
        self.assertEqual(answers["q"].probability, 0.9)
        self.assertEqual(usage.total_input_tokens, 120)

    def test_rejects_invalid_questions(self):
        client = self._client()
        with self.assertRaises(Exception):
            client.decide("", {"q": {"type": "noul", "instructions": "¿?"}})
        with self.assertRaises(Exception):
            client.decide("texto", {"clave inválida": {"type": "noul", "instructions": "¿?"}})
        with self.assertRaises(Exception):
            client.decide("texto", {"q": {"type": "otro", "instructions": "¿?"}})
        with self.assertRaises(Exception):
            client.decide("texto", {"q": {"type": "noul", "instructions": ""}})

    def test_maps_authentication_error(self):
        error = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)
        with patch("davinci_flow.ai.decision_client.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(Exception) as context:
                self._client().decide("texto", {"q": {"type": "noul", "instructions": "¿?"}})
        self.assertIn("decisiones", str(context.exception).lower())


def _answers_for(snapshot, **overrides):
    """Respuestas simuladas para todos los bloques de una captura."""
    answers = {}
    for index in range(len(snapshot.cues)):
        answers[f"c{index}_destaca"] = _answer(type="noul", noul=0.9)
        answers[f"c{index}_jerarquia"] = _answer(type="choice", choice=LAYER_MAIN,
                                                probabilities={LAYER_MAIN: 0.9})
        answers[f"c{index}_intensidad"] = _answer(type="score", score=2.0, probabilities={"2": 0.9})
        answers[f"c{index}_plantilla_ctx"] = _answer(type="choice", choice="t0", probabilities={"t0": 1.0})
        answers[f"c{index}_plantilla_main"] = _answer(type="choice", choice="t0", probabilities={"t0": 1.0})
        answers[f"c{index}_plantilla_accent"] = _answer(type="choice", choice="t0", probabilities={"t0": 1.0})
        answers[f"c{index}_efecto"] = _answer(type="noul", noul=0.1)
        answers[f"c{index}_tipo_efecto"] = _answer(type="choice", choice="s0", probabilities={"s0": 1.0})
        answers[f"c{index}_respirar"] = _answer(type="noul", noul=0.1)
        answers[f"c{index}_acento_final"] = _answer(type="noul", noul=0.2)
    for key, value in overrides.items():
        answers[key] = value
    return answers


class DecisionPlannerTests(unittest.TestCase):
    """Verifica que las decisiones calibradas respetan el contrato editorial."""

    def setUp(self):
        self.snapshot = from_srt(FIXTURE, fps=24.0)
        self.templates = basic_titles()
        self.options = EditorialOptions(mode="highlights", format="auto", density="balanced",
                                        direction="", resources=())

    def _answers_for(self, **overrides):
        return _answers_for(self.snapshot, **overrides)

    def test_proposal_is_valid_and_reviewed_is_false(self):
        client = _FakeDecisionClient(self._answers_for())
        proposal, traces = propose_with_decisions(self.snapshot, self.templates, client, self.options)
        proposal.validate()
        self.assertEqual(len(traces), len(self.snapshot.cues))
        self.assertTrue(all(decision.reviewed is False for decision in proposal.decisions))
        self.assertEqual(proposal.model, "gemini-decision-1")
        self.assertEqual(proposal.version, "1.1.0")

    def test_low_probability_leaves_block_without_rotulo(self):
        answers = self._answers_for()
        answers["c0_destaca"] = _answer(type="noul", noul=0.1)
        client = _FakeDecisionClient(answers)
        proposal, _traces = propose_with_decisions(self.snapshot, self.templates, client, self.options)
        first = proposal.decisions[0]
        self.assertFalse(first.enabled)
        self.assertEqual(first.main, "")
        self.assertEqual(first.templates, {})

    def test_respirar_disables_rotulo_and_sound(self):
        answers = self._answers_for()
        answers["c1_respirar"] = _answer(type="noul", noul=0.95)
        client = _FakeDecisionClient(answers)
        proposal, _traces = propose_with_decisions(self.snapshot, self.templates, client, self.options)
        self.assertFalse(proposal.decisions[1].enabled)
        self.assertEqual(proposal.decisions[1].resource_id, "")

    def test_sound_only_when_requested_and_not_blocked(self):
        answers = self._answers_for()
        answers["c0_efecto"] = _answer(type="noul", noul=0.95)
        answers["c0_tipo_efecto"] = _answer(type="choice", choice="s0", probabilities={"s0": 1.0})
        client = _FakeDecisionClient(answers)
        proposal, _traces = propose_with_decisions(self.snapshot, self.templates, client, self.options)
        self.assertTrue(proposal.decisions[0].resource_id.startswith("sfx_"))

    def test_accent_split_keeps_the_original_order(self):
        answers = self._answers_for()
        answers["c8_jerarquia"] = _answer(type="choice", choice=LAYER_ACCENT,
                                           probabilities={LAYER_ACCENT: 0.9})
        answers["c8_acento_final"] = _answer(type="noul", noul=0.9)
        client = _FakeDecisionClient(answers)
        proposal, _traces = propose_with_decisions(self.snapshot, self.templates, client, self.options)
        decision = proposal.decisions[8]
        self.assertTrue(decision.accent)
        self.assertIn("accent", decision.templates)
        rebuilt = " ".join(" ".join((decision.context, decision.main, decision.accent)).split())
        self.assertEqual(rebuilt, " ".join(self.snapshot.cues[8].text.split()))

    def test_idea_extraction_never_drops_negations(self):
        answers = self._answers_for()
        answers["c8_idea_larga"] = _answer(type="noul", noul=0.99)
        client = _FakeDecisionClient(answers)
        proposal, _traces = propose_with_decisions(self.snapshot, self.templates, client, self.options)
        decision = proposal.decisions[8]
        self.assertIn("No", decision.main)

    def test_context_layer_splits_the_block_in_order(self):
        answers = self._answers_for()
        answers["c2_jerarquia"] = _answer(type="choice", choice=LAYER_CONTEXT,
                                           probabilities={LAYER_CONTEXT: 0.9})
        client = _FakeDecisionClient(answers)
        proposal, _traces = propose_with_decisions(self.snapshot, self.templates, client, self.options)
        decision = proposal.decisions[2]
        self.assertTrue(decision.context)
        self.assertIn("context", decision.templates)
        rebuilt = " ".join(" ".join((decision.context, decision.main, decision.accent)).split())
        self.assertEqual(rebuilt, " ".join(self.snapshot.cues[2].text.split()))

    def test_layer_none_leaves_the_block_untouched(self):
        answers = self._answers_for()
        answers["c3_jerarquia"] = _answer(type="choice", choice=LAYER_NONE, probabilities={LAYER_NONE: 0.95})
        client = _FakeDecisionClient(answers)
        proposal, _traces = propose_with_decisions(self.snapshot, self.templates, client, self.options)
        self.assertFalse(proposal.decisions[3].enabled)

    def test_reason_records_the_probabilities(self):
        client = _FakeDecisionClient(self._answers_for())
        proposal, traces = propose_with_decisions(self.snapshot, self.templates, client, self.options)
        self.assertIn("0.90", proposal.decisions[0].reason)
        self.assertEqual(proposal.decisions[0].reason.count("·"), 3)

    def test_one_request_per_batch(self):
        client = _FakeDecisionClient(self._answers_for())
        propose_with_decisions(self.snapshot, self.templates, client, self.options, batch_size=5)
        self.assertEqual(len(client.calls), 3)
        input_text, questions = client.calls[0]
        self.assertIn("Transcripción", input_text)
        self.assertLessEqual(len(questions), 1000)


class ControllerDecisionTests(unittest.TestCase):
    """Verifica la integración del motor de decisiones en el controlador."""

    def test_controller_proposes_with_decisions(self):
        from davinci_flow.editorial.controller import EditorialController

        snapshot = from_srt(FIXTURE, fps=24.0)
        with tempfile.TemporaryDirectory() as tmp:
            controller = EditorialController(Path(tmp) / "prefs.json")
            controller.snapshot = snapshot
            controller.templates = basic_titles()
            client = _FakeDecisionClient(_answers_for(snapshot))
            proposal = controller.generate_decisions(client=client)
            self.assertEqual(proposal.model, "gemini-decision-1")
            self.assertIs(controller.proposal, proposal)
            self.assertTrue(controller.dirty)
            self.assertTrue(all(not decision.reviewed for decision in proposal.decisions))

    def test_controller_requires_a_capture(self):
        from davinci_flow.editorial.controller import EditorialController

        with tempfile.TemporaryDirectory() as tmp:
            controller = EditorialController(Path(tmp) / "prefs.json")
            with self.assertRaises(EditorialError):
                controller.generate_decisions(client=_FakeDecisionClient({}))


class ComparisonTests(unittest.TestCase):
    """Verifica las métricas de comparación entre motores."""

    def _proposal(self, enabled_flags, cues=None):
        snapshot = from_srt(FIXTURE, fps=24.0)
        if cues is not None:
            snapshot = replace(snapshot, cues=tuple(snapshot.cues[:cues]))
        templates = basic_titles()
        options = EditorialOptions(mode="highlights", format="auto", density="balanced",
                                    direction="", resources=())
        decisions = tuple(
            Decision(cue_index=index, context="", main=cue.text if flag else "",
                     accent="", templates={"main": templates[0].id} if flag else {},
                     reason="motivo", enabled=flag, reviewed=False)
            for index, (cue, flag) in enumerate(zip(snapshot.cues, enabled_flags))
        )
        proposal = Proposal(snapshot, templates, decisions, "modelo", "1.1.0", options)
        proposal.validate()
        return proposal

    def test_agreement_is_measured_per_block(self):
        baseline = self._proposal([True] * 12)
        candidate = self._proposal([True] * 6 + [False] * 6)
        metrics = compare_proposals(baseline, candidate)
        self.assertEqual(metrics.blocks, 12)
        self.assertAlmostEqual(metrics.enabled_agreement, 0.5)
        self.assertAlmostEqual(metrics.exact_agreement, 0.5)
        self.assertEqual(metrics.baseline_accepted, 1.0)

    def test_audit_detects_contract_breaches(self):
        baseline = self._proposal([True] * 12)
        broken = self._proposal([True] * 12)
        decisions = list(broken.decisions)
        decisions[0] = Decision(cue_index=0, context="", main="palabras inventadas", accent="",
                                 templates={"main": broken.templates[0].id}, reason="motivo",
                                 enabled=True, reviewed=False)
        broken = Proposal(broken.snapshot, broken.templates, tuple(decisions), "modelo", "1.0.0")
        audits = audit_proposal(broken)
        self.assertFalse(audits[0].accepted)
        self.assertTrue(all(audit.accepted for audit in audits[1:]))

    def test_proposal_with_different_sizes_cannot_be_compared(self):
        baseline = self._proposal([True] * 12)
        candidate = self._proposal([True] * 6, cues=6)
        with self.assertRaises(EditorialError):
            compare_proposals(baseline, candidate)


if __name__ == "__main__":
    unittest.main()
