"""
Genera una partitura en PDF usando music21.
Ejecutar: C:/ProgramData/anaconda3/python.exe generar_partitura.py
"""

from music21 import stream, note, meter, tempo, metadata, clef, key

# --- Crear la partitura ---
score = stream.Score()
score.metadata = metadata.Metadata()
score.metadata.title = "Pequeño Vals en Do Mayor"
score.metadata.composer = "Cesar Fernando"

part = stream.Part()
part.id = "Piano"

# Clave de Sol, tonalidad Do Mayor, compás 3/4
part.append(clef.TrebleClef())
part.append(key.KeySignature(0))          # Do Mayor (sin sostenidos ni bemoles)
part.append(meter.TimeSignature("3/4"))
part.append(tempo.MetronomeMark(number=120, referent=note.Note(type="quarter")))

# --- Notas (notación: C4=Do central, D4=Re, etc.) ---
melodia = [
    # Compás 1
    ("E5", "quarter"), ("G5", "quarter"), ("C6", "quarter"),
    # Compás 2
    ("B5", "half"),    ("G5", "quarter"),
    # Compás 3
    ("G5", "quarter"), ("F5", "quarter"), ("E5", "quarter"),
    # Compás 4
    ("F5", "half"),    ("D5", "quarter"),
    # Compás 5
    ("E5", "quarter"), ("D5", "quarter"), ("C5", "quarter"),
    # Compás 6
    ("D5", "quarter"), ("E5", "quarter"), ("F5", "quarter"),
    # Compás 7
    ("G5", "quarter"), ("A5", "quarter"), ("B5", "quarter"),
    # Compás 8
    ("C6", "whole"),
]

for pitch, duration in melodia:
    n = note.Note(pitch)
    n.duration.type = duration
    part.append(n)

score.append(part)

# --- Exportar a PDF (requiere MuseScore o LilyPond instalado)
# Si no hay visor externo, se exporta a MusicXML y se abre en el navegador como texto
try:
    # Intentar exportar como PDF (necesita MuseScore instalado)
    fp = score.write("musicxml.pdf", fp="partitura.pdf")
    print(f"PDF generado: {fp}")
except Exception:
    # Fallback: exportar a MusicXML (abre con MuseScore, Finale, Sibelius, etc.)
    fp = score.write("musicxml", fp="partitura.xml")
    print(f"MusicXML generado: {fp}")
    print("Abre partitura.xml con MuseScore (https://musescore.org) para ver el PDF.")

    # También exportar como MIDI
    fp_midi = score.write("midi", fp="partitura.mid")
    print(f"MIDI generado: {fp_midi}")
