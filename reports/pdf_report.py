import io
import datetime
import sqlite3
from typing import Dict, Tuple, List

import matplotlib.pyplot as plt

from db.init_db import get_connection
from db import crud


def _fetch_session_bundle(session_id: int) -> Dict:
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


def _metrics_by_series(session_id: int) -> Dict[str, Dict[str, any]]:
    rows = crud.get_metrics_by_session(session_id) or []
    series: Dict[str, Dict[str, any]] = {}

    for name, value, unit in rows:
        if not isinstance(name, str):
            continue
        
        if name.endswith("_min"):
            base, key = name[:-4], "min"
        elif name.endswith("_max"):
            base, key = name[:-4], "max"
        elif name.endswith("_range"):
            base, key = name[:-6], "range"
        else:
            continue

        try:
            v = float(value) if value is not None else None
        except (TypeError, ValueError):
            v = None

        if v is None:
            continue

        series.setdefault(base, {})
        series[base][key] = v
        
        if "unit" not in series[base] and unit:
            series[base]["unit"] = unit

    return series


def _separate_metrics_by_type(series_map: Dict[str, Dict[str, any]]) -> Tuple[Dict, Dict]:
    angular = {}
    symmetry = {}
    
    for serie, stats in series_map.items():
        if serie.startswith("symmetry_"):
            symmetry[serie] = stats
        else:
            angular[serie] = stats
    
    return angular, symmetry


def _figure_to_png_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _chart_ranges(series_map: Dict[str, Dict[str, float]], title: str = "Rango por serie") -> bytes:
    labels, values = [], []
    for serie, stats in sorted(series_map.items()):
        if "range" in stats:
            labels.append(serie)
            values.append(stats["range"])

    if not labels:
        fig = plt.figure(figsize=(6, 3))
        plt.title(title)
        plt.text(0.5, 0.5, "Sin datos de 'range'", ha="center", va="center")
        return _figure_to_png_bytes(fig)

    fig = plt.figure(figsize=(8, 4))
    plt.title(title)
    plt.bar(labels, values, color='steelblue')
    
    if labels and labels[0].startswith("symmetry_") and "_y" in labels[0]:
        plt.ylabel("pixels")
    else:
        plt.ylabel("degrees")
    
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    return _figure_to_png_bytes(fig)


def _chart_min_max(series_map: Dict[str, Dict[str, float]], title: str = "Min y Max por serie") -> bytes:
    labels, mins, maxs = [], [], []
    for serie, stats in sorted(series_map.items()):
        if "min" in stats or "max" in stats:
            labels.append(serie)
            mins.append(stats.get("min", 0.0))
            maxs.append(stats.get("max", 0.0))

    if not labels:
        fig = plt.figure(figsize=(6, 3))
        plt.title(title)
        plt.text(0.5, 0.5, "Sin datos de 'min/max'", ha="center", va="center")
        return _figure_to_png_bytes(fig)

    import numpy as np
    x = np.arange(len(labels))
    width = 0.38

    fig = plt.figure(figsize=(8, 4))
    plt.title(title)
    plt.bar(x - width / 2, mins, width, label="min", color='lightcoral')
    plt.bar(x + width / 2, maxs, width, label="max", color='lightgreen')
    
    if labels and labels[0].startswith("symmetry_") and "_y" in labels[0]:
        plt.ylabel("pixels")
    else:
        plt.ylabel("degrees")
    
    plt.xticks(x, labels, rotation=20, ha="right")
    plt.legend()
    plt.tight_layout()
    return _figure_to_png_bytes(fig)


