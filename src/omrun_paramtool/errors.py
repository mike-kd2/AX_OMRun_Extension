"""Zentrale Fehlertypen. Meldungen nennen Tokens/Dateien, keine Werte."""


class OMrunToolError(Exception):
    """Basisklasse fuer erwartbare, benutzerseitige Fehler (Exit-Code 2)."""


class ConfigNotFoundError(OMrunToolError):
    """Config-Wurzel, TestObject, .env oder .rtl nicht gefunden/mehrdeutig."""


class ResolutionError(OMrunToolError):
    """Platzhalter liess sich nicht aufloesen (z.B. Alias-Zyklus)."""


class DehydrateConflict(OMrunToolError):
    """Mehrdeutige Ersetzung beim Dehydrate (nur mit --force erzwingbar)."""
