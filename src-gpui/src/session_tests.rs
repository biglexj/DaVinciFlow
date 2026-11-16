use super::*;

fn document() -> Document {
    subtitles::parse("1\n00:00:01,001 --> 00:00:02,009\nHola, Ely\n\n2\n00:00:03,010 --> 00:00:04,011\n¡Qué tal!", "captura".into()).unwrap()
}
fn session() -> SubtitleSession {
    let mut session = SubtitleSession::default();
    session.load(document()).unwrap();
    session
}
fn edit(session: &mut SubtitleSession, text: &str) {
    session.set_draft(text.into());
    session.save_draft().unwrap();
}
fn receipt(snapshot: ExportSnapshot) -> ExportReceipt {
    ExportReceipt {
        document_id: snapshot.document_id,
        revision: snapshot.revision,
        texts: snapshot.texts,
        path: PathBuf::from("unit-test-only.srt"),
    }
}

#[test]
fn load_rejects_unsaved_text_and_draft_without_losing_either() {
    let mut s = session();
    s.set_draft("Edición pendiente".into());
    assert!(s.load(document()).is_err());
    assert_eq!(s.draft(), "Edición pendiente");
    s.save_draft().unwrap();
    assert!(s.load(document()).is_err());
    assert_eq!(s.document().cues[0].text, "Edición pendiente");
    s.undo().unwrap();
    s.load(document()).unwrap();
    assert!(!s.is_dirty());
}

#[test]
fn failed_load_validates_before_replacing_the_current_source() {
    let mut s = session();
    assert!(s.load(Document::default()).is_err());
    let mut invalid = document();
    invalid.cues[0].end_ms = 0;
    assert!(s.load(invalid).is_err());
    assert_eq!(s.document().cues.len(), 2);
    assert_eq!(s.draft(), "Hola, Ely");
}

#[test]
fn selection_preserves_pending_draft_and_rejects_invalid_indices() {
    let mut s = session();
    s.set_draft("Pendiente".into());
    assert!(s.select(1).is_err());
    assert!(s.select(99).is_err());
    s.select(0).unwrap();
    assert_eq!(s.draft(), "Pendiente");
    s.discard_draft();
    s.select(1).unwrap();
    assert_eq!(s.draft(), "¡Qué tal!");
}

#[test]
fn editing_is_undoable_and_never_changes_timing_or_originals() {
    let mut s = session();
    let before = s.document().cues.clone();
    s.set_draft(" \n ¡Hola, Ely! \r\n\r\n ¿Qué tal? \n ".into());
    assert_eq!(s.save_draft().unwrap(), 1);
    assert_eq!(s.draft(), "¡Hola, Ely!\n¿Qué tal?");
    assert!(s.is_dirty());
    assert_eq!(s.document().cues[0].start_ms, 1001);
    assert_eq!(s.document().cues[0].end_ms, 2009);
    assert_eq!(s.document().cues[0].original, before[0].original);
    s.undo().unwrap();
    assert_eq!(s.document().cues, before);
    assert!(!s.is_dirty());
    s.redo().unwrap();
    assert!(s.is_dirty());
}

#[test]
fn an_empty_edit_stays_available_for_correction() {
    let mut s = session();
    s.set_draft("  \r\n ".into());
    assert!(s.save_draft().is_err());
    assert!(s.has_draft());
    assert!(!s.is_dirty());
    assert_eq!(s.document().cues[0].text, "Hola, Ely");
    assert!(!s.can_undo());
}

#[test]
fn batch_failure_does_not_write_partial_changes_or_erase_history() {
    let mut s = session();
    edit(&mut s, "Hola, Ely corregido");
    assert!(s.replace("¡Qué tal!", "", true).is_err());
    assert_eq!(s.document().cues[0].text, "Hola, Ely corregido");
    assert_eq!(s.document().cues[1].text, "¡Qué tal!");
    assert!(s.can_undo());
    s.undo().unwrap();
    assert!(!s.is_dirty());
    assert!(s.replace("Ely", "nuevo\n\nbloque", true).is_err());
    assert!(!s.is_dirty());
}

#[test]
fn drafts_block_batch_undo_and_export() {
    let mut s = session();
    edit(&mut s, "Guardado");
    s.set_draft("Pendiente".into());
    assert!(s.normalize().is_err());
    assert!(s.replace("Hola", "Adiós", true).is_err());
    assert!(s.restore_all().is_err());
    assert!(s.undo().is_err());
    assert!(s.redo().is_err());
    assert!(s.export_snapshot().is_err());
    assert_eq!(s.draft(), "Pendiente");
}

