"""Stable bookmark identity, including escaped spaces and Vietnamese filenames."""
import hashlib

from PySide6.QtCore import QUrl


def resume_key(source):
    url = QUrl(source)
    canonical = url.toString(QUrl.FullyEncoded)
    return 'resume-v2/' + hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def read_resume(settings, source):
    key = resume_key(source)
    # v0.3 wrote QUrl's pretty-decoded URL but read Path.as_uri()'s encoded
    # URL. Read the old writer's key first, then migrate without deleting it.
    url = QUrl(source)
    candidates = [key]
    for legacy in (url.toString(), str(source)):
        candidates.append('resume/' + hashlib.sha256(legacy.encode('utf-8')).hexdigest())
    for candidate in candidates:
        if settings.contains(candidate):
            try:
                position = max(0, int(settings.value(candidate)))
            except (ValueError, TypeError):
                continue
            if candidate != key:
                settings.setValue(key, str(position))
            return position
    return 0


def write_resume(settings, source, position):
    # Decimal strings preserve full millisecond precision in Windows Registry
    # and INI settings, independently of a platform's QVariant integer width.
    settings.setValue(resume_key(source), str(max(0, int(position))))
