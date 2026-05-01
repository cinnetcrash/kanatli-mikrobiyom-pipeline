#!/usr/bin/env python3
"""
Kanatlı Mikrobiyom - Bolluk ve Diversite Analizi
Bracken + Kraken2 çıktılarından kapsamlı istatistiksel analiz üretir.
"""

import argparse
import json
import os
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from scipy.spatial.distance import braycurtis
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.stats import kruskal

warnings.filterwarnings('ignore')
sns.set_theme(style='whitegrid', font_scale=1.1)

PALETTE_MAIN = sns.color_palette('tab20', 20) + sns.color_palette('tab20b', 20)


# ─── Veri Okuma ──────────────────────────────────────────────────────────────

def read_bracken_file(filepath: Path) -> pd.DataFrame:
    """Bracken çıktı dosyasını oku."""
    df = pd.read_csv(
        filepath, sep='\t',
        usecols=['name', 'taxonomy_id', 'taxonomy_lvl',
                 'kraken_assigned_reads', 'added_reads',
                 'new_est_reads', 'fraction_total_reads']
    )
    df.columns = ['name', 'taxid', 'level', 'kraken_reads',
                  'added_reads', 'est_reads', 'fraction']
    df = df[df['est_reads'] > 0].copy()
    return df


def read_kraken_report(filepath: Path) -> pd.DataFrame:
    """Kraken2 rapor dosyasını oku."""
    df = pd.read_csv(
        filepath, sep='\t', header=None,
        names=['pct', 'clade_reads', 'direct_reads', 'level', 'taxid', 'name']
    )
    df['name'] = df['name'].str.strip()
    return df


def load_all_samples(species_dir: Path, genus_dir: Path,
                     kraken_dir: Path) -> dict:
    """Tüm örnek dosyalarını yükle."""
    data = {'species': {}, 'genus': {}, 'kraken': {}}

    for f in sorted(species_dir.glob('*_species.bracken')):
        sid = re.sub(r'_species\.bracken$', '', f.name)
        data['species'][sid] = read_bracken_file(f)

    for f in sorted(genus_dir.glob('*_genus.bracken')):
        sid = re.sub(r'_genus\.bracken$', '', f.name)
        data['genus'][sid] = read_bracken_file(f)

    for f in sorted(kraken_dir.glob('*_kraken2.report')):
        sid = re.sub(r'_kraken2\.report$', '', f.name)
        data['kraken'][sid] = read_kraken_report(f)

    return data


# ─── Diversite Hesaplama ─────────────────────────────────────────────────────

def shannon_entropy(counts: np.ndarray) -> float:
    counts = counts[counts > 0].astype(float)
    p = counts / counts.sum()
    return float(-np.sum(p * np.log(p)))


def simpson_index(counts: np.ndarray) -> float:
    counts = counts[counts > 0].astype(float)
    p = counts / counts.sum()
    return float(1 - np.sum(p ** 2))


def chao1(counts: np.ndarray) -> float:
    n1 = np.sum(counts == 1)
    n2 = np.sum(counts == 2)
    obs = np.sum(counts > 0)
    if n2 == 0:
        return float(obs + n1 * (n1 - 1) / 2)
    return float(obs + (n1 ** 2) / (2 * n2))


def evenness_pielou(counts: np.ndarray) -> float:
    """Pielou J eşitlik indeksi."""
    h = shannon_entropy(counts)
    s = np.sum(counts > 0)
    if s <= 1:
        return 0.0
    return float(h / np.log(s))


def calculate_alpha_diversity(df: pd.DataFrame) -> dict:
    counts = df['est_reads'].values
    return {
        'Gözlemlenen Tür': int(np.sum(counts > 0)),
        'Shannon Entropisi': round(shannon_entropy(counts), 4),
        'Simpson İndeksi': round(simpson_index(counts), 4),
        'Chao1 Tahmini': round(chao1(counts), 2),
        'Pielou Eşitliği': round(evenness_pielou(counts), 4),
        'Toplam Okuma': int(counts.sum()),
    }


