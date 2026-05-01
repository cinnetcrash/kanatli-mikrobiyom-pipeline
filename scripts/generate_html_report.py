#!/usr/bin/env python3
"""
Kanatlı Mikrobiyom - HTML Rapor Üreticisi
Analiz sonuçlarından interaktif HTML raporu oluşturur.
"""

import argparse
import base64
import json
import os
from datetime import datetime
from pathlib import Path


def img_to_base64(path: Path) -> str:
    """Görseli base64'e çevir - bağımsız HTML için."""
    if not path.exists():
        return ''
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def load_summary(analysis_dir: Path) -> dict:
    summary_file = analysis_dir / 'analysis_summary.json'
    if summary_file.exists():
        with open(summary_file, encoding='utf-8') as f:
            return json.load(f)
    return {}


def alpha_div_table(summary: dict) -> str:
    """Alfa diversite HTML tablosu."""
    alpha = summary.get('alpha_diversity', {})
    if not alpha:
        return '<p>Alfa diversite verisi bulunamadı.</p>'

    sample_ids = sorted(alpha.keys())
    metrics = list(next(iter(alpha.values())).keys()) if alpha else []

    rows = ''
    for sid in sample_ids:
        vals = alpha[sid]
        row_cells = ''.join(
            f'<td class="num">{vals.get(m, "-")}</td>' for m in metrics
        )
        rows += f'<tr><td class="sid">{sid}</td>{row_cells}</tr>'

    headers = ''.join(f'<th>{m}</th>' for m in metrics)
    return f"""
    <table class="diversity-table">
        <thead>
            <tr><th>Örnek</th>{headers}</tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>"""


def image_section(analysis_dir: Path, pattern: str, title: str) -> str:
    """Belirli desene uyan görselleri HTML bölümü olarak göster."""
    images = sorted(analysis_dir.glob(pattern))
    if not images:
        return ''

    html = f'<h2 class="section-title">{title}</h2>\n<div class="img-grid">'
    for img_path in images:
        b64 = img_to_base64(img_path)
        if b64:
            caption = img_path.stem.replace('_', ' ').title()
            html += f'''
            <figure class="fig-card">
                <img src="data:image/png;base64,{b64}" alt="{caption}" loading="lazy"/>
                <figcaption>{caption}</figcaption>
            </figure>'''
    html += '</div>'
    return html