def _chart_symmetry_overview(symmetry_map: Dict[str, Dict[str, float]]) -> bytes:
    if not symmetry_map:
        fig = plt.figure(figsize=(6, 3))
        plt.title("Análisis de Simetría Bilateral")
        plt.text(0.5, 0.5, "Sin datos de simetría", ha="center", va="center")
        return _figure_to_png_bytes(fig)
    
    angular_labels, angular_values = [], []
    positional_labels, positional_values = [], []
    
    for serie, stats in sorted(symmetry_map.items()):
        if "max" not in stats:
            continue
        
        label = serie.replace("symmetry_", "").replace("_", " ").title()
        
        if "_y" in serie:
            positional_labels.append(label)
            positional_values.append(stats["max"])
        else:
            angular_labels.append(label)
            angular_values.append(stats["max"])
    
    if angular_values and positional_values:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        
        ax1.barh(angular_labels, angular_values, color='cornflowerblue')
        ax1.set_xlabel('Asimetría máxima (degrees)')
        ax1.set_title('Simetría Angular')
        ax1.invert_yaxis()
        
        ax2.barh(positional_labels, positional_values, color='coral')
        ax2.set_xlabel('Asimetría máxima (pixels)')
        ax2.set_title('Simetría Posicional')
        ax2.invert_yaxis()
        
        plt.tight_layout()
    else:
        fig = plt.figure(figsize=(8, 4))
        if angular_values:
            plt.barh(angular_labels, angular_values, color='cornflowerblue')
            plt.xlabel('Asimetría máxima (degrees)')
            plt.title('Simetría Angular')
        else:
            plt.barh(positional_labels, positional_values, color='coral')
            plt.xlabel('Asimetría máxima (pixels)')
            plt.title('Simetría Posicional')
        plt.gca().invert_yaxis()
        plt.tight_layout()
    
    return _figure_to_png_bytes(fig)