def bray_curtis_matrix(samples_dict: dict, top_n: int = 200) -> tuple:
    """Bray-Curtis mesafe matrisi hesapla."""
    sample_ids = sorted(samples_dict.keys())
    if len(sample_ids) < 2:
        return None, sample_ids

    # Ortak taksa seti
    all_taxa = set()
    for df in samples_dict.values():
        all_taxa.update(df['name'].tolist())
    all_taxa = sorted(all_taxa)

    # Bolluk matrisi
    mat = np.zeros((len(sample_ids), len(all_taxa)))
    taxa_idx = {t: i for i, t in enumerate(all_taxa)}
    for i, sid in enumerate(sample_ids):
        df = samples_dict[sid]
        total = df['est_reads'].sum()
        for _, row in df.iterrows():
            if row['name'] in taxa_idx:
                mat[i, taxa_idx[row['name']]] = row['est_reads'] / total

    # Bray-Curtis
    n = len(sample_ids)
    dist_mat = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = braycurtis(mat[i], mat[j])
            dist_mat[i, j] = dist_mat[j, i] = d

    return dist_mat, sample_ids


# ─── Grafik Üretimi ──────────────────────────────────────────────────────────

def plot_top_taxa_bar(samples_dict: dict, level: str, top_n: int,
                      outdir: Path) -> None:
    """Her örnek için yatay çubuk grafik (en yaygın N taksa)."""
    for sid, df in samples_dict.items():
        df_sorted = df.nlargest(top_n, 'fraction').copy()
        df_sorted['pct'] = df_sorted['fraction'] * 100

        fig, ax = plt.subplots(figsize=(12, max(6, len(df_sorted) * 0.35)))
        colors = PALETTE_MAIN[:len(df_sorted)]
        bars = ax.barh(df_sorted['name'], df_sorted['pct'],
                       color=colors[::-1], edgecolor='white', linewidth=0.5)

        ax.set_xlabel('Göreli Bolluk (%)', fontsize=12)
        ax.set_title(f'{sid} — En Yaygın {top_n} {level.capitalize()}\n'
                     f'(toplam {int(df_sorted["est_reads"].sum()):,} okuma)',
                     fontsize=13, fontweight='bold')
        ax.tick_params(axis='y', labelsize=9)
        ax.invert_yaxis()

        for bar, (_, row) in zip(bars, df_sorted.iterrows()):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                    f'{row["pct"]:.2f}%',
                    va='center', ha='left', fontsize=8)

        plt.tight_layout()
        fig.savefig(outdir / f'{sid}_{level}_top{top_n}_bar.png',
                    dpi=150, bbox_inches='tight')
        plt.close(fig)


def plot_stacked_bar(samples_dict: dict, level: str, top_n: int,
                     outdir: Path) -> None:
    """Çoklu örnek yığılmış çubuk grafiği."""
    if len(samples_dict) < 1:
        return

    # Tüm örneklerde en yüksek ortalama bolluğa sahip N taksa
    all_fractions = {}
    for df in samples_dict.values():
        for _, row in df.iterrows():
            all_fractions[row['name']] = \
                all_fractions.get(row['name'], 0) + row['fraction']

    top_taxa = sorted(all_fractions, key=all_fractions.get, reverse=True)[:top_n]
    sample_ids = sorted(samples_dict.keys())

    matrix = pd.DataFrame(index=sample_ids, columns=top_taxa, data=0.0)
    for sid, df in samples_dict.items():
        for _, row in df.iterrows():
            if row['name'] in top_taxa:
                matrix.loc[sid, row['name']] = row['fraction'] * 100

    matrix['Diğer'] = 100 - matrix[top_taxa].sum(axis=1)
    matrix['Diğer'] = matrix['Diğer'].clip(lower=0)

    cols = top_taxa + ['Diğer']
    colors = PALETTE_MAIN[:len(top_taxa)] + [(0.85, 0.85, 0.85)]

    fig, ax = plt.subplots(figsize=(max(10, len(sample_ids) * 2), 8))
    bottom = np.zeros(len(sample_ids))
    x = np.arange(len(sample_ids))

    for col, color in zip(cols, colors):
        vals = matrix[col].values.astype(float)
        ax.bar(x, vals, bottom=bottom, color=color,
               edgecolor='white', linewidth=0.3, label=col)
        bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels(sample_ids, rotation=30, ha='right', fontsize=10)
    ax.set_ylabel('Göreli Bolluk (%)', fontsize=12)
    ax.set_title(f'Örnekler Arası {level.capitalize()} Düzeyi Bolluk Dağılımı\n'
                 f'(En yaygın {top_n} taksa)',
                 fontsize=13, fontweight='bold')
    ax.set_ylim(0, 105)

    handles = [mpatches.Patch(color=c, label=t)
               for t, c in zip(cols, colors) if matrix[t].sum() > 0]
    ax.legend(handles=handles, bbox_to_anchor=(1.01, 1), loc='upper left',
              fontsize=7, ncol=1, frameon=False)

    plt.tight_layout()
    fig.savefig(outdir / f'all_samples_{level}_stacked_bar.png',
                dpi=150, bbox_inches='tight')
    plt.close(fig)


