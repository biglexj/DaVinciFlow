"""Voces instaladas de Windows: catálogo real y exportación WAV sin servicios cloud."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid
import wave

from davinci_flow.editorial.model import EditorialError

SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$p = [Console]::In.ReadToEnd() | ConvertFrom-Json
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if ($p.action -eq 'list') {
        $items = @($s.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object {
            @{ id = $_.VoiceInfo.Id; name = $_.VoiceInfo.Name; language = $_.VoiceInfo.Culture.Name }
        })
        ConvertTo-Json -InputObject $items -Compress
    } elseif ($p.action -eq 'generate') {
        $s.SelectVoice($p.voice)
        $s.SetOutputToWaveFile($p.path)
        $s.Speak($p.text)
        $s.SetOutputToNull()
    } else { throw 'Invalid action' }
} finally { $s.Dispose() }
'''


def _run(payload, timeout=30):
    if os.name != 'nt':
        raise EditorialError('Las voces del sistema requieren Windows.')
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', SCRIPT],
            input=json.dumps(payload), capture_output=True, text=True, encoding='utf-8', timeout=timeout,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired) as error:
        raise EditorialError('Windows no pudo completar la síntesis de voz local.') from error
    if result.returncode:
        raise EditorialError('No se pudo utilizar la voz instalada. Actualiza el catálogo de voces.')
    return result.stdout.lstrip('\ufeff').strip()


def system_voices():
    if os.name != 'nt':
        return []
    try:
        rows = json.loads(_run({'action': 'list'}))
        if not isinstance(rows, list):
            return []
        return [{'id': 'system-' + hashlib.sha256((row['id'] + row['name']).encode()).hexdigest()[:20],
                 'name': row['name'], 'system_name': row['name'], 'language': row['language'],
                 'provider': 'system', 'ready': True} for row in rows
                if isinstance(row, dict) and all(isinstance(row.get(k), str) and row[k] for k in ('id', 'name', 'language'))]
    except (EditorialError, ValueError):
        return []


def synthesize_system(text, voice, directory):
    text = text.strip()
    if not text or len(text) > 10_000 or not voice.get('system_name'):
        raise EditorialError('Elige una voz instalada y escribe entre 1 y 10.000 caracteres.')
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (str(uuid.uuid4()) + '.wav')
    temporary = path.with_suffix('.part.wav')
    try:
        _run({'action': 'generate', 'voice': voice['system_name'], 'text': text, 'path': str(temporary.resolve())}, timeout=180)
        with wave.open(str(temporary), 'rb') as audio:
            if audio.getnframes() <= 0:
                raise EditorialError('La voz local no produjo audio válido.')
        temporary.replace(path)
    except (OSError, EOFError, wave.Error) as error:
        raise EditorialError('La voz local no produjo un WAV válido.') from error
    finally:
        temporary.unlink(missing_ok=True)
    return path