def _build_pdf_reportlab(bundle: Dict, series_map: Dict[str, Dict[str, float]],
                         png_ranges: bytes, png_minmax: bytes, 
                         png_symmetry: bytes = None) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Informe de Sesión - Recon IA")
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>1. Datos del paciente</b>", styles["Heading2"]))
    p_age = bundle.get("patient_age")
    p_gender = bundle.get("patient_gender")
    story.append(Paragraph(f"Nombre: {bundle.get('patient_name') or '—'}", styles["BodyText"]))
    story.append(Paragraph(f"ID paciente: {bundle.get('patient_id') or '—'}", styles["BodyText"]))
    story.append(Paragraph(f"Edad: {p_age if p_age is not None else '—'}", styles["BodyText"]))
    story.append(Paragraph(f"Género: {p_gender or '—'}", styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>2. Detalles de la sesión</b>", styles["Heading2"]))
    dt = bundle.get("datetime")
    story.append(Paragraph(f"ID sesión: {bundle.get('id')}", styles["BodyText"]))
    story.append(Paragraph(f"Fecha y hora: {dt or '—'}", styles["BodyText"]))
    story.append(Paragraph(f"Ejercicio: {bundle.get('exercise_name') or '—'}", styles["BodyText"]))
    story.append(Paragraph(f"Notas clínicas: {bundle.get('notes') or '—'}", styles["BodyText"]))
    story.append(Paragraph(f"Vídeo asociado: {bundle.get('video_path') or '—'}", styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>3. Resumen de métricas</b>", styles["Heading2"]))
    
    angular_metrics, symmetry_metrics = _separate_metrics_by_type(series_map)
    
    if angular_metrics:
        story.append(Paragraph("<b>3.1 Ángulos Articulares</b>", styles["Heading3"]))
        table_data = [["Serie", "Métrica", "Valor", "Unidad"]]
        for serie, stats in sorted(angular_metrics.items()):
            for key in ("min", "max", "range"):
                if key in stats:
                    table_data.append([
                        serie, 
                        key, 
                        f"{stats[key]:.2f}", 
                        stats.get("unit", "degrees")
                    ])

        tbl = Table(table_data, hAlign="LEFT")
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ]
            )
        )
        story.append(tbl)
        story.append(Spacer(1, 12))
    
    if symmetry_metrics:
        story.append(Paragraph("<b>3.2 Análisis de Simetría Bilateral</b>", styles["Heading3"]))
        story.append(Paragraph(
            "Valores cercanos a 0 indican simetría perfecta. Valores altos indican asimetría/compensación.",
            styles["BodyText"]
        ))
        story.append(Spacer(1, 6))
        
        table_data = [["Serie", "Métrica", "Valor", "Unidad"]]
        for serie, stats in sorted(symmetry_metrics.items()):
            for key in ("min", "max", "range"):
                if key in stats:
                    table_data.append([
                        serie.replace("symmetry_", ""), 
                        key, 
                        f"{stats[key]:.2f}", 
                        stats.get("unit", "degrees")
                    ])

        tbl = Table(table_data, hAlign="LEFT")
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightcoral),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ]
            )
        )
        story.append(tbl)
        story.append(Spacer(1, 12))

    story.append(Paragraph("<b>4. Visualizaciones</b>", styles["Heading2"]))
    
    if png_symmetry and symmetry_metrics:
        story.append(Paragraph("<b>4.1 Análisis de Simetría Bilateral</b>", styles["Heading3"]))
        story.append(Image(io.BytesIO(png_symmetry), width=480, height=260))
        story.append(Spacer(1, 12))
    
    if angular_metrics:
        story.append(Paragraph("<b>4.2 Rango de Movimiento Articular</b>", styles["Heading3"]))
        story.append(Image(io.BytesIO(png_ranges), width=480, height=260))
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>4.3 Valores Mínimos y Máximos</b>", styles["Heading3"]))
        story.append(Image(io.BytesIO(png_minmax), width=480, height=260))
        story.append(PageBreak())

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def _build_pdf_fallback_matplotlib(bundle: Dict, series_map: Dict[str, Dict[str, float]],
                                   png_ranges: bytes, png_minmax: bytes,
                                   png_symmetry: bytes = None) -> bytes:
    from matplotlib.backends.backend_pdf import PdfPages

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))
        plt.axis("off")

        y = 0.95
        def t(line: str, size=12, dy=0.03, bold=False):
            nonlocal y
            fontweight = "bold" if bold else "normal"
            plt.text(0.06, y, line, fontsize=size, fontweight=fontweight, va="top")
            y -= dy

        t("INFORME DE SESIÓN - RECON IA", size=16, bold=True, dy=0.05)
        y -= 0.02
        
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
        y -= 0.02
        
        angular_metrics, symmetry_metrics = _separate_metrics_by_type(series_map)
        
        t("3. Resumen de métricas", bold=True)
        if angular_metrics:
            t("3.1 Ángulos Articulares", bold=True, dy=0.02)
            t("Serie | Métrica | Valor | Unidad", dy=0.02)
            for serie, stats in sorted(angular_metrics.items()):
                for key in ("min", "max", "range"):
                    if key in stats:
                        unit = stats.get("unit", "degrees")
                        t(f"{serie} | {key} | {stats[key]:.2f} | {unit}", dy=0.02)
        
        if symmetry_metrics:
            y -= 0.01
            t("3.2 Simetría Bilateral", bold=True, dy=0.02)
            t("Serie | Métrica | Valor | Unidad", dy=0.02)
            for serie, stats in sorted(symmetry_metrics.items()):
                for key in ("min", "max", "range"):
                    if key in stats:
                        unit = stats.get("unit", "degrees")
                        t(f"{serie.replace('symmetry_', '')} | {key} | {stats[key]:.2f} | {unit}", dy=0.02)
        
        pdf.savefig(fig)
        plt.close(fig)

        if png_symmetry and symmetry_metrics:
            fig2 = plt.figure(figsize=(8.27, 5.5))
            img = plt.imread(io.BytesIO(png_symmetry))
            plt.imshow(img)
            plt.axis("off")
            plt.title("Análisis de Simetría Bilateral", fontsize=14, fontweight="bold", pad=20)
            pdf.savefig(fig2)
            plt.close(fig2)

        if angular_metrics:
            fig3 = plt.figure(figsize=(8.27, 5.5))
            img2 = plt.imread(io.BytesIO(png_ranges))
            plt.imshow(img2)
            plt.axis("off")
            plt.title("Rango de Movimiento Articular", fontsize=14, fontweight="bold", pad=20)
            pdf.savefig(fig3)
            plt.close(fig3)

            fig4 = plt.figure(figsize=(8.27, 5.5))
            img3 = plt.imread(io.BytesIO(png_minmax))
            plt.imshow(img3)
            plt.axis("off")
            plt.title("Valores Mínimos y Máximos", fontsize=14, fontweight="bold", pad=20)
            pdf.savefig(fig4)
            plt.close(fig4)

    buf.seek(0)
    return buf.getvalue()


def generate_session_report_pdf(session_id: int) -> bytes:
    bundle = _fetch_session_bundle(session_id)
    series_map = _metrics_by_series(session_id)
    
    angular_metrics, symmetry_metrics = _separate_metrics_by_type(series_map)

    png_ranges = _chart_ranges(angular_metrics, "Rango de Movimiento Articular")
    png_minmax = _chart_min_max(angular_metrics, "Valores Mínimos y Máximos")
    
    png_symmetry = None
    if symmetry_metrics:
        png_symmetry = _chart_symmetry_overview(symmetry_metrics)

    try:
        return _build_pdf_reportlab(bundle, series_map, png_ranges, png_minmax, png_symmetry)
    except Exception:
        return _build_pdf_fallback_matplotlib(bundle, series_map, png_ranges, png_minmax, png_symmetry)