def generate_report(analysis_dir: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    summary = load_summary(analysis_dir)

    n_samples = summary.get('n_samples', 0)
    sample_ids = summary.get('sample_ids', [])
    now = datetime.now().strftime('%d.%m.%Y %H:%M')

    alpha_table = alpha_div_table(summary)

    # Beta diversite matrisi
    beta_html = ''
    if 'beta_diversity' in summary:
        beta = summary['beta_diversity']
        sids = sample_ids
        beta_html = '<h2 class="section-title">Beta Diversite (Bray-Curtis Mesafe Matrisi)</h2>'
        beta_html += '<div class="table-wrap"><table class="diversity-table"><thead><tr><th>Örnek</th>'
        beta_html += ''.join(f'<th>{s}</th>' for s in sids)
        beta_html += '</tr></thead><tbody>'
        for s1 in sids:
            beta_html += f'<tr><td class="sid">{s1}</td>'
            for s2 in sids:
                v = beta['matrix'].get(s1, {}).get(s2, '-')
                bg = ''
                if isinstance(v, float):
                    intensity = int(255 * (1 - v))
                    bg = f'style="background:rgba(52,152,219,{v:.2f})"'
                beta_html += f'<td class="num" {bg}>{v}</td>'
            beta_html += '</tr>'
        beta_html += '</tbody></table></div>'

    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Kanatlı Mikrobiyom Analiz Raporu</title>
    <style>
        :root {{
            --primary: #2c3e50;
            --accent: #3498db;
            --bg: #f8f9fa;
            --card: #ffffff;
            --border: #dee2e6;
            --text: #343a40;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        header {{
            background: var(--primary);
            color: white;
            padding: 2rem;
            text-align: center;
        }}
        header h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
        header p {{ opacity: 0.85; font-size: 0.95rem; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0;
        }}
        .stat-card {{
            background: var(--card);
            border-radius: 8px;
            padding: 1.2rem;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,.08);
            border-top: 4px solid var(--accent);
        }}
        .stat-card .value {{ font-size: 2rem; font-weight: 700; color: var(--accent); }}
        .stat-card .label {{ font-size: 0.85rem; color: #666; margin-top: 0.3rem; }}
        .section-title {{
            font-size: 1.4rem;
            color: var(--primary);
            margin: 2rem 0 1rem;
            padding-bottom: 0.4rem;
            border-bottom: 2px solid var(--accent);
        }}
        .img-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(600px, 1fr));
            gap: 1.5rem;
            margin: 1rem 0;
        }}
        .fig-card {{
            background: var(--card);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,.08);
        }}
        .fig-card img {{
            width: 100%;
            height: auto;
            border-radius: 4px;
        }}
        figcaption {{
            font-size: 0.85rem;
            color: #666;
            text-align: center;
            margin-top: 0.5rem;
        }}
        .diversity-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
            background: var(--card);
            box-shadow: 0 2px 8px rgba(0,0,0,.08);
            border-radius: 8px;
            overflow: hidden;
            margin: 1rem 0;
        }}
        .diversity-table th {{
            background: var(--primary);
            color: white;
            padding: 0.7rem 1rem;
            text-align: left;
        }}
        .diversity-table td {{
            padding: 0.6rem 1rem;
            border-bottom: 1px solid var(--border);
        }}
        .diversity-table tr:hover {{ background: #f1f3f5; }}
        td.num {{ text-align: right; font-family: monospace; }}
        td.sid {{ font-weight: 600; }}
        .table-wrap {{ overflow-x: auto; }}
        .pipeline-info {{
            background: var(--card);
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 2px 8px rgba(0,0,0,.08);
            font-size: 0.9rem;
        }}
        .pipeline-info ul {{ list-style: none; padding: 0; }}
        .pipeline-info li {{
            padding: 0.3rem 0;
            border-bottom: 1px solid var(--border);
        }}
        .pipeline-info li:last-child {{ border-bottom: none; }}
        .badge {{
            display: inline-block;
            background: var(--accent);
            color: white;
            border-radius: 12px;
            padding: 2px 10px;
            font-size: 0.8rem;
            margin-left: 0.5rem;
        }}
        footer {{
            text-align: center;
            padding: 2rem;
            color: #999;
            font-size: 0.85rem;
            margin-top: 3rem;
            border-top: 1px solid var(--border);
        }}
    </style>
</head>
<body>

<header>
    <h1>🦠 Kanatlı Mikrobiyom Analiz Raporu</h1>
    <p>Nanopore Uzun Okuma Sekans Analizi &bull; {now} &bull;
       Kraken2 + Bracken Pipeline</p>
</header>

<div class="container">

    <!-- Özet İstatistikler -->
    <div class="stats-grid">
        <div class="stat-card">
            <div class="value">{n_samples}</div>
            <div class="label">Analiz Edilen Örnek</div>
        </div>
        <div class="stat-card">
            <div class="value">30 GB</div>
            <div class="label">Kraken2 Veritabanı</div>
        </div>
        <div class="stat-card">
            <div class="value">R10.4.1</div>
            <div class="label">Nanopore Kimyası</div>
        </div>
        <div class="stat-card">
            <div class="value">Gallus</div>
            <div class="label">Konak Temizliği</div>
        </div>
    </div>

    <!-- Pipeline Bilgisi -->
    <h2 class="section-title">Pipeline Bilgisi</h2>
    <div class="pipeline-info">
        <ul>
            <li><strong>Adım 1:</strong> Ham okuma QC <span class="badge">NanoStat</span></li>
            <li><strong>Adım 2:</strong> Kalite filtresi (Q≥8, min 500 bp) <span class="badge">Chopper</span></li>
            <li><strong>Adım 3:</strong> Gallus gallus konak DNA temizliği <span class="badge">Minimap2 + Samtools</span></li>
            <li><strong>Adım 4:</strong> Taksonomik sınıflandırma (PlusPF 30GB) <span class="badge">Kraken2</span></li>
            <li><strong>Adım 5:</strong> Bolluk tahmini (Tür / Cins / Aile) <span class="badge">Bracken</span></li>
            <li><strong>Adım 6:</strong> İstatistiksel analiz ve görselleştirme <span class="badge">Python</span></li>
        </ul>
    </div>

    <!-- Alfa Diversite -->
    <h2 class="section-title">Alfa Diversite İstatistikleri</h2>
    <div class="table-wrap">{alpha_table}</div>

    {beta_html}

    {image_section(analysis_dir, '*phylum_donut.png',
                   'Phylum Düzeyi Dağılım')}

    {image_section(analysis_dir, '*_species_top*_bar.png',
                   'En Yaygın Türler')}

    {image_section(analysis_dir, '*_genus_top*_bar.png',
                   'En Yaygın Cinsler')}

    {image_section(analysis_dir, '*stacked_bar.png',
                   'Yığılmış Bolluk Grafiği')}

    {image_section(analysis_dir, '*heatmap.png',
                   'Bolluk Isı Haritası')}

    {image_section(analysis_dir, 'beta_diversity*.png',
                   'Beta Diversite')}

    {image_section(analysis_dir, 'alpha_diversity_comparison.png',
                   'Alfa Diversite Karşılaştırması')}

    {image_section(analysis_dir, 'kraken2_classification_rates.png',
                   'Sınıflandırma Oranları')}

</div>

<footer>
    Kanatlı Mikrobiyom Pipeline v1.0 &bull;
    Rapor tarihi: {now} &bull;
    Nextflow + Docker + Kraken2 + Bracken
</footer>
</body>
</html>"""

    out_file = outdir / 'mikrobiyom_raporu.html'
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[INFO] HTML raporu oluşturuldu: {out_file}", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description='Kanatlı Mikrobiyom HTML Rapor Üreticisi'
    )
    parser.add_argument('--analysis-dir', type=Path, required=True)
    parser.add_argument('--outdir', type=Path, default=Path('report'))
    args = parser.parse_args()
    generate_report(args.analysis_dir, args.outdir)


if __name__ == '__main__':
    main()