#[test]
fn saving_the_same_text_does_not_destroy_redo() {
    let mut s = session();
    edit(&mut s, "Corregido");
    s.undo().unwrap();
    assert_eq!(s.save_draft().unwrap(), 0);
    assert!(s.can_redo());
    assert_eq!(s.replace("no existe", "irrelevante", true).unwrap(), 0);
    assert!(s.can_redo());
    s.redo().unwrap();
    assert_eq!(s.draft(), "Corregido");
}

#[test]
fn a_new_edit_clears_the_old_redo_branch() {
    let mut s = session();
    edit(&mut s, "Primera");
    s.undo().unwrap();
    edit(&mut s, "Otra rama");
    assert!(!s.can_redo());
    assert!(s.redo().is_err());
}

#[test]
fn restore_after_export_is_dirty_and_can_be_undone() {
    let mut s = session();
    edit(&mut s, "Exportado");
    s.accept_export(receipt(s.export_snapshot().unwrap()))
        .unwrap();
    assert!(!s.is_dirty());
    assert_eq!(s.restore_all().unwrap(), 1);
    assert!(s.is_dirty());
    s.undo().unwrap();
    assert!(!s.is_dirty());
    assert_eq!(s.draft(), "Exportado");
}

#[test]
fn a_late_export_does_not_clear_newer_edits_or_a_pending_draft() {
    let mut s = session();
    edit(&mut s, "Estado A");
    let snapshot = s.export_snapshot().unwrap();
    edit(&mut s, "Estado B");
    s.set_draft("Borrador C".into());
    s.accept_export(receipt(snapshot)).unwrap();
    assert!(s.is_dirty());
    assert!(s.has_draft());
    assert_eq!(s.draft(), "Borrador C");
    s.discard_draft();
    s.undo().unwrap();
    assert!(!s.is_dirty());
    assert_eq!(s.draft(), "Estado A");
}

#[test]
fn receipts_from_other_sessions_or_previous_loads_are_rejected() {
    let mut a = session();
    let mut b = session();
    assert!(
        b.accept_export(receipt(a.export_snapshot().unwrap()))
            .is_err()
    );
    let old = receipt(a.export_snapshot().unwrap());
    a.load(document()).unwrap();
    assert!(a.accept_export(old).is_err());
    assert!(!a.is_dirty());
}

#[test]
fn export_receipts_cannot_regress_the_last_confirmed_export() {
    let mut s = session();
    edit(&mut s, "Antiguo");
    let old = receipt(s.export_snapshot().unwrap());
    edit(&mut s, "Reciente");
    let new = receipt(s.export_snapshot().unwrap());
    s.accept_export(new).unwrap();
    assert!(s.accept_export(old).is_err());
    assert!(!s.is_dirty());
}

#[test]
fn history_is_bounded_and_uses_only_successful_text_changes() {
    let mut s = session();
    for i in 0..40 {
        edit(&mut s, &format!("Cambio {i}"));
    }
    let mut undos = 0;
    while s.can_undo() {
        s.undo().unwrap();
        undos += 1;
    }
    assert_eq!(undos, 32);
    assert_eq!(s.draft(), "Cambio 7");
}

#[test]
fn filtering_searches_both_original_and_current_text_in_spanish() {
    let mut s = session();
    edit(&mut s, "Completamente distinto");
    assert_eq!(s.filtered_indices("ELY"), vec![0]);
    assert_eq!(s.filtered_indices("QUÉ"), vec![1]);
    assert_eq!(s.filtered_indices("distinto"), vec![0]);
    assert_eq!(s.filtered_indices(""), vec![0, 1]);
}

#[test]
fn export_snapshot_is_sendable_and_produces_a_receipt_only_after_disk_write() {
    fn assert_send<T: Send>() {}
    assert_send::<ExportSnapshot>();
    assert_send::<ExportReceipt>();
    let mut s = session();
    edit(&mut s, "Exportación real: ¡qué tal!");
    let path = std::env::temp_dir().join(format!("df-session-export-{}.srt", std::process::id()));
    let receipt = s.export_snapshot().unwrap().save_new(&path).unwrap();
    assert_eq!(receipt.path(), path);
    assert_eq!(
        subtitles::load(&path).unwrap().cues[0].text,
        "Exportación real: ¡qué tal!"
    );
    s.accept_export(receipt).unwrap();
    assert!(!s.is_dirty());
    assert!(s.export_snapshot().unwrap().save_new(&path).is_err());
    std::fs::remove_file(path).unwrap();
}