def plot_heatmap(samples_dict: dict, level: str, top_n: int,
                 outdir: Path) -> None:
    """Bolluk ısı haritası."""
    if len(samples_dict) < 2:
        return

    all_means = {}
    for df in samples_dict.values():
        for _, row in df.iterrows():
            all_means[row['name']] = \
                all_means.get(row['name'], 0) + row['fraction']

    top_taxa = sorted(all_means, key=all_means.get, reverse=True)[:top_n]
    sample_ids = sorted(samples_dict.keys())

    mat = pd.DataFrame(index=sample_ids, columns=top_taxa, data=0.0)
    for sid, df in samples_dict.items():
        for _, row in df.iterrows():
            if row['name'] in top_taxa:
                mat.loc[sid, row['name']] = row['fraction'] * 100

    fig, ax = plt.subplots(figsize=(max(14, len(top_taxa) * 0.4),
                                    max(6, len(sample_ids) * 0.6)))
    sns.heatmap(
        mat.astype(float),
        ax=ax,
        cmap='YlOrRd',
        xticklabels=True,
        yticklabels=True,
        linewidths=0.3,
        cbar_kws={'label': 'Göreli Bolluk (%)'}
    )
    ax.set_title(f'{level.capitalize()} Düzeyi Bolluk Isı Haritası',
                 fontsize=13, fontweight='bold')
    ax.tick_params(axis='x', labelsize=7, rotation=45)
    ax.tick_params(axis='y', labelsize=9)

    plt.tight_layout()
    fig.savefig(outdir / f'all_samples_{level}_heatmap.png',
                dpi=150, bbox_inches='tight')
    plt.close(fig)


def plot_bray_curtis(dist_mat: np.ndarray, sample_ids: list,
                     outdir: Path) -> None:
    """Bray-Curtis mesafe matrisi ve dendrogramı."""
    if dist_mat is None or len(sample_ids) < 2:
        return

    fig, axes = plt.subplots(1, 2, figsize=(16, max(6, len(sample_ids) * 0.5)))

    # Mesafe matrisi ısı haritası
    df_dist = pd.DataFrame(dist_mat, index=sample_ids, columns=sample_ids)
    sns.heatmap(
        df_dist, ax=axes[0], cmap='Blues',
        annot=len(sample_ids) <= 20,
        fmt='.3f',
        cbar_kws={'label': 'Bray-Curtis Mesafesi'},
        xticklabels=True, yticklabels=True
    )
    axes[0].set_title('Bray-Curtis Mesafe Matrisi', fontweight='bold')

    # Hiyerarşik kümeleme dendrogramı
    linked = linkage(dist_mat[np.triu_indices(len(sample_ids), k=1)],
                     method='average')
    dendrogram(linked, labels=sample_ids, ax=axes[1],
               orientation='right', leaf_font_size=10)
    axes[1].set_title('Hiyerarşik Kümeleme (Ortalama bağlantı)', fontweight='bold')
    axes[1].set_xlabel('Bray-Curtis Mesafesi')

    plt.tight_layout()
    fig.savefig(outdir / 'beta_diversity_bray_curtis.png',
                dpi=150, bbox_inches='tight')
    plt.close(fig)


def plot_alpha_diversity_comparison(alpha_div: dict, outdir: Path) -> None:
    """Örnekler arası alfa diversite karşılaştırması."""
    if len(alpha_div) < 2:
        return

    metrics = ['Gözlemlenen Tür', 'Shannon Entropisi',
               'Simpson İndeksi', 'Chao1 Tahmini', 'Pielou Eşitliği']
    sample_ids = sorted(alpha_div.keys())

    fig, axes = plt.subplots(1, len(metrics), figsize=(4 * len(metrics), 6))

    for ax, metric in zip(axes, metrics):
        values = [alpha_div[sid].get(metric, 0) for sid in sample_ids]
        colors_bar = [PALETTE_MAIN[i % len(PALETTE_MAIN)]
                      for i in range(len(sample_ids))]
        bars = ax.bar(sample_ids, values, color=colors_bar,
                      edgecolor='white', linewidth=0.5)
        ax.set_title(metric, fontsize=10, fontweight='bold')
        ax.set_ylabel(metric, fontsize=9)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.01,
                    f'{val:.2f}', ha='center', va='bottom', fontsize=8)

    plt.suptitle('Alfa Diversite Karşılaştırması', fontsize=14, fontweight='bold')
    plt.tight_layout()
    fig.savefig(outdir / 'alpha_diversity_comparison.png',
                dpi=150, bbox_inches='tight')
    plt.close(fig)


