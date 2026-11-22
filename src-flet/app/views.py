"""Vistas importadas y construidas únicamente cuando se necesitan."""

from collections.abc import Mapping
from importlib import import_module

VIEW_TYPES = {
    'assistant': ('features.assistant.assistant_view', 'AssistantView', {}),
    'editor': ('features.editor.editor_view', 'EditorView', {}),
    'voice': ('features.voice.voice_view', 'VoiceView', {}),
    'sfx': ('features.sfx.sfx_view', 'SFXView', {}),
    'brolls': ('features.brolls.brolls_view', 'BRollsView', {}),
    'fetch': ('features.luna_fetch.fetch_view', 'FetchView', {}),
    'catalog': ('features.catalog.catalog_view', 'CatalogView', {}),
    'library': ('features.library.library_view', 'LibraryView', {}),
    'music': ('features.library.library_view', 'LibraryView', {'category': 'music'}),
    'subtitles': ('features.subtitles.subtitles_view', 'SubtitlesView', {}),
    'settings': ('features.settings.settings_view', 'SettingsView', {}),
    'updates': ('features.about.update_panel', 'UpdatePanel', {}),
}


class LazyViews(Mapping):
    def __init__(self, app):
        self.app = app
        self.loaded = {}

    def __getitem__(self, key):
        if key not in self.loaded:
            module, name, options = VIEW_TYPES[key]
            self.loaded[key] = getattr(import_module(module), name)(self.app, **options)
        return self.loaded[key]

    def __iter__(self):
        return (key for key in VIEW_TYPES if key != 'updates')

    def __len__(self):
        return len(VIEW_TYPES) - 1

    def __contains__(self, key):
        return key in VIEW_TYPES and key != 'updates'
