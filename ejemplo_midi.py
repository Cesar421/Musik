from music21 import stream, note, midi

# Crear una melodía simple
melody = ["E5", "G5", "C6", "B5", "G5", "G5", "F5", "E5", "F5", "D5", "E5", "D5", "C5", "D5", "E5", "F5", "G5", "A5", "B5", "C6"]
s = stream.Stream()
for p in melody:
    n = note.Note(p)
    n.quarterLength = 0.5
    s.append(n)

# Guardar como MIDI
s.write('midi', fp='ejemplo.mid')
print('Archivo ejemplo.mid generado')
