# reports/pdf_report.py
import io
import datetime
import sqlite3
from typing import Dict, Tuple, List

import matplotlib.pyplot as plt

from db.init_db import get_connection
from db import crud


# ----------------------------
# Helpers de datos
# ----------------------------
def _fetch_session_bundle(session_id: int) -> Dict:
    """
    Devuelve un dict con datos de sesión + paciente + ejercicio.
    Keys:
      id, datetime, video_path, notes,
      patient_id, patient_name, patient_age, patient_gender,
      exercise_id, exercise_name
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
              s.id,
              s.timestamp AS datetime,
              s.video_path,
              s.notes,
              p.id   AS patient_id,
              p.name AS patient_name,
              p.age  AS patient_age,
              p.gender AS patient_gender,
              e.id   AS exercise_id,
              e.name AS exercise_name
            FROM sessions s
            LEFT JOIN patients  p ON p.id = s.patient_id
            LEFT JOIN exercises e ON e.id = s.exercise_id
            WHERE s.id = ?
            """,
            (session_id,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Sesión {session_id} no encontrada")
        return dict(row)


def _metrics_by_series(session_id: int) -> Dict[str, Dict[str, float]]:
    """
    Devuelve un mapa: { serie_base: {min: x, max: y, range: z} }
    a partir de filas (metric_name, metric_value, unit).
    """
    rows = crud.get_metrics_by_session(session_id) or []
    series: Dict[str, Dict[str, float]] = {}

    for name, value, unit in rows:
        if not isinstance(name, str):
            continue
        # Esperado: "<serie>_(min|max|range)"
        if name.endswith("_min"):
            base, key = name[:-4], "min"
        elif name.endswith("_max"):
            base, key = name[:-4], "max"
        elif name.endswith("_range"):
            base, key = name[:-6], "range"
        else:
            # ignorar otras métricas de depuración o nombres no estándar
            continue

        try:
            v = float(value) if value is not None else None
        except (TypeError, ValueError):
            v = None

        if v is None:
            continue

        series.setdefault(base, {})
        series[base][key] = v

    return series


# ----------------------------
# Gráficos (matplotlib)
# ----------------------------
def _figure_to_png_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _chart_ranges(series_map: Dict[str, Dict[str, float]]) -> bytes:
    """Gráfico de barras: range por serie."""
    labels, values = [], []
    for serie, stats in sorted(series_map.items()):
        if "range" in stats:
            labels.append(serie)
            values.append(stats["range"])

    if not labels:
        # gráfico vacío “placeholder”
        fig = plt.figure(figsize=(6, 3))
        plt.title("Rango por serie")
        plt.text(0.5, 0.5, "Sin datos de 'range'", ha="center", va="center")
        return _figure_to_png_bytes(fig)

    fig = plt.figure(figsize=(8, 4))
    plt.title("Rango por serie")
    plt.bar(labels, values)
    plt.ylabel("degrees")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    return _figure_to_png_bytes(fig)


def _chart_min_max(series_map: Dict[str, Dict[str, float]]) -> bytes:
    """Gráfico de barras dobles: min y max por serie."""
    labels, mins, maxs = [], [], []
    for serie, stats in sorted(series_map.items()):
        if "min" in stats or "max" in stats:
            labels.append(serie)
            mins.append(stats.get("min", 0.0))
            maxs.append(stats.get("max", 0.0))

    if not labels:
        fig = plt.figure(figsize=(6, 3))
        plt.title("Min y Max por serie")
        plt.text(0.5, 0.5, "Sin datos de 'min/max'", ha="center", va="center")
        return _figure_to_png_bytes(fig)

    import numpy as np
    x = np.arange(len(labels))
    width = 0.38

    fig = plt.figure(figsize=(8, 4))
    plt.title("Min y Max por serie")
    plt.bar(x - width / 2, mins, width, label="min")
    plt.bar(x + width / 2, maxs, width, label="max")
    plt.ylabel("degrees")
    plt.xticks(x, labels, rotation=20, ha="right")
    plt.legend()
    plt.tight_layout()
    return _figure_to_png_bytes(fig)


# ----------------------------
# PDF (ReportLab con fallback a PdfPages)
# ----------------------------
def _build_pdf_reportlab(bundle: Dict, series_map: Dict[str, Dict[str, float]],
                         png_ranges: bytes, png_minmax: bytes) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Informe de Sesión")
    styles = getSampleStyleSheet()
    story = []

    # 1. Datos del paciente
    story.append(Paragraph("<b>1. Datos del paciente</b>", styles["Heading2"]))
    p_age = bundle.get("patient_age")
    p_gender = bundle.get("patient_gender")
    story.append(Paragraph(f"Nombre: {bundle.get('patient_name') or '—'}", styles["BodyText"]))
    story.append(Paragraph(f"ID paciente: {bundle.get('patient_id') or '—'}", styles["BodyText"]))
    story.append(Paragraph(f"Edad: {p_age if p_age is not None else '—'}", styles["BodyText"]))
    story.append(Paragraph(f"Género: {p_gender or '—'}", styles["BodyText"]))
    story.append(Spacer(1, 12))

    # 2. Detalles de la sesión
    story.append(Paragraph("<b>2. Detalles de la sesión</b>", styles["Heading2"]))
    dt = bundle.get("datetime")
    story.append(Paragraph(f"ID sesión: {bundle.get('id')}", styles["BodyText"]))
    story.append(Paragraph(f"Fecha y hora: {dt or '—'}", styles["BodyText"]))
    story.append(Paragraph(f"Ejercicio: {bundle.get('exercise_name') or '—'}", styles["BodyText"]))
    story.append(Paragraph(f"Notas clínicas: {bundle.get('notes') or '—'}", styles["BodyText"]))
    story.append(Paragraph(f"Vídeo asociado: {bundle.get('video_path') or '—'}", styles["BodyText"]))
    story.append(Spacer(1, 12))

    # 3. Resumen de métricas (tabla)
    story.append(Paragraph("<b>3. Resumen de métricas</b>", styles["Heading2"]))
    table_data = [["Serie", "Métrica", "Valor", "Unidad"]]
    for serie, stats in sorted(series_map.items()):
        for key in ("min", "max", "range"):
            if key in stats:
                table_data.append([serie, key, f"{stats[key]:.2f}", "degrees"])

    tbl = Table(table_data, hAlign="LEFT")
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 12))

    # 4. Visualizaciones
    story.append(Paragraph("<b>4. Visualizaciones</b>", styles["Heading2"]))
    story.append(Paragraph("Gráfico de barras: Rango por serie", styles["BodyText"]))
    story.append(Image(io.BytesIO(png_ranges), width=480, height=260))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Gráfico de barras dobles: Min y Max por serie", styles["BodyText"]))
    story.append(Image(io.BytesIO(png_minmax), width=480, height=260))
    story.append(PageBreak())

    # 5. Generación del documento
    story.append(Paragraph("<b>5. Generación del documento</b>", styles["Heading2"]))
    story.append(Paragraph("Generado por: Recon IA", styles["BodyText"]))
    story.append(Paragraph(f"Fecha de generación: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["BodyText"]))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def _build_pdf_fallback_matplotlib(bundle: Dict, series_map: Dict[str, Dict[str, float]],
                                   png_ranges: bytes, png_minmax: bytes) -> bytes:
    """
    Fallback si no hay reportlab: generamos un PDF multipágina con matplotlib.
    """
    from matplotlib.backends.backend_pdf import PdfPages
    import numpy as np

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        # Página 1: texto
        fig = plt.figure(figsize=(8.27, 11.69))  # A4 aprox en pulgadas
        plt.axis("off")

        y = 0.95
        def t(line: str, size=12, dy=0.03, bold=False):
            nonlocal y
            fontweight = "bold" if bold else "normal"
            plt.text(0.06, y, line, fontsize=size, fontweight=fontweight, va="top")
            y -= dy

        t("1. Datos del paciente", bold=True)
        t(f"Nombre: {bundle.get('patient_name') or '—'}")
        t(f"ID paciente: {bundle.get('patient_id') or '—'}")
        t(f"Edad: {bundle.get('patient_age') if bundle.get('patient_age') is not None else '—'}")
        t(f"Género: {bundle.get('patient_gender') or '—'}")
        y -= 0.02
        t("2. Detalles de la sesión", bold=True)
        t(f"ID sesión: {bundle.get('id')}")
        t(f"Fecha y hora: {bundle.get('datetime') or '—'}")
        t(f"Ejercicio: {bundle.get('exercise_name') or '—'}")
        t(f"Notas clínicas: {bundle.get('notes') or '—'}")
        t(f"Vídeo asociado: {bundle.get('video_path') or '—'}")
        y -= 0.02
        t("3. Resumen de métricas", bold=True)

        # Tabla simple en texto
        t("Serie | Métrica | Valor | Unidad", dy=0.02)
        for serie, stats in sorted(series_map.items()):
            for key in ("min", "max", "range"):
                if key in stats:
                    t(f"{serie} | {key} | {stats[key]:.2f} | degrees", dy=0.02)
        pdf.savefig(fig)
        plt.close(fig)

        # Página 2: Rango por serie
        fig2 = plt.figure(figsize=(8.27, 5.5))
        img = plt.imread(io.BytesIO(png_ranges))
        plt.imshow(img)
        plt.axis("off")
        pdf.savefig(fig2)
        plt.close(fig2)

        # Página 3: Min/Max por serie
        fig3 = plt.figure(figsize=(8.27, 5.5))
        img2 = plt.imread(io.BytesIO(png_minmax))
        plt.imshow(img2)
        plt.axis("off")
        pdf.savefig(fig3)
        plt.close(fig3)

    buf.seek(0)
    return buf.getvalue()


# ----------------------------
# API principal
# ----------------------------
def generate_session_report_pdf(session_id: int) -> bytes:
    """
    Genera el informe PDF de la sesión (binario).
    - Usa métricas ya almacenadas.
    - Crea dos gráficos (range, min/max).
    """
    bundle = _fetch_session_bundle(session_id)
    series_map = _metrics_by_series(session_id)

    png_ranges = _chart_ranges(series_map)
    png_minmax = _chart_min_max(series_map)

    # Intentar ReportLab primero
    try:
        return _build_pdf_reportlab(bundle, series_map, png_ranges, png_minmax)
    except Exception:
        # Fallback sin dependencia
        return _build_pdf_fallback_matplotlib(bundle, series_map, png_ranges, png_minmax)