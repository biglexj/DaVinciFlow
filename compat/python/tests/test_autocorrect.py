"""Pruebas unitarias del autocorrector de subtítulos."""

import re
import unittest

from davinci_flow.errors import AutocorrectError
from davinci_flow.subtitles.autocorrect import (
    AI_STAGE,
    GLOSSARY_STAGE,
    NORMALIZATION_STAGE,
    SubtitleAutocorrector,
)
from davinci_flow.subtitles.model import SubtitleCue


class _FakeProvider:
    """Proveedor de IA simulado que devuelve correcciones para lo que se le pide.

    El prompt del autocorrector enumera las líneas como ``<indice>: <texto>``; el
    doble lee esos índices para devolver exactamente el lote solicitado.
    """

    name = "fake"
    _INDEX_PATTERN = re.compile(r"^(\d+): ", re.MULTILINE)

    def __init__(self, payload=None, model_name="modelo-fake", text_for_index=None):
        self.payload = payload
        self.model_name = model_name
        self.text_for_index = text_for_index
        self.calls = []

    def generate_json(self, prompt, system_instruction="", temperature=0.2):
        self.calls.append(prompt)
        if self.payload is not None:
            return self.payload
        indices = [int(value) for value in self._INDEX_PATTERN.findall(prompt)]
        return {
            "correcciones": [
                {"indice": index, "texto": self.text_for_index(index) if self.text_for_index else f"linea {index}"}
                for index in indices
            ]
        }

    def generate_text(self, prompt, system_instruction="", temperature=0.4):
        return "texto"

    def test_connection(self):
        return True


def _cue(text, start=0, end=48, track=1):
    return SubtitleCue(text=text, start_frame=start, end_frame=end, track_index=track)


class AutocorrectDeterministicTests(unittest.TestCase):
    """Verifica las etapas que no dependen del modelo."""

    def test_normalization_stage(self) -> None:
        corrector = SubtitleAutocorrector()
        result = corrector.correct([_cue("  Hola   mundo  ")], use_ai=False)
        self.assertEqual(result.cues[0].text, "Hola mundo")
        self.assertEqual(result.stages_applied, (NORMALIZATION_STAGE,))
        self.assertEqual(result.changes[0].stages, (NORMALIZATION_STAGE,))

    def test_glossary_stage(self) -> None:
        corrector = SubtitleAutocorrector(glossary={"DaVinci": "DaVinci Resolve"})
        result = corrector.correct([_cue("DaVinci")], use_ai=False)
        self.assertEqual(result.cues[0].text, "DaVinci Resolve")
        self.assertEqual(result.stages_applied, (NORMALIZATION_STAGE, GLOSSARY_STAGE))
        self.assertEqual(result.changes[0].stages, (GLOSSARY_STAGE,))

    def test_ai_stage_is_reported_as_skipped(self) -> None:
        corrector = SubtitleAutocorrector()
        result = corrector.correct([_cue("Hola")], use_ai=False)
        self.assertEqual(result.ai_status, "skipped")
        self.assertEqual(result.modified_count, 0)

    def test_empty_batch_is_rejected(self) -> None:
        with self.assertRaises(AutocorrectError):
            SubtitleAutocorrector().correct([], use_ai=False)

    def test_ai_without_provider_is_rejected(self) -> None:
        with self.assertRaises(AutocorrectError):
            SubtitleAutocorrector().correct([_cue("Hola")], use_ai=True)


class AutocorrectAITests(unittest.TestCase):
    """Verifica la etapa con IA y la validación de su respuesta."""

    def test_applies_corrections_and_reports_stage(self) -> None:
        provider = _FakeProvider({"correcciones": [{"indice": 0, "texto": "Hola, ¿cómo estás?"}]})
        corrector = SubtitleAutocorrector(provider=provider)
        result = corrector.correct([_cue("Hola como estas")], use_ai=True)

        self.assertEqual(result.cues[0].text, "Hola, ¿cómo estás?")
        self.assertEqual(result.ai_status, "ok")
        self.assertEqual(result.changes[0].stages, (AI_STAGE,))
        self.assertEqual(result.modified_count, 1)

    def test_keeps_original_when_model_repeats_text(self) -> None:
        provider = _FakeProvider({"correcciones": [{"indice": 0, "texto": "Hola como estas"}]})
        corrector = SubtitleAutocorrector(provider=provider)
        result = corrector.correct([_cue("Hola como estas")], use_ai=True)
        self.assertEqual(result.modified_count, 0)

    def test_wrong_indices_cancel_the_operation(self) -> None:
        provider = _FakeProvider({"correcciones": [{"indice": 7, "texto": "Otro"}]})
        corrector = SubtitleAutocorrector(provider=provider)
        with self.assertRaises(AutocorrectError):
            corrector.correct([_cue("Hola")], use_ai=True)

    def test_invalid_payload_cancels_the_operation(self) -> None:
        provider = _FakeProvider({"otra_cosa": []})
        corrector = SubtitleAutocorrector(provider=provider)
        with self.assertRaises(AutocorrectError):
            corrector.correct([_cue("Hola")], use_ai=True)

    def test_batches_are_split(self) -> None:
        provider = _FakeProvider(text_for_index=lambda index: f"linea {index}")
        corrector = SubtitleAutocorrector(provider=provider, batch_size=2)
        cues = [_cue(f"linea {index}", start=index * 48, end=index * 48 + 48) for index in range(6)]
        result = corrector.correct(cues, use_ai=True)
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(result.cues[5].text, "linea 5")

    def test_summary_counts_changes(self) -> None:
        provider = _FakeProvider(
            {"correcciones": [{"indice": 0, "texto": "Corregido"}, {"indice": 1, "texto": "Igual"}]}
        )
        corrector = SubtitleAutocorrector(provider=provider)
        cues = [_cue("Mal escrito", 0, 48), _cue("Igual", 48, 96)]
        result = corrector.correct(cues, use_ai=True)
        summary = result.summary()
        self.assertEqual(summary["cues"], 2)
        self.assertEqual(summary["modificados"], 1)
        self.assertEqual(summary["sin_cambios"], 1)
        self.assertEqual(summary["estado_ia"], "ok")

    def test_invalid_batch_size_is_rejected(self) -> None:
        with self.assertRaises(AutocorrectError):
            SubtitleAutocorrector(batch_size=0)


if __name__ == "__main__":
    unittest.main()