def plot_kraken_classification_rate(kraken_data: dict, outdir: Path) -> None:
    """Kraken2 sınıflandırma oranları."""
    if not kraken_data:
        return

    records = []
    for sid, df in kraken_data.items():
        unclass = df[df['level'] == 'U']['pct'].sum()
        classified = 100 - unclass
        records.append({'sample': sid, 'Sınıflandırıldı': classified,
                        'Sınıflandırılmadı': unclass})

    df_rates = pd.DataFrame(records).set_index('sample')
    fig, ax = plt.subplots(figsize=(max(8, len(records) * 1.5), 6))
    df_rates.plot(kind='bar', ax=ax, color=['#2ecc71', '#e74c3c'],
                  edgecolor='white', linewidth=0.5)
    ax.set_title('Kraken2 Sınıflandırma Oranları', fontsize=13, fontweight='bold')
    ax.set_ylabel('Oran (%)', fontsize=12)
    ax.set_ylim(0, 110)
    ax.tick_params(axis='x', rotation=30)
    ax.legend(loc='upper right')
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f%%', fontsize=8, padding=2)
    plt.tight_layout()
    fig.savefig(outdir / 'kraken2_classification_rates.png',
                dpi=150, bbox_inches='tight')
    plt.close(fig)


def plot_phylum_donut(samples_dict: dict, kraken_data: dict, outdir: Path) -> None:
    """Phylum düzeyi pasta/çörek grafiği."""
    for sid, kdf in kraken_data.items():
        phyla = kdf[kdf['level'] == 'P'].copy()
        phyla = phyla.nlargest(10, 'clade_reads')
        if phyla.empty:
            continue

        total = phyla['clade_reads'].sum()
        if total == 0:
            continue

        phyla['pct'] = phyla['clade_reads'] / total * 100
        colors = PALETTE_MAIN[:len(phyla)]

        fig, ax = plt.subplots(figsize=(9, 7))
        wedges, texts, autotexts = ax.pie(
            phyla['pct'], labels=None,
            autopct=lambda p: f'{p:.1f}%' if p > 2 else '',
            pctdistance=0.8,
            colors=colors,
            startangle=90,
            wedgeprops=dict(width=0.55, edgecolor='white', linewidth=1.5)
        )
        for at in autotexts:
            at.set_fontsize(8)

        ax.legend(
            [f'{row["name"]} ({row["pct"]:.1f}%)'
             for _, row in phyla.iterrows()],
            loc='lower center', bbox_to_anchor=(0.5, -0.15),
            ncol=2, fontsize=8, frameon=False
        )
        ax.set_title(f'{sid} — Phylum Düzeyi Dağılımı',
                     fontsize=13, fontweight='bold', pad=20)
        plt.tight_layout()
        fig.savefig(outdir / f'{sid}_phylum_donut.png',
                    dpi=150, bbox_inches='tight')
        plt.close(fig)


# ─── Sonuç Tabloları ─────────────────────────────────────────────────────────

def save_abundance_tables(samples_dict: dict, level: str, outdir: Path) -> None:
    """Tüm örnekler için birleşik bolluk tablosu."""
    if not samples_dict:
        return

    all_taxa = set()
    for df in samples_dict.values():
        all_taxa.update(df['name'].tolist())

    combined = pd.DataFrame(index=sorted(all_taxa))
    for sid, df in sorted(samples_dict.items()):
        tmp = df.set_index('name')['fraction']
        combined[sid] = tmp

    combined = combined.fillna(0)
    combined['mean'] = combined.mean(axis=1)
    combined = combined.sort_values('mean', ascending=False).drop('mean', axis=1)
    combined = combined * 100  # yüzdeye çevir

    combined.to_csv(outdir / f'abundance_table_{level}.csv',
                    float_format='%.6f')

    # Excel versiyonu
    try:
        with pd.ExcelWriter(outdir / f'abundance_table_{level}.xlsx',
                            engine='openpyxl') as writer:
            combined.to_excel(writer, sheet_name=level.capitalize())
    except Exception:
        pass


