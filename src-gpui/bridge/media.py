"""Medios de GPUI sobre los servicios originales, con operaciones explícitas."""
from contextlib import redirect_stdout
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from protocol import read_request


def client():
    from davinci_flow.voice.aurora import AuroraVoiceClient
    return AuroraVoiceClient()


def execute(operation, args):
    if operation == 'fetch_analyze':
        from davinci_flow.fetch.engine import FetchEngine
        return asdict(FetchEngine.analyze(args['url']))
    if operation == 'fetch_download':
        from davinci_flow.fetch.engine import FetchEngine
        from davinci_flow.fetch.models import FetchRequest, MediaKind
        result = FetchEngine.download(FetchRequest(url=args['url'], kind=MediaKind(args['kind']),
            output_dir=Path(args['directory']) if args.get('directory') else None,
            import_to_resolve=args.get('import', False)))
        if not result.success:
            raise ValueError(result.error_message or 'La descarga no se completó.')
        return {'path': str(result.file_path), 'title': result.title,
                'imported': result.imported_to_resolve, 'message': result.error_message or ''}
    if operation == 'import_media':
        from davinci_flow.editorial import resolve_bridge
        path = Path(args['path'])
        if not path.is_file():
            raise ValueError('El recurso ya no existe.')
        from davinci_flow.fetch.models import MediaKind
        from davinci_flow.fetch.resolve_importer import ResolveMediaImporter
        kind = MediaKind.AUDIO if path.suffix.lower() in {'.wav', '.mp3', '.flac', '.m4a', '.aac', '.ogg'} else MediaKind.VIDEO
        success, detail = ResolveMediaImporter.import_to_resolve(path, kind)
        if not success:
            raise ValueError(detail)
        return {'success': True, 'detail': detail}
    if operation == 'preview':
        path = Path(args['path'])
        if not path.is_file():
            raise ValueError('El recurso ya no existe.')
        if path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}:
            return {'path': str(path.resolve())}
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            raise ValueError('FFmpeg no está disponible para extraer una vista previa.')
        from davinci_flow.user_data import user_data_dir
        folder = user_data_dir() / 'gpui/previews'
        folder.mkdir(parents=True, exist_ok=True)
        identity = f'{path.resolve()}:{path.stat().st_mtime_ns}:{path.stat().st_size}'
        output = folder / (hashlib.sha256(identity.encode()).hexdigest() + '.jpg')
        if not output.is_file():
            result = subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', str(path),
                '-frames:v', '1', '-vf', 'scale=480:-2', '-y', str(output)],
                capture_output=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode or not output.is_file() or not output.stat().st_size:
                output.unlink(missing_ok=True)
                raise ValueError('El recurso no contiene una imagen de previsualización disponible.')
        return {'path': str(output)}
    if operation == 'sfx_file':
        from davinci_flow.sfx.assets import ensure_builtin_sfx_assets
        files = ensure_builtin_sfx_assets()
        if args['id'] not in files:
            raise ValueError('Efecto de sonido no disponible.')
        return {'path': str(files[args['id']])}
    if operation == 'voice_login':
        voice = client()
        url = voice.account.begin_login(args.get('provider', 'google'))
        import winreg
        from davinci_flow.voice.account import scheme
        python = Path(sys.executable).with_name('pythonw.exe')
        command = subprocess.list2cmdline([str(python if python.is_file() else Path(sys.executable)),
            str(Path(__file__).with_name('auth_callback.py'))]) + ' "%1"'
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, 'Software\\Classes\\' + scheme() + '\\shell\\open\\command') as key:
            winreg.SetValueEx(key, '', 0, winreg.REG_SZ, command)
        return {'url': url}
    if operation == 'voice_complete':
        client().account.complete_login()
        return {'confirmed': True}
    if operation == 'voice_logout':
        client().account.logout()
        return {'confirmed': True}
    if operation == 'voice_catalog':
        from davinci_flow.voice.system_tts import system_voices
        voice = client()
        voices = system_voices()
        result = {'authenticated': False, 'user': '', 'voices': voices, 'balance': None, 'pending': False, 'warnings': []}
        try:
            user = voice.account.restore()
            if user:
                access = voice.refresh_access()
                result.update(authenticated=True, user=user.get('email', ''), balance=access['balance'],
                              pending=bool(voice.pending_id), voices=voices + access['voices'])
        except Exception as error:
            result['warnings'].append('No se confirmó el acceso a Aurora: ' + str(error))
        return result
    if operation in {'voice_quote', 'voice_generate', 'voice_recover'}:
        from davinci_flow.voice.system_tts import system_voices, synthesize_system
        from davinci_flow.voice.catalog import voice_cost
        from davinci_flow.user_data import user_data_dir
        if args.get('provider') == 'system':
            voice = next((v for v in system_voices() if v['id'] == args['voice']), None)
            if not voice:
                raise ValueError('La voz seleccionada ya no está instalada.')
            if operation == 'voice_quote':
                return {'cost': 0}
            return {'path': str(synthesize_system(args['text'], voice, user_data_dir() / 'gpui/voice'))}
        voice = client()
        access = voice.refresh_access()
        if operation == 'voice_recover':
            return {'path': str(voice.recover())}
        engine = next((e for e in access['engines'] if e['id'] == args['provider'] and e['available']), None)
        if not engine:
            raise ValueError('El motor de voz seleccionado no está disponible.')
        cost = voice_cost(args['text'], engine['rate'], access.get('internal', False))
        if operation == 'voice_quote':
            return {'cost': cost}
        if type(args.get('max_cost')) is not int or cost != args['max_cost']:
            raise ValueError('El consumo ha cambiado. Calcúlalo otra vez antes de generar.')
        if cost > access['balance']:
            raise ValueError('El saldo de Aurora no cubre esta generación.')
        return {'path': str(voice.generate(args['text'], args['voice'], args['provider']))}
    raise ValueError('Operación de medios no admitida.')


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
