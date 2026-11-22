"""Voz de Aurora: cuenta, acceso verificado, generación y audio recuperable."""

import inspect
import asyncio
import uuid
import flet as ft

from davinci_flow.voice.aurora import AuroraVoiceClient
from davinci_flow.voice.media import AUDIO_EXTENSIONS, import_voice_file, validate_voice_file
from davinci_flow.voice.catalog import normalize_catalog, voice_cost
from davinci_flow.voice.system_tts import system_voices, synthesize_system
from shared.components import ACCENT, MUTED, button, card, field, select, text

VOICE_STUDIO_URL = 'https://biglexj.com/creator-suite/audio?tab=voice_studio'


class VoiceView:
    def __init__(self, app, client=None):
        self.app = app
        self.client = client or AuroraVoiceClient()
        self.audio_path = None
        self.player = None
        self.opened = False
        self.waiting_login = False
        self.voices_by_engine = {}
        self.engines = {}
        self.local_voices = []
        self.local_loaded = False
        self.account_status = text('Conecta tu cuenta de Aurora', size=14, weight=ft.FontWeight.W_600)
        self.account_avatar = ft.Container(ft.Icon(ft.Icons.ACCOUNT_CIRCLE_OUTLINED, color=ACCENT),
                                           width=28, height=28, alignment=ft.Alignment.CENTER)
        self.access_status = text('Tu saldo y acceso de prueba se consultarán en Aurora.', color=MUTED)
        self.login_buttons = ft.Row([
            button('Continuar con Google', app.bind(self.login, 'google'), ft.Icons.LOGIN, primary=True),
            button('Discord', app.bind(self.login, 'discord')),
        ], wrap=True)
        self.cancel_button = button('Cancelar inicio', app.bind(self.cancel_login), visible=False)
        self.session_buttons = ft.Row([
            button('Actualizar acceso', app.bind(self.refresh_access), ft.Icons.REFRESH),
            button('Cerrar sesión', app.bind(self.logout)),
        ], visible=False, wrap=True)
        self.account_card = card(ft.Column([
            ft.Row([self.account_avatar, self.account_status], spacing=10),
            self.access_status, self.login_buttons, self.cancel_button, self.session_buttons,
        ], spacing=12), padding=20)
        self.account_summary = text('Inicia sesión en Ajustes para generar voz.', color=MUTED, expand=True)
        self.narration = field('Guion de voz', multiline=True, min_lines=10, max_lines=16,
                               hint_text='Escribe el texto tal como quieres escucharlo.', on_change=app.bind(self.update_estimate))
        self.engine = select('Proveedor / modelo', {}, None, 280, disabled=True,
                             on_select=app.bind(self.change_engine))
        self.voice = select('Voz', {}, None, 320, disabled=True, on_select=app.bind(self.update_estimate))
        self.estimate = text('0 caracteres', color=MUTED)
        self.catalog_status = text('', color=MUTED, size=11, visible=False)
        self.generate_button = button('Generar voz', app.bind(self.generate), ft.Icons.RECORD_VOICE_OVER_ROUNDED, primary=True, disabled=True)
        self.recover_button = button('Recuperar generación', app.bind(self.recover), ft.Icons.RESTORE, visible=False)
        self.generator = card(ft.Column([
            self.narration, ft.Row([self.engine, self.voice, self.estimate], wrap=True, spacing=10),
            self.catalog_status,
            ft.Row([self.generate_button, self.recover_button], wrap=True),
        ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
        self.generator.disabled = True
        self.file_name = text('Aún no hay audio. También puedes seleccionar uno descargado de Voice Studio.', color=MUTED, selectable=True)
        self.player_area = ft.Container(visible=False)
        self.import_button = button('Importar a Resolve', app.bind(self.import_audio), ft.Icons.LIBRARY_ADD_OUTLINED, primary=True, disabled=True)
        self.content = ft.Column([
            ft.Row([self.account_summary,
                    button('Ir a Ajustes', app.bind(app.navigate, 'settings'), ft.Icons.SETTINGS_OUTLINED)], spacing=10),
            self.generator,
            card(ft.Column([
                text('Audio generado', size=14, weight=ft.FontWeight.W_600), self.player_area, self.file_name,
                ft.Row([self.import_button, button('Seleccionar audio', app.bind(self.pick_audio), ft.Icons.AUDIO_FILE_OUTLINED),
                        button('Voice Studio web', app.bind(self.open_studio), ft.Icons.OPEN_IN_NEW)], wrap=True),
                text('Se importa al Media Pool del proyecto activo, en «DaVinci Flow · Voces».', color=MUTED),
            ], spacing=10)),
        ], spacing=12, expand=True, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.import_button.opacity = 0.45

    async def open(self):
        if not self.opened:
            self.opened = True
            await self.load_local_voices()
            if self.client.account.store.exists('session'):
                result = await self.app.run('Verificando la sesión de Aurora…', self.client.account.restore)
                if result:
                    await self.refresh_access()
            self.render_account()

    async def _launch(self, url):
        result = self.app.page.launch_url(url)
        if inspect.isawaitable(result):
            await result

    async def open_studio(self):
        await self._launch(VOICE_STUDIO_URL)

    async def login(self, provider):
        url = await self.app.run('Preparando el inicio de sesión de Aurora…', lambda: self.client.account.begin_login(provider))
        if url:
            self.waiting_login = True
            self.render_account()
            await self._launch(url)
            self.app.notify('Completa el inicio de sesión en el navegador y vuelve a DaVinci Flow.')

    async def cancel_login(self):
        self.client.account.cancel_login()
        self.waiting_login = False
        self.render_account()

    async def handle_callback_if_ready(self):
        if self.app.busy or self.app.closing or not self.client.account.store.exists('callback'):
            return
        result = await self.app.run('Verificando el retorno de Aurora…', self.client.account.complete_login)
        self.waiting_login = False
        if result:
            await self.app.navigate('settings')
            await self.refresh_access()
        self.render_account()
        self.app.page.update()

    async def refresh_access(self):
        await self.load_local_voices()
        result = await self.app.run('Consultando acceso, voces y saldo de Aurora…', self.client.refresh_access)
        self._set_catalog(result)
        self.render_account()

    async def load_local_voices(self):
        if not self.local_loaded:
            self.local_voices = await asyncio.get_running_loop().run_in_executor(self.app.media_executor, system_voices)
            self.local_loaded = True
        self._set_catalog(self.client.access)

    def _set_catalog(self, result):
        self.voices_by_engine = {}
        catalog = normalize_catalog(result) if result else {'engines': [], 'voices': []}
        self.engines = {engine['id']: engine for engine in catalog['engines']}
        for voice in catalog['voices']:
            if voice['ready']:
                self.voices_by_engine.setdefault(voice['provider'], {})[voice['id']] = voice['name']
        if self.local_voices:
            self.engines['system'] = {'id': 'system', 'name': 'Voces del sistema · Gratis', 'available': True,
                                      'rate': None}
            self.voices_by_engine['system'] = {voice['id']: voice['name'] for voice in self.local_voices}
        available = {key for key, engine in self.engines.items() if engine['available'] and self.voices_by_engine.get(key)}
        self.engine.options = [ft.DropdownOption(key=key,
            text=engine['name'] + ('' if key in available else ' · No disponible'), disabled=key not in available)
            for key, engine in self.engines.items()]
        self.engine.disabled = not available
        if self.engine.value not in available:
            self.engine.value = next((key for key in self.engines if key in available), None)
        notices = list(catalog.get('notices', []))
        if result and result.get('catalog_version') != 2:
            notices.append('Este servidor todavía expone el catálogo anterior. Falta actualizar Aurora para los demás motores.')
        self.catalog_status.value = ' '.join(notices)
        self.catalog_status.visible = bool(notices)
        self._refresh_voices()

    def _refresh_voices(self):
        voices = self.voices_by_engine.get(self.engine.value, {})
        self.voice.options = [ft.DropdownOption(key=key, text=name) for key, name in voices.items()]
        self.voice.disabled = not voices
        if self.voice.value not in voices:
            self.voice.value = next(iter(voices), None)

    def change_engine(self):
        self.voice.value = None
        self._refresh_voices()
        self.update_estimate()

    def render_account(self):
        user, access = self.client.account.user, self.client.access
        avatar = (user.get('profile_avatar_url') or user.get('avatar_url')) if user else None
        fallback = ft.Icon(ft.Icons.ACCOUNT_CIRCLE_OUTLINED, color=ACCENT)
        self.account_avatar.content = ft.Image(src=avatar, width=28, height=28, fit=ft.BoxFit.COVER,
                                               border_radius=14, error_content=fallback) if avatar else fallback
        if user:
            self.account_status.value = user.get('email') or 'Cuenta de Aurora'
        else:
            self.account_status.value = 'Esperando el navegador…' if self.waiting_login else 'Conecta tu cuenta de Aurora'
        self.login_buttons.visible = not user and not self.waiting_login
        self.cancel_button.visible = self.waiting_login
        self.session_buttons.visible = bool(user)
        if access and access.get('internal'):
            self.access_status.value = 'Acceso interno · Sin consumo de créditos'
            self.account_summary.value = self.access_status.value
        elif access:
            self.access_status.value = f"{access['plan']} · {access['balance']} créditos disponibles"
            self.account_summary.value = self.access_status.value
        else:
            self.access_status.value = 'El acceso debe verificarse en Aurora antes de generar.' if user else 'La prueba utiliza los créditos disponibles de tu cuenta.'
            self.account_summary.value = 'Actualiza tu acceso en Ajustes para generar voz.' if user else 'Inicia sesión en Ajustes para generar voz.'
        self.generator.disabled = not bool(user)
        self.generator.opacity = 1 if user else 0.55
        self.recover_button.visible = bool(user and self.client.pending_id)
        self.update_estimate()

    def update_estimate(self):
        count = len((self.narration.value or '').strip())
        access = self.client.access if self.client.account.user else None
        self.estimate.value = f'{count}/10.000 caracteres'
        engine = self.engines.get(self.engine.value, {})
        local = self.engine.value == 'system'
        enough = bool(self.client.account.user) if local else bool(access and access.get('internal'))
        if local:
            self.estimate.value += ' · Gratis · Generación local'
        elif access and not enough and engine.get('available'):
            cost = voice_cost(self.narration.value or '', engine.get('rate'))
            self.estimate.value += f' · {cost} créditos estimados'
            enough = cost <= access['balance']
        valid_voice = self.voice.value in self.voices_by_engine.get(self.engine.value, {})
        self.generate_button.disabled = not ((access or local) and engine.get('available') and enough
            and 0 < count <= 10_000 and valid_voice and not self.client.pending_id)
        self.generate_button.opacity = 0.45 if self.generate_button.disabled else 1
        self.recover_button.visible = bool(self.client.account.user and self.client.pending_id)

    async def generate(self):
        self.update_estimate()
        if self.generate_button.disabled:
            return
        local = self.engine.value == 'system'
        if local:
            voice = next(v for v in self.local_voices if v['id'] == self.voice.value)
            owner = str(uuid.UUID(self.client.account.user['id']))
            path = await self.app.run('Generando voz en este equipo…', lambda: synthesize_system(
                self.narration.value or '', voice, self.client.directory / 'generated' / owner / 'system'))
        else:
            path = await self.app.run('Generando voz en Aurora…', lambda: self.client.generate(
                self.narration.value or '', self.voice.value, provider=self.engine.value))
        self.render_account()
        if path:
            await self.show_audio(path)
            if not local:
                await self.refresh_access()

    async def recover(self):
        path = await self.app.run('Buscando el resultado de tu solicitud…', self.client.recover)
        self.render_account()
        if path:
            await self.show_audio(path)
            await self.refresh_access()

    async def show_audio(self, path):
        import flet_video as ftv
        if self.player:
            await self.player.pause()
        self.audio_path = validate_voice_file(path)
        self.file_name.value = str(self.audio_path)
        self.import_button.disabled = False
        self.import_button.opacity = 1
        self.player = ftv.Video(playlist=[ftv.VideoMedia(self.audio_path.resolve().as_uri())], autoplay=False, volume=100, height=80,
            configuration=ftv.VideoConfiguration(enable_hardware_acceleration=False, hardware_decoding_api='no'),
            on_error=lambda e: self.app.show_error('No se pudo reproducir este archivo de audio.'))
        self.player_area.content = self.player
        self.player_area.visible = True

    async def pick_audio(self):
        path = await self.app.pick_file('Audio generado en Voice Studio', list(AUDIO_EXTENSIONS))
        if path:
            await self.show_audio(path)

    async def import_audio(self):
        if self.audio_path is None:
            return
        result = await self.app.run('Importando audio a Resolve…', lambda: import_voice_file(self.audio_path))
        if result:
            self.app.notify(f'Audio importado al Media Pool: {result}.')

    async def logout(self):
        if self.player:
            await self.player.pause()
        revoked = await self.app.run('Cerrando la sesión de Aurora…', self.client.logout)
        self.waiting_login, self.audio_path, self.player = False, None, None
        self.player_area.visible, self.import_button.disabled = False, True
        self.import_button.opacity = 0.45
        self.player_area.content = None
        self.narration.value = ''
        self.voice.value = None
        self.voice.options = []
        self.voice.disabled = True
        self.engine.value = None
        self.engine.options = []
        self.engine.disabled = True
        self.voices_by_engine.clear()
        self.engines.clear()
        self.file_name.value = 'Sesión cerrada. Los audios exportados permanecen en disco.'
        self.render_account()
        if revoked is not None:
            self.app.notify('Sesión cerrada.' if revoked else 'Sesión borrada de este equipo; Aurora no confirmó la revocación remota.')
