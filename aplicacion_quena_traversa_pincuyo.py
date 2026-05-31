#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 TALLER DE QUENAS & PINCUYOS  ·  Aplicación de escritorio (GUI)
============================================================================
Interfaz gráfica para diseñar quenas, pincuyos y flautas traversas en
cualquier afinación. Calcula el largo del tubo y la posición de cada agujero
(modelo Benade/Helmholtz) y los dibuja a escala, todo en tiempo real.

Solo usa la librería estándar de Python (tkinter + math).
Ejecutar con:   python3 taller_quenas_gui.py
============================================================================
"""

import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ===========================================================================
#  NÚCLEO ACÚSTICO  (Benade / Helmholtz)
# ===========================================================================

NOTAS_ES = ["Do", "Do#", "Re", "Re#", "Mi", "Fa",
            "Fa#", "Sol", "Sol#", "La", "La#", "Si"]
NOTAS_EN = ["C", "C#", "D", "D#", "E", "F",
            "F#", "G", "G#", "A", "A#", "B"]
ESCALAS = {"mayor": [0, 2, 4, 5, 7, 9, 11],
           "menor": [0, 2, 3, 5, 7, 8, 10]}
EMBOCADURA = {"quena": 0.1, "pincuyo": 1.5, "traversa": 2.3}

PRESETS = {
    "quena":    dict(nota="Sol", oct=4, dia=18.0, pared=3.0,
                     holes=[8, 7, 7.5, 8, 7.5, 8], material="Bambú / caña",
                     trasero=True, dia_tras=5.5),
    "pincuyo":  dict(nota="Re", oct=5, dia=16.0, pared=2.0,
                     holes=[5.5, 6, 6, 6, 6, 5.5], material="Bambú / caña",
                     trasero=False, dia_tras=5.0),
    "traversa": dict(nota="Re", oct=4, dia=19.0, pared=3.0,
                     holes=[6, 6.5, 7, 7, 6.5, 6], material="Madera dura",
                     trasero=False, dia_tras=5.0),
}

# Rango recomendado de Ø de los agujeros de digitación (mm) por instrumento
RANGO_AGUJEROS = {"quena": (7, 11), "pincuyo": (5, 7), "traversa": (6, 9)}

# Materiales: (espesor de pared sugerido min-max, nota de taller)
MATERIALES = {
    "Bambú / caña": ((2.5, 4.0),
        "Tradicional y cálido. Elige cañas rectas, secas y sin grietas; "
        "quema o lija los nudos internos y sella el interior con aceite de linaza."),
    "PVC": ((2.0, 3.0),
        "Económico y de afinación muy estable. Usa PVC de presión (no el fino de "
        "desagüe) y lija el interior para dejarlo liso."),
    "Madera dura": ((3.0, 5.0),
        "Palo santo, granadillo o jacarandá: sonido denso y proyectado. Requiere "
        "broca de precisión y sellado interno con aceite."),
    "Metal (aluminio/cobre)": ((1.0, 2.0),
        "Brillante y potente, de pared fina. Lima bien los bordes de los agujeros "
        "para que no corten."),
    "Hueso / asta": ((2.0, 3.0),
        "Tradicional andino, timbre peculiar. Material duro: usa herramientas finas "
        "y avanza despacio."),
}


def embocadura_specs(instrumento, D):
    """Dimensiones sugeridas de la embocadura, escaladas con el Ø interno D (mm).
    Son puntos de partida artesanales; el ajuste fino es por oído."""
    instrumento = instrumento.lower()
    if instrumento == "quena":
        return [
            ("Tipo", "Muesca (bisel/escotadura) en el extremo abierto por donde se sopla"),
            ("Forma", "U o V; filo trasero biselado 30–45° hacia afuera"),
            ("Ancho del bisel", f"{0.62 * D:.1f} mm  (≈ 0,62 × Ø interno)"),
            ("Largo del bisel", f"{0.55 * D:.1f} mm  (≈ 0,55 × Ø interno)"),
            ("Filo de ataque", "Borde delantero afilado y limpio: ahí se parte el aire"),
            ("Agujero del pulgar", "En la cara trasera, pequeño (≈ 5–6 mm); ver tabla"),
        ]
    if instrumento == "pincuyo":
        return [
            ("Tipo", "Pico con canal de aire (fipple) y tapón, como una flauta dulce"),
            ("Tapón / block", f"Largo ≈ {1.5 * D:.0f} mm, ajustado al tubo, con cara plana"),
            ("Canal de aire (windway)", "Alto 0,8–1,2 mm, recto, liso y uniforme"),
            ("Ventana (boca)", f"Ancho ≈ {0.7 * D:.1f} mm × largo ≈ {0.9 * D:.1f} mm"),
            ("Labio (labium)", "Bisel afilado ≈ 15°, alineado con el canal de aire"),
        ]
    if instrumento == "traversa":
        return [
            ("Tipo", "Orificio oval en el costado, junto al extremo tapado"),
            ("Orificio de embocadura", f"Oval ≈ {0.55 * D:.1f} × {0.65 * D:.1f} mm"),
            ("Rebaje (undercut)", "Achaflana el orificio por dentro ≈ 7° para mejor timbre"),
            ("Chimenea", "Si la pared es gruesa, rebájala a 4–5 mm bajo la boca"),
        ]
    return []


def indice_nota(nombre):
    n = nombre.strip().capitalize()
    if n in NOTAS_ES:
        return NOTAS_ES.index(n)
    if n.upper() in NOTAS_EN:
        return NOTAS_EN.index(n.upper())
    raise ValueError(f"Nota desconocida: {nombre!r}")


def velocidad_sonido(temp_c):
    return 331.3 * math.sqrt(1.0 + temp_c / 273.15)


def frecuencia(midi_num):
    return 440.0 * (2.0 ** ((midi_num - 69) / 12.0))


def calcular_diseno(instrumento, nota, octava, escala,
                    dia_interno, espesor_pared, diametros, temp_c,
                    material="Bambú / caña", trasero=False, dia_trasero=5.5):
    """Devuelve un dict con toda la geometría del instrumento.

    `diametros` son los 6 Ø de los agujeros FRONTALES en orden físico:
    el [0] es el más cercano a la boca (nota más aguda) y el [5] el más
    lejano (nota más grave sobre la base).
    `trasero` activa el agujero del pulgar (octava), más cercano a la boca.
    """
    instrumento = instrumento.lower()
    v = velocidad_sonido(temp_c)
    R = (dia_interno / 1000.0) / 2.0
    t = espesor_pared / 1000.0

    base_idx = indice_nota(nota)
    base_midi = 12 * (octava + 1) + base_idx
    f_base = frecuencia(base_midi)

    L_ac = v / (2.0 * f_base)
    d_extremo = 0.613 * R
    d_emb = EMBOCADURA[instrumento] * R
    L_fis = L_ac - d_emb - d_extremo

    def posicion(midi_num, d_mm):
        """Posición física (m) del centro de un agujero desde el Punto 0."""
        f = frecuencia(midi_num)
        r = (d_mm / 1000.0) / 2.0
        t_ef = t + 1.5 * r
        C_h = t_ef * ((R / r) ** 2)
        return f, v / (2.0 * f) - C_h

    # Agujeros frontales en ORDEN FÍSICO (boca -> punta): grados de la escala
    # ordenados de la nota más aguda a la más grave.
    front_offsets = sorted(ESCALAS[escala][1:], reverse=True)  # p.ej. [11,9,7,5,4,2]

    spec = []  # (etiqueta, midi, diametro, es_trasero)
    if trasero:
        # agujero del pulgar = octava de la base (el más agudo y cercano a la boca)
        spec.append(("P", base_midi + 12, dia_trasero, True))
    for k, off in enumerate(front_offsets):
        spec.append((k + 1, base_midi + off, diametros[k], False))

    # calcular posiciones y ordenar por distancia a la boca
    calc = []
    for etq, m, d, tras in spec:
        f, pos = posicion(m, d)
        calc.append((etq, m, f, d, pos, tras))
    calc.sort(key=lambda x: x[4])

    agujeros, prev = [], 0.0
    for i, (etq, m, f, d, pos, tras) in enumerate(calc):
        pos_cm = pos * 100.0
        tramo = pos_cm if i == 0 else pos_cm - prev * 100.0
        agujeros.append(dict(etq=etq, nombre=NOTAS_ES[m % 12], freq=f,
                             diametro=d, pos_cm=pos_cm, tramo_cm=tramo,
                             trasero=tras))
        prev = pos

    avisos = []
    if L_fis <= 0:
        avisos.append("Ø interno demasiado grande para esa nota.")
    ant = 0.0
    for i, a in enumerate(agujeros):
        if a["pos_cm"] <= 0:
            avisos.append(f"Agujero {a['etq']} ({a['nombre']}): posición imposible.")
        if i > 0 and a["pos_cm"] <= ant:
            avisos.append(f"Los agujeros {agujeros[i-1]['etq']} y {a['etq']} se solapan.")
        ant = a["pos_cm"]
    if agujeros and agujeros[-1]["pos_cm"] >= L_fis * 100.0:
        avisos.append("El último agujero cae fuera del tubo.")

    pared_min, pared_max = MATERIALES.get(material, ((2, 4), ""))[0]
    rango = RANGO_AGUJEROS.get(instrumento, (5, 10))

    return dict(
        instrumento=instrumento,
        nota_base=f"{NOTAS_ES[base_midi % 12]}{octava}",
        escala=escala, dia=dia_interno, pared=espesor_pared,
        temp=temp_c, v=v, f_base=f_base,
        largo_cm=L_fis * 100.0,
        tapon_cm=(d_emb * 100.0) if instrumento != "quena" else 0.0,
        agujeros=agujeros, avisos=avisos, trasero=trasero,
        material=material,
        material_nota=MATERIALES.get(material, ((0, 0), ""))[1],
        pared_sugerida=(pared_min, pared_max),
        rango_agujeros=rango,
        embocadura=embocadura_specs(instrumento, dia_interno),
    )


def plano_texto(d):
    s = f"PLANO — {d['instrumento'].upper()} en {d['nota_base']} {d['escala']}\n"
    s += "=" * 64 + "\n"
    s += f"Ø interno {d['dia']} mm | pared {d['pared']} mm | {d['temp']}°C "
    s += f"(v={d['v']:.1f} m/s)\n"
    s += f"Largo de la boca al final: {d['largo_cm']:.2f} cm "
    s += "(corta 1-2 cm más largo)\n"
    if d["instrumento"] != "quena":
        s += f"Tapón trasero: {d['tapon_cm']:.2f} cm detrás del Punto 0\n"
    s += "-" * 64 + "\n"
    s += f"{'Aguj':<5}{'Nota':<6}{'Frec':>9}{'Ø mm':>7}{'Boca cm':>10}{'Tramo':>9}\n"
    for a in d["agujeros"]:
        marca = " (trasero/pulgar)" if a.get("trasero") else ""
        s += (f"{str(a['etq']):<5}{a['nombre']:<6}{a['freq']:>9.1f}{a['diametro']:>7.1f}"
              f"{a['pos_cm']:>10.2f}{a['tramo_cm']:>9.2f}{marca}\n")
    tf = d["largo_cm"] - d["agujeros"][-1]["pos_cm"]
    s += f"{'—':<5}{'Final':<6}{d['f_base']:>9.1f}{'—':>7}{d['largo_cm']:>10.2f}{tf:>9.2f}\n"
    s += "=" * 64 + "\n"
    s += "Medidas desde el Punto 0 (centro de la embocadura).\n\n"

    s += "FABRICACIÓN\n" + "-" * 64 + "\n"
    s += f"Material: {d['material']}\n"
    s += f"Espesor de pared sugerido: {d['pared_sugerida'][0]:.1f}-{d['pared_sugerida'][1]:.1f} mm\n"
    s += f"Ø de agujeros recomendado: {d['rango_agujeros'][0]}-{d['rango_agujeros'][1]} mm\n"
    if d.get("material_nota"):
        s += f"Nota material: {d['material_nota']}\n"
    s += "\nEMBOCADURA\n" + "-" * 64 + "\n"
    for etq, val in d["embocadura"]:
        s += f"  {etq}: {val}\n"
    s += "=" * 64 + "\n"
    return s


# ===========================================================================
#  PALETA Y FUENTES
# ===========================================================================

COL = dict(
    paper="#f3e9d8", card="#f8f1e3", ink="#2a241e", soft="#5c5347",
    line="#cbbda3", terra="#b5462a", terra_d="#90341e", teal="#2c635c",
    ochre="#c0902f", field="#fffaf0", tube="#efe2c7",
)
F_DISPLAY = ("Georgia", 22, "bold")
F_H = ("Consolas", 9, "bold")
F_BODY = ("Georgia", 11)
F_MONO = ("Consolas", 10)
F_BIG = ("Georgia", 20, "bold")


# ===========================================================================
#  APLICACIÓN
# ===========================================================================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Taller de Quenas & Pincuyos · Diseñador acústico")
        self.configure(bg=COL["paper"])
        self.geometry("1060x720")
        self.minsize(940, 640)
        self.ultimo = None

        self._estilos()
        self._variables()
        self._layout()
        self._cargar_preset()      # dispara el primer cálculo

    # ---- estilo ttk ----
    def _estilos(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", background=COL["card"], foreground=COL["ink"],
                     font=F_BODY)
        st.configure("Card.TFrame", background=COL["card"])
        st.configure("Paper.TFrame", background=COL["paper"])
        st.configure("TLabel", background=COL["card"], foreground=COL["ink"])
        st.configure("Soft.TLabel", background=COL["card"],
                     foreground=COL["soft"], font=F_H)
        st.configure("TCombobox", fieldbackground=COL["field"],
                     background=COL["field"])
        st.configure("Treeview", background=COL["field"],
                     fieldbackground=COL["field"], foreground=COL["ink"],
                     font=F_MONO, rowheight=24, borderwidth=0)
        st.configure("Treeview.Heading", background=COL["ink"],
                     foreground=COL["paper"], font=F_H, relief="flat")
        st.map("Treeview", background=[("selected", COL["ochre"])])
        st.configure("TButton", font=F_H, padding=6)
        st.configure("TNotebook", background=COL["paper"], borderwidth=0)
        st.configure("TNotebook.Tab", background=COL["paper"],
                     foreground=COL["soft"], font=F_H, padding=(16, 7))
        st.map("TNotebook.Tab",
               background=[("selected", COL["card"])],
               foreground=[("selected", COL["terra"])])

    # ---- variables ----
    def _variables(self):
        self.v_instr = tk.StringVar(value="quena")
        self.v_nota = tk.StringVar()
        self.v_oct = tk.StringVar()
        self.v_escala = tk.StringVar(value="mayor")
        self.v_dia = tk.StringVar()
        self.v_pared = tk.StringVar()
        self.v_temp = tk.StringVar(value="27")
        self.v_material = tk.StringVar(value="Bambú / caña")
        self.v_holes = [tk.StringVar() for _ in range(6)]
        self.v_trasero = tk.BooleanVar(value=True)
        self.v_dia_tras = tk.StringVar(value="5.5")
        # recálculo en vivo
        for var in ([self.v_nota, self.v_oct, self.v_escala, self.v_dia,
                     self.v_pared, self.v_temp, self.v_material,
                     self.v_trasero, self.v_dia_tras] + self.v_holes):
            var.trace_add("write", lambda *_: self._recalcular())

    # ---- layout ----
    def _layout(self):
        cab = ttk.Frame(self, style="Paper.TFrame")
        cab.pack(fill="x", padx=18, pady=(14, 6))
        tk.Label(cab, text="Taller de Quenas & Pincuyos", font=F_DISPLAY,
                 bg=COL["paper"], fg=COL["ink"]).pack(anchor="w")
        tk.Label(cab, text="DISEÑADOR ACÚSTICO · MODELO BENADE–HELMHOLTZ",
                 font=("Consolas", 9), bg=COL["paper"], fg=COL["terra"]).pack(anchor="w")

        cont = ttk.Frame(self, style="Paper.TFrame")
        cont.pack(fill="both", expand=True, padx=18, pady=8)

        # --- panel de controles ---
        ctrl = tk.Frame(cont, bg=COL["card"], highlightbackground=COL["line"],
                        highlightthickness=1)
        ctrl.pack(side="left", fill="y", padx=(0, 14))
        self._panel_controles(ctrl)

        # --- panel de resultados ---
        res = ttk.Frame(cont, style="Paper.TFrame")
        res.pack(side="left", fill="both", expand=True)
        self._panel_resultados(res)

    def _titulo_panel(self, parent, texto):
        f = tk.Frame(parent, bg=COL["card"])
        f.pack(fill="x", padx=14, pady=(12, 8))
        tk.Frame(f, bg=COL["terra"], width=8, height=8).pack(side="left", pady=3)
        tk.Label(f, text=texto, font=F_H, bg=COL["card"], fg=COL["teal"]
                 ).pack(side="left", padx=8)

    def _campo(self, parent, etiqueta):
        tk.Label(parent, text=etiqueta.upper(), font=("Consolas", 8),
                 bg=COL["card"], fg=COL["soft"]).pack(anchor="w", padx=14)

    def _panel_controles(self, p):
        self._titulo_panel(p, "PARÁMETROS DE DISEÑO")

        self._campo(p, "Instrumento")
        cb = ttk.Combobox(p, textvariable=self.v_instr, state="readonly",
                          values=["quena", "pincuyo", "traversa"], width=24)
        cb.pack(padx=14, pady=(0, 10))
        cb.bind("<<ComboboxSelected>>", lambda *_: self._cargar_preset())

        fila = tk.Frame(p, bg=COL["card"]); fila.pack(fill="x", padx=14)
        for col, (lbl, var, vals, w) in enumerate([
                ("Nota base", self.v_nota, NOTAS_ES, 7),
                ("Octava", self.v_oct, ["2", "3", "4", "5", "6"], 4),
                ("Escala", self.v_escala, ["mayor", "menor"], 7)]):
            c = tk.Frame(fila, bg=COL["card"]); c.grid(row=0, column=col, padx=(0, 6))
            tk.Label(c, text=lbl.upper(), font=("Consolas", 8), bg=COL["card"],
                     fg=COL["soft"]).pack(anchor="w")
            ttk.Combobox(c, textvariable=var, state="readonly",
                         values=vals, width=w).pack()

        fila2 = tk.Frame(p, bg=COL["card"]); fila2.pack(fill="x", padx=14, pady=(10, 0))
        for col, (lbl, var) in enumerate([("Ø interno (mm)", self.v_dia),
                                          ("Espesor pared (mm)", self.v_pared)]):
            c = tk.Frame(fila2, bg=COL["card"]); c.grid(row=0, column=col, padx=(0, 8))
            tk.Label(c, text=lbl.upper(), font=("Consolas", 8), bg=COL["card"],
                     fg=COL["soft"]).pack(anchor="w")
            tk.Entry(c, textvariable=var, width=11, font=F_MONO,
                     bg=COL["field"], relief="solid", bd=1).pack()

        self._campo(p, "Temperatura del aire (°C)")
        tk.Entry(p, textvariable=self.v_temp, width=10, font=F_MONO,
                 bg=COL["field"], relief="solid", bd=1).pack(anchor="w", padx=14)
        self.lbl_v = tk.Label(p, text="", font=("Georgia", 9, "italic"),
                              bg=COL["card"], fg=COL["soft"])
        self.lbl_v.pack(anchor="w", padx=14, pady=(2, 8))

        self._campo(p, "Material")
        ttk.Combobox(p, textvariable=self.v_material, state="readonly",
                     values=list(MATERIALES.keys()), width=24).pack(
                     anchor="w", padx=14, pady=(0, 8))

        self._campo(p, "Ø de cada agujero (mm) · de la boca a la punta")
        grid = tk.Frame(p, bg=COL["card"]); grid.pack(padx=14, pady=(2, 6))
        self.lbl_holes = []
        for i in range(6):
            cell = tk.Frame(grid, bg=COL["card"], highlightbackground=COL["line"],
                            highlightthickness=1)
            cell.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="w")
            lab = tk.Label(cell, text=f"Agujero {i+1}", font=("Consolas", 8),
                           bg=COL["card"], fg=COL["terra"])
            lab.pack(anchor="w", padx=4)
            self.lbl_holes.append(lab)
            tk.Entry(cell, textvariable=self.v_holes[i], width=8, font=F_MONO,
                     bg=COL["field"], relief="flat").pack(padx=4, pady=(0, 3))

        # --- agujero trasero (pulgar) ---
        tras = tk.Frame(p, bg=COL["card"]); tras.pack(fill="x", padx=14, pady=(6, 2))
        chk = tk.Checkbutton(tras, text="Agujero trasero (pulgar)",
                             variable=self.v_trasero, bg=COL["card"], fg=COL["ink"],
                             activebackground=COL["card"], font=("Georgia", 10),
                             selectcolor=COL["field"], anchor="w")
        chk.pack(side="left")
        tk.Label(tras, text="Ø", font=("Consolas", 9), bg=COL["card"],
                 fg=COL["soft"]).pack(side="left", padx=(8, 2))
        tk.Entry(tras, textvariable=self.v_dia_tras, width=6, font=F_MONO,
                 bg=COL["field"], relief="solid", bd=1).pack(side="left")
        tk.Label(p, text="La octava aguda, en la cara trasera. Obligatorio en quena; "
                 "opcional en pincuyo.", font=("Georgia", 8, "italic"),
                 bg=COL["card"], fg=COL["soft"], wraplength=300,
                 justify="left").pack(anchor="w", padx=14)

        ttk.Button(p, text="Guardar plano (.txt)",
                   command=self._guardar).pack(padx=14, pady=14, fill="x")

    def _panel_resultados(self, p):
        nb = ttk.Notebook(p)
        nb.pack(fill="both", expand=True)

        tab_dis = tk.Frame(nb, bg=COL["paper"])
        tab_fab = tk.Frame(nb, bg=COL["paper"])
        nb.add(tab_dis, text="  Diseño  ")
        nb.add(tab_fab, text="  Fabricación  ")

        self._tab_diseno(tab_dis)
        self._tab_fabricacion(tab_fab)

    def _tab_diseno(self, p):
        # tarjeta resumen
        card = tk.Frame(p, bg=COL["card"], highlightbackground=COL["line"],
                        highlightthickness=1)
        card.pack(fill="x", pady=(8, 0))
        self._titulo_panel(card, "RESULTADO")
        self.lbl_res_title = tk.Label(card, text="", font=("Georgia", 13, "bold"),
                                      bg=COL["card"], fg=COL["ink"])
        self.lbl_res_title.pack(anchor="w", padx=14)
        sumf = tk.Frame(card, bg=COL["card"]); sumf.pack(fill="x", padx=14, pady=10)
        self.lbl_largo = self._stat(sumf, 0, "Largo boca→final")
        self.lbl_base = self._stat(sumf, 1, "Nota base")
        self.lbl_vsum = self._stat(sumf, 2, "Vel. sonido")

        self.lbl_avisos = tk.Label(card, text="", font=("Georgia", 10),
                                   bg=COL["card"], fg=COL["terra_d"],
                                   wraplength=560, justify="left")
        self.lbl_avisos.pack(anchor="w", padx=14)
        # el texto de avisos se reajusta al ancho de la tarjeta
        card.bind("<Configure>",
                  lambda e: self.lbl_avisos.config(wraplength=max(e.width - 40, 200)))

        # tabla (columnas que se ensanchan con la ventana)
        cols = ("n", "nota", "freq", "dia", "pos", "tramo")
        self.tree = ttk.Treeview(card, columns=cols, show="headings", height=7)
        for c, txt, w in [("n", "Aguj", 60), ("nota", "Nota", 80),
                          ("freq", "Frec(Hz)", 110), ("dia", "Ø mm", 80),
                          ("pos", "Desde boca", 140), ("tramo", "Tramo", 120)]:
            self.tree.heading(c, text=txt)
            self.tree.column(c, width=w, anchor="center", stretch=True)
        self.tree.pack(fill="x", padx=14, pady=(4, 12))
        self.tree.tag_configure("fin", background="#e7ecdf")

        # diagrama
        dia = tk.Frame(p, bg=COL["card"], highlightbackground=COL["line"],
                       highlightthickness=1)
        dia.pack(fill="both", expand=True, pady=(12, 8))
        self._titulo_panel(dia, "PLANO A ESCALA")
        self.canvas = tk.Canvas(dia, bg=COL["card"], height=250,
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.canvas.bind("<Configure>", lambda *_: self._dibujar())

        tk.Label(dia, text="Punto 0 = centro de la embocadura · corta el tubo "
                 "1-2 cm más largo y afina recortando",
                 font=("Georgia", 9, "italic"), bg=COL["card"],
                 fg=COL["soft"]).pack(anchor="w", padx=14, pady=(0, 8))

    def _tab_fabricacion(self, p):
        # Tarjeta: embocadura
        emb = tk.Frame(p, bg=COL["card"], highlightbackground=COL["line"],
                       highlightthickness=1)
        emb.pack(fill="x", pady=(8, 0))
        self._titulo_panel(emb, "EMBOCADURA")
        self.fab_emb = tk.Frame(emb, bg=COL["card"])
        self.fab_emb.pack(fill="x", padx=14, pady=(0, 12))

        # Tarjeta: material y dimensiones
        mat = tk.Frame(p, bg=COL["card"], highlightbackground=COL["line"],
                       highlightthickness=1)
        mat.pack(fill="x", pady=(12, 0))
        self._titulo_panel(mat, "MATERIAL Y DIMENSIONES")
        self.fab_mat = tk.Frame(mat, bg=COL["card"])
        self.fab_mat.pack(fill="x", padx=14, pady=(0, 12))
        self.lbl_mat_nota = tk.Label(mat, text="", font=("Georgia", 10, "italic"),
                                     bg=COL["card"], fg=COL["soft"],
                                     wraplength=560, justify="left")
        self.lbl_mat_nota.pack(anchor="w", padx=14, pady=(0, 12))
        mat.bind("<Configure>",
                 lambda e: self.lbl_mat_nota.config(wraplength=max(e.width - 40, 200)))

        # Tarjeta: notas generales de construcción
        gen = tk.Frame(p, bg=COL["card"], highlightbackground=COL["line"],
                       highlightthickness=1)
        gen.pack(fill="both", expand=True, pady=(12, 8))
        self._titulo_panel(gen, "NOTAS DE CONSTRUCCIÓN")
        notas = (
            "• Perfora cada agujero con broca más pequeña y agrándalo escuchando "
            "un afinador hasta dar la nota.\n"
            "• Limpia y bisela ligeramente el borde interior de cada agujero.\n"
            "• Bore (interior) cilíndrico y bien liso: cualquier rebaba desafina y "
            "ensucia el timbre.\n"
            "• La quena tradicional suele llevar además un 7º agujero de pulgar en la "
            "parte trasera (opcional).\n"
            "• Sella el interior según el material (aceite en bambú y madera) para "
            "estabilizar la afinación con la humedad del aliento.\n"
            "• Marca primero todos los centros con lápiz y verifica las distancias "
            "antes de taladrar."
        )
        lbl = tk.Label(gen, text=notas, font=("Georgia", 10), bg=COL["card"],
                       fg=COL["ink"], wraplength=560, justify="left")
        lbl.pack(anchor="w", padx=14, pady=(0, 12))
        gen.bind("<Configure>",
                 lambda e: lbl.config(wraplength=max(e.width - 40, 200)))

    def _fila_dato(self, parent, etiqueta, valor):
        f = tk.Frame(parent, bg=COL["card"]); f.pack(fill="x", pady=2)
        tk.Label(f, text=etiqueta, font=F_H, bg=COL["card"], fg=COL["teal"],
                 width=22, anchor="w").pack(side="left")
        tk.Label(f, text=valor, font=("Georgia", 10), bg=COL["card"],
                 fg=COL["ink"], justify="left", anchor="w",
                 wraplength=380).pack(side="left", fill="x", expand=True)

    def _stat(self, parent, col, etiqueta):
        f = tk.Frame(parent, bg=COL["card"])
        f.grid(row=0, column=col, padx=(0, 26), sticky="w")
        tk.Label(f, text=etiqueta.upper(), font=("Consolas", 8),
                 bg=COL["card"], fg=COL["soft"]).pack(anchor="w")
        val = tk.Label(f, text="—", font=F_BIG, bg=COL["card"], fg=COL["ink"])
        val.pack(anchor="w")
        return val

    # ---- lógica ----
    def _cargar_preset(self):
        pr = PRESETS[self.v_instr.get()]
        self.v_nota.set(pr["nota"]); self.v_oct.set(str(pr["oct"]))
        self.v_escala.set("mayor")
        self.v_dia.set(str(pr["dia"])); self.v_pared.set(str(pr["pared"]))
        self.v_material.set(pr["material"])
        self.v_trasero.set(pr.get("trasero", False))
        self.v_dia_tras.set(str(pr.get("dia_tras", 5.5)))
        for i, d in enumerate(pr["holes"]):
            self.v_holes[i].set(str(d))
        self._recalcular()

    def _leer(self):
        try:
            holes = [float(v.get()) for v in self.v_holes]
            if any(h <= 0 for h in holes):
                return None
            trasero = bool(self.v_trasero.get())
            dia_tras = float(self.v_dia_tras.get()) if trasero else 5.5
            if trasero and dia_tras <= 0:
                return None
            return calcular_diseno(
                self.v_instr.get(), self.v_nota.get(),
                int(self.v_oct.get()), self.v_escala.get(),
                float(self.v_dia.get()), float(self.v_pared.get()),
                holes, float(self.v_temp.get()), self.v_material.get(),
                trasero, dia_tras)
        except (ValueError, ZeroDivisionError):
            return None

    def _recalcular(self):
        d = self._leer()
        if not d:
            return
        self.ultimo = d
        self.lbl_res_title.config(
            text=f"{d['instrumento'].upper()} en {d['nota_base']} {d['escala']}")
        self.lbl_largo.config(text=f"{d['largo_cm']:.2f} cm")
        self.lbl_base.config(text=d["nota_base"], font=("Georgia", 16, "bold"))
        self.lbl_vsum.config(text=f"{d['v']:.0f} m/s", font=("Georgia", 16, "bold"))
        self.lbl_v.config(text=f"Velocidad del sonido: {d['v']:.1f} m/s")

        # etiquetas de los 6 agujeros FRONTALES (en orden boca->punta)
        frontales = [a for a in d["agujeros"] if not a.get("trasero")]
        for i, a in enumerate(frontales):
            self.lbl_holes[i].config(text=f"Agujero {a['etq']} · {a['nombre']}")

        # avisos
        if d["avisos"]:
            self.lbl_avisos.config(text="⚠ " + "  ".join(d["avisos"]))
        else:
            self.lbl_avisos.config(text="")

        # tabla
        self.tree.delete(*self.tree.get_children())
        self.tree.tag_configure("tras", background="#efe2c7")
        for a in d["agujeros"]:
            etq = f"{a['etq']} ↩" if a.get("trasero") else str(a["etq"])
            tags = ("tras",) if a.get("trasero") else ()
            self.tree.insert("", "end", tags=tags, values=(
                etq, a["nombre"], f"{a['freq']:.1f}", f"{a['diametro']:.1f}",
                f"{a['pos_cm']:.2f} cm", f"{a['tramo_cm']:.2f} cm"))
        tf = d["largo_cm"] - d["agujeros"][-1]["pos_cm"]
        self.tree.insert("", "end", tags=("fin",), values=(
            "—", "Final", f"{d['f_base']:.1f}", "—",
            f"{d['largo_cm']:.2f} cm", f"{tf:.2f} cm"))

        self._dibujar()
        self._actualizar_fabricacion(d)

    def _actualizar_fabricacion(self, d):
        # embocadura
        for w in self.fab_emb.winfo_children():
            w.destroy()
        for etq, val in d["embocadura"]:
            self._fila_dato(self.fab_emb, etq, val)

        # material y dimensiones
        for w in self.fab_mat.winfo_children():
            w.destroy()
        pmin, pmax = d["pared_sugerida"]
        amin, amax = d["rango_agujeros"]
        self._fila_dato(self.fab_mat, "Material", d["material"])
        self._fila_dato(self.fab_mat, "Espesor de pared",
                        f"{d['pared']:.1f} mm  (sugerido {pmin:.1f}–{pmax:.1f} mm)")
        self._fila_dato(self.fab_mat, "Ø interno del tubo", f"{d['dia']:.1f} mm")
        self._fila_dato(self.fab_mat, "Ø de agujeros (rango)",
                        f"{amin}–{amax} mm")
        if d["instrumento"] != "quena":
            self._fila_dato(self.fab_mat, "Tapón trasero",
                            f"{d['tapon_cm']:.2f} cm detrás del Punto 0")
        self.lbl_mat_nota.config(text=d.get("material_nota", ""))

    def _dibujar(self):
        c = self.canvas
        c.delete("all")
        d = self.ultimo
        if not d:
            return
        Lcm = d["largo_cm"]
        if Lcm <= 0:
            return

        # ── dimensiones que se adaptan al canvas ──────────────────────────
        W  = max(c.winfo_width(), 480)
        H  = max(c.winfo_height(), 200)
        padX  = 68
        tubeH = min(max(H * 0.18, 44), 72)   # alto del rectángulo del tubo
        scale = (W - padX * 2) / Lcm          # px/cm
        x0, x1 = padX, padX + Lcm * scale
        # centra el tubo dejando espacio arriba (etiquetas) y abajo (trasero+regla)
        cy = H * 0.42
        y  = cy - tubeH / 2                   # borde superior del tubo

        espacio_arr  = y - 6                  # px disponibles arriba del tubo
        espacio_aba  = H - (y + tubeH) - 4   # px disponibles debajo

        # ── tapón (pincuyo / traversa) ────────────────────────────────────
        if d["instrumento"] != "quena":
            sx = x0 - d["tapon_cm"] * scale
            c.create_rectangle(sx, y + 8, x0, y + tubeH - 8,
                               fill=COL["ochre"], outline=COL["terra_d"], width=1)
            c.create_text((sx + x0) / 2, y - 10, text="tapón",
                         fill=COL["terra_d"], font=("Consolas", 8))

        # ── cuerpo del tubo ───────────────────────────────────────────────
        c.create_rectangle(x0, y, x1, y + tubeH,
                           fill=COL["tube"], outline=COL["ink"], width=2)
        c.create_line(x0, cy, x1, cy, fill=COL["line"], dash=(4, 4))

        # ── embocadura ────────────────────────────────────────────────────
        r_emb = 8
        c.create_oval(x0 - r_emb, cy - r_emb, x0 + r_emb, cy + r_emb,
                     fill=COL["terra"], outline="white", width=2)
        c.create_text(x0, y - 14, text="0 · boca",
                     fill=COL["terra"], font=("Consolas", 9, "bold"))
        c.create_text(x1 + 4, y - 14, text=f"{Lcm:.1f} cm",
                     fill=COL["ink"], font=("Consolas", 9), anchor="w")

        # ── agujeros ──────────────────────────────────────────────────────
        # Separamos frontales y el trasero (pulgar)
        frontales = [a for a in d["agujeros"] if not a.get("trasero")]
        traseros  = [a for a in d["agujeros"] if     a.get("trasero")]

        rad_max = tubeH / 2 - 4

        # Frontales: etiquetas alternadas arriba/abajo
        lbl_espacio = 30           # px mínimo entre el tubo y la primera etiqueta
        filas_arr = max(2, int(espacio_arr / 13))   # cuántas filas caben arriba
        for fi, a in enumerate(frontales):
            hx  = x0 + a["pos_cm"] * scale
            rad = min(max((a["diametro"] / 10.0) * scale / 2.0, 3), rad_max)
            c.create_oval(hx - rad, cy - rad, hx + rad, cy + rad,
                         fill=COL["ink"], outline=COL["soft"], width=1)

            up   = (fi % 2 == 0)
            if up:
                lbl_y  = y - lbl_espacio
                nota_y = lbl_y - 13
                ln_y1, ln_y2 = y - 2, lbl_y + 2
            else:
                lbl_y  = y + tubeH + lbl_espacio
                nota_y = lbl_y + 13
                ln_y1, ln_y2 = y + tubeH + 2, lbl_y - 2

            c.create_line(hx, ln_y1, hx, ln_y2, fill=COL["teal"], width=1)
            c.create_text(hx, nota_y, text=a["nombre"],
                         fill=COL["teal"], font=("Georgia", 10, "bold"))
            c.create_text(hx, lbl_y,  text=f"{a['pos_cm']:.1f}",
                         fill=COL["soft"], font=("Consolas", 8))

        # Trasero (pulgar): dibujado DEBAJO del tubo con color distinto
        for a in traseros:
            hx  = x0 + a["pos_cm"] * scale
            rad = min(max((a["diametro"] / 10.0) * scale / 2.0, 3), rad_max)
            # círculo con borde color tierra para distinguirlo
            c.create_oval(hx - rad, cy - rad, hx + rad, cy + rad,
                         fill=COL["terra_d"], outline=COL["ochre"], width=2)
            # etiqueta siempre abajo (cara trasera)
            lbl_y  = y + tubeH + lbl_espacio + 22
            nota_y = lbl_y + 13
            c.create_line(hx, y + tubeH + 2, hx, lbl_y - 2,
                         fill=COL["terra"], dash=(3, 3), width=1)
            c.create_text(hx, nota_y, text=f"↩ {a['nombre']}",
                         fill=COL["terra"], font=("Georgia", 9, "bold"))
            c.create_text(hx, lbl_y,  text=f"{a['pos_cm']:.1f}",
                         fill=COL["soft"], font=("Consolas", 8))

        # ── leyenda ───────────────────────────────────────────────────────
        if traseros:
            c.create_text(x0, H - 8, anchor="w",
                         text="● frente   ● trasero/pulgar",
                         fill=COL["soft"], font=("Consolas", 8))

        # ── regla ─────────────────────────────────────────────────────────
        ry = min(y + tubeH + 56, H - 18)
        c.create_line(x0, ry, x1, ry, fill=COL["ink"])
        cm_mark = 0
        while cm_mark <= Lcm:
            tx = x0 + cm_mark * scale
            h_tick = 6 if cm_mark % 10 == 0 else 3
            c.create_line(tx, ry - h_tick, tx, ry + h_tick, fill=COL["ink"])
            if cm_mark % 5 == 0:
                c.create_text(tx, ry + 14, text=str(cm_mark),
                             fill=COL["soft"], font=("Consolas", 7))
            cm_mark += 5

    def _guardar(self):
        if not self.ultimo:
            return
        nombre = f"plano_{self.ultimo['instrumento']}_{self.ultimo['nota_base']}.txt"
        ruta = filedialog.asksaveasfilename(
            defaultextension=".txt", initialfile=nombre,
            filetypes=[("Texto", "*.txt")])
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(plano_texto(self.ultimo))
            messagebox.showinfo("Guardado", f"Plano guardado en:\n{ruta}")


if __name__ == "__main__":
    App().mainloop()