def save_alpha_diversity_table(alpha_div: dict, outdir: Path) -> None:
    """Alfa diversite özet tablosu."""
    if not alpha_div:
        return
    df = pd.DataFrame(alpha_div).T
    df.index.name = 'sample_id'
    df.to_csv(outdir / 'alpha_diversity_summary.csv', float_format='%.4f')
    try:
        df.to_excel(outdir / 'alpha_diversity_summary.xlsx', engine='openpyxl')
    except Exception:
        pass


def save_summary_json(alpha_div: dict, dist_mat, sample_ids: list,
                      outdir: Path) -> None:
    """Makine-okunabilir özet JSON."""
    summary = {
        'pipeline': 'kanatli-mikrobiyom',
        'n_samples': len(alpha_div),
        'sample_ids': sorted(alpha_div.keys()),
        'alpha_diversity': {
            sid: {k: float(v) if isinstance(v, (np.floating, float)) else v
                  for k, v in metrics.items()}
            for sid, metrics in alpha_div.items()
        }
    }
    if dist_mat is not None and len(sample_ids) >= 2:
        summary['beta_diversity'] = {
            'method': 'bray_curtis',
            'matrix': {
                sample_ids[i]: {
                    sample_ids[j]: round(float(dist_mat[i, j]), 4)
                    for j in range(len(sample_ids))
                }
                for i in range(len(sample_ids))
            }
        }
    with open(outdir / 'analysis_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


# ─── Ana Giriş Noktası ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Kanatlı Mikrobiyom İstatistiksel Analiz'
    )
    parser.add_argument('--species-dir',  type=Path, required=True)
    parser.add_argument('--genus-dir',    type=Path, required=True)
    parser.add_argument('--kraken-dir',   type=Path, required=True)
    parser.add_argument('--outdir',       type=Path, default=Path('results'))
    parser.add_argument('--top-taxa',     type=int,  default=30)
    parser.add_argument('--threads',      type=int,  default=4)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Veriler yükleniyor...", flush=True)
    data = load_all_samples(args.species_dir, args.genus_dir, args.kraken_dir)

    n_sp = len(data['species'])
    n_ge = len(data['genus'])
    n_kr = len(data['kraken'])
    print(f"[INFO] {n_sp} tür, {n_ge} cins, {n_kr} Kraken2 raporu bulundu.",
          flush=True)

    if n_sp == 0:
        print("[UYARI] Tür düzeyi Bracken dosyası bulunamadı!", file=sys.stderr)
        sys.exit(1)

    # ── Alfa Diversite ──
    print("[INFO] Alfa diversite hesaplanıyor...", flush=True)
    alpha_div = {sid: calculate_alpha_diversity(df)
                 for sid, df in data['species'].items()}
    save_alpha_diversity_table(alpha_div, args.outdir)

    # ── Beta Diversite ──
    print("[INFO] Beta diversite (Bray-Curtis) hesaplanıyor...", flush=True)
    dist_mat, sids = bray_curtis_matrix(data['species'])

    # ── Tablolar ──
    print("[INFO] Bolluk tabloları kaydediliyor...", flush=True)
    save_abundance_tables(data['species'], 'species', args.outdir)
    save_abundance_tables(data['genus'],   'genus',   args.outdir)
    save_summary_json(alpha_div, dist_mat, sids, args.outdir)

    # ── Grafikler ──
    print("[INFO] Grafikler oluşturuluyor...", flush=True)
    plot_top_taxa_bar(data['species'], 'species', args.top_taxa, args.outdir)
    plot_top_taxa_bar(data['genus'],   'genus',   args.top_taxa, args.outdir)
    plot_stacked_bar(data['species'], 'species', args.top_taxa, args.outdir)
    plot_stacked_bar(data['genus'],   'genus',   args.top_taxa, args.outdir)

    if n_sp >= 2:
        plot_heatmap(data['species'], 'species', args.top_taxa, args.outdir)
        plot_heatmap(data['genus'],   'genus',   args.top_taxa, args.outdir)
        plot_bray_curtis(dist_mat, sids, args.outdir)
        plot_alpha_diversity_comparison(alpha_div, args.outdir)

    plot_kraken_classification_rate(data['kraken'], args.outdir)
    plot_phylum_donut(data['species'], data['kraken'], args.outdir)

    print(f"[INFO] Analiz tamamlandı. Çıktılar: {args.outdir}", flush=True)
    print("\n=== Alfa Diversite Özeti ===")
    for sid, metrics in sorted(alpha_div.items()):
        print(f"\n  Örnek: {sid}")
        for k, v in metrics.items():
            print(f"    {k}: {v}")


if __name__ == '__main__':
    main()
