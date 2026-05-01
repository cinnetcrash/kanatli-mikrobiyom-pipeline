# Kanatlı Mikrobiyom Pipeline

**Nanopore metagenomik sekans verilerinden mikrobiyom kompozisyonu ve diversite analizi**

[![Nextflow](https://img.shields.io/badge/nextflow%20DSL2-%E2%89%A525.0.0-23aa62.svg)](https://www.nextflow.io/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## İçindekiler

- [Genel Bakış](#genel-bakış)
- [Pipeline Akışı](#pipeline-akışı)
- [Sistem Gereksinimleri](#sistem-gereksinimleri)
- [Kurulum](#kurulum)
- [Veritabanı Hazırlığı](#veritabanı-hazırlığı)
- [Kullanım](#kullanım)
- [Girdi Formatı](#girdi-formatı)
- [Çıktılar](#çıktılar)
- [Parametreler](#parametreler)
- [Sorun Giderme](#sorun-giderme)

---

## Genel Bakış

Bu pipeline, Oxford Nanopore Technology (ONT) cihazlarından elde edilen ham barcode klasörlerini alıp taksonomik sınıflandırma, bolluk tahmini ve istatistiksel analize kadar tüm adımları otomatik olarak yürütür.

**Kullanım alanı:** Kanatlı (Gallus gallus) bağırsak mikrobiyom çalışmaları. Konak DNA'sı otomatik temizlenir.  
**Birden fazla örnek** aynı anda paralel çalıştırılır.

---

## Pipeline Akışı

```
Barcode klasörü (*.fastq dosyaları)
         │
         ▼
   ┌─────────────┐
   │  CAT_FASTQ  │  Klasördeki tüm fastq'ları tek dosyada birleştirir
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │ NANOSTAT    │  Ham okuma kalite istatistikleri (okuma sayısı, N50, medyan kalite)
   │ (ham)       │
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │   CHOPPER   │  Kalite filtresi: Q ≥ 8, uzunluk ≥ 500 bp
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │ NANOSTAT    │  Filtre sonrası okuma kalite kontrolü
   │ (filtreli)  │
   └──────┬──────┘
          │
          ▼
   ┌──────────────────┐
   │  HOST_REMOVAL    │  Gallus gallus genomuna hizalama → konak okumaları çıkar
   │  Minimap2 + SAM  │  (map-ont preset)
   └────────┬─────────┘
            │
            ▼
   ┌─────────────────────────────────┐
   │           KRAKEN2               │  Taksonomik sınıflandırma
   │  PlusPF 30 GB  --memory-mapping │  (bacteria, archaea, viral, fungi, protozoa)
   └──────────────┬──────────────────┘
                  │
                  ▼
   ┌──────────────────────┐
   │        BRACKEN       │  Tür / Cins / Aile düzeyi bolluk tahmini
   │  + KrakenTools alpha │  Shannon, Simpson, Pielou, Chao1
   └──────────┬───────────┘
              │
              ▼
   ┌─────────────────────────┐
   │   ABUNDANCE_ANALYSIS    │  Bolluk grafikleri, ısı haritası,
   │   (Python + matplotlib) │  Bray-Curtis beta diversite, HTML rapor
   └──────────┬──────────────┘
              │
              ▼
   ┌──────────────┐
   │   MULTIQC    │  Tüm QC çıktılarını tek raporda birleştirir
   └──────────────┘
```

---

## Sistem Gereksinimleri

| Bileşen | Minimum | Önerilen |
|---------|---------|----------|
| CPU | 8 çekirdek | 16 çekirdek |
| RAM | 16 GB | 32 GB |
| Disk | 100 GB boş | 300 GB boş (SSD) |
| İşletim Sistemi | Linux (Ubuntu 20.04+) | Ubuntu 22.04 |

> **Not:** Kraken2 30 GB veritabanı `--memory-mapping` ile çalıştırılır; veritabanı RAM'e yüklenmez, diskten okunur. Bu nedenle veritabanının **SSD üzerinde** olması çalışma süresini önemli ölçüde kısaltır.

---

## Kurulum

### 1. Bağımlılıklar

**Docker:**
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
```

**Nextflow** (conda ile):
```bash
conda create -n nextflow -c bioconda nextflow
conda activate nextflow
nextflow -version
```

**Nextflow** (doğrudan kurulum):
```bash
curl -s https://get.nextflow.io | bash
sudo mv nextflow /usr/local/bin/
```

### 2. Pipeline'ı İndir

```bash
git clone https://github.com/cinnetcrash/kanatli-mikrobiyom-pipeline.git
cd kanatli-mikrobiyom-pipeline
```

### 3. Stats Docker İmajını Derle

```bash
docker build -t kanatli-mikrobiyom-stats:1.0 -f docker/stats/Dockerfile .
```

---

## Veritabanı Hazırlığı

`setup_databases.sh` betiği Gallus gallus referans genomunu ve Kraken2 PlusPF veritabanını otomatik indirir.

```bash
bash setup_databases.sh /hedef/dizin 16
# Örnek: bash setup_databases.sh /data/databases 16
```

Bu betik şunları yapar:
1. **Gallus gallus genomu** (~312 MB) — NCBI RefSeq GCF_016699485.2
2. **Kraken2 PlusPF veritabanı** (~30 GB) — bacteria, archaea, viral, fungi, protozoa

> ⏱ **Tahmini süre:** İndirme hızına bağlı olarak 1–4 saat.  
> Bağlantı kesilirse `wget -c` ile kaldığı yerden devam eder.

İndirme bittikten sonra arşivi açın:
```bash
tar -xzf /data/databases/kraken2_plusPF/k2_pluspf.tar.gz \
    -C /data/databases/kraken2_plusPF/
rm /data/databases/kraken2_plusPF/k2_pluspf.tar.gz
```

---

## Kullanım

### Hızlı Başlangıç

```bash
bash run_pipeline.sh \
    -i samplesheet.csv \
    -g /data/databases/gallus_gallus/gallus_gallus.fa.gz \
    -k /data/databases/kraken2_plusPF \
    -o results \
    -t 16
```

### Tüm Seçenekler

```
bash run_pipeline.sh [seçenekler]

Zorunlu:
  -i, --input         Samplesheet CSV dosyası (sample_id, barcode_dir)
  -g, --host-genome   Gallus gallus referans genomu (.fa veya .fa.gz)
  -k, --kraken2-db    Kraken2 veritabanı dizini

Opsiyonel:
  -o, --outdir        Çıktı dizini (varsayılan: results)
  -t, --threads       Thread sayısı (varsayılan: 8)
  -q, --min-quality   Minimum Phred kalitesi (varsayılan: 8)
  -l, --min-length    Minimum okuma uzunluğu bp (varsayılan: 500)
  -b, --bracken-len   Bracken okuma uzunluğu (varsayılan: 150)
  -r, --resume        Kaldığı yerden devam et
  -n, --dry-run       İş akışını kontrol et, çalıştırma
  -h, --help          Yardım mesajını göster
```

### Nextflow ile Doğrudan Çalıştırma

```bash
conda activate nextflow

nextflow run main.nf \
    -profile docker \
    --input samplesheet.csv \
    --host_genome /data/databases/gallus_gallus/gallus_gallus.fa.gz \
    --kraken2_db /data/databases/kraken2_plusPF \
    --outdir results \
    --threads 16

# Kaldığı yerden devam etmek için:
nextflow run main.nf -resume [diğer parametreler...]
```

---

## Girdi Formatı

### Samplesheet (CSV)

Her satır bir barcode klasörünü temsil eder. Klasör içindeki tüm `.fastq` ve `.fastq.gz` dosyaları otomatik olarak birleştirilir.

```csv
sample_id,barcode_dir
S1,/data/sekans/barcode01_S1/barcode01_S1
S2,/data/sekans/barcode02_S2/barcode02_S2
S3,/data/sekans/barcode03_S3/barcode03_S3
```

| Sütun | Açıklama |
|-------|----------|
| `sample_id` | Benzersiz örnek adı (çıktı dosyalarında kullanılır) |
| `barcode_dir` | Barcode klasörünün tam yolu (fastq dosyaları içermeli) |

### Barcode Klasörü Yapısı

```
barcode02_S2/
├── PBA41881_pass_barcode02_xxx_13.fastq
├── PBA57530_pass_barcode02_xxx_17.fastq
├── PBA57530_pass_barcode02_xxx_18.fastq
└── ...
```

---

## Çıktılar

```
results/
├── concat/              # Birleştirilmiş fastq.gz dosyaları
├── qc/
│   ├── nanostat/        # Ham ve filtreli okuma istatistikleri
│   ├── host_removal/    # Konak DNA temizleme istatistikleri
│   └── kraken2/         # Kraken2 log dosyaları
├── filtered/            # Chopper sonrası filtreli okumalar
├── host_removed/        # Konak DNA temizlenmiş okumalar
├── kraken2/             # Kraken2 rapor ve çıktı dosyaları
├── bracken/             # Tür/cins/aile düzeyi bolluk dosyaları
├── diversity/           # Alfa diversite metrikleri
├── statistics/
│   ├── abundance_analysis/
│   │   ├── abundance_table_species.csv    # Tür bolluk tablosu
│   │   ├── abundance_table_genus.csv      # Cins bolluk tablosu
│   │   ├── alpha_diversity_summary.csv    # Diversite özet tablosu
│   │   ├── alpha_diversity_summary.xlsx   # Excel formatı
│   │   ├── analysis_summary.json         # Makine-okunabilir özet
│   │   ├── *_species_top30_bar.png       # Tür bolluk grafikleri
│   │   ├── *_genus_top30_bar.png         # Cins bolluk grafikleri
│   │   ├── all_samples_*_stacked_bar.png # Yığılmış bolluk grafiği
│   │   ├── all_samples_*_heatmap.png     # Isı haritası
│   │   ├── beta_diversity_bray_curtis.png # Beta diversite + dendrogram
│   │   ├── alpha_diversity_comparison.png # Örnekler arası karşılaştırma
│   │   ├── *_phylum_donut.png            # Phylum dağılımı
│   │   └── kraken2_classification_rates.png
│   └── report/
│       └── mikrobiyom_raporu.html        # İnteraktif HTML raporu
├── multiqc/
│   └── multiqc_report.html              # Birleşik QC raporu
└── pipeline_info/
    ├── report.html     # Nextflow çalışma raporu
    ├── timeline.html   # Proses zaman çizelgesi
    └── trace.txt       # Kaynak kullanım detayları
```

---

## Parametreler

| Parametre | Varsayılan | Açıklama |
|-----------|-----------|----------|
| `--input` | — | Samplesheet CSV yolu |
| `--host_genome` | — | Gallus gallus referans genomu |
| `--kraken2_db` | — | Kraken2 veritabanı dizini |
| `--outdir` | `results` | Çıktı dizini |
| `--threads` | `8` | Thread sayısı |
| `--min_quality` | `8` | Minimum Phred kalitesi (Chopper) |
| `--min_length` | `500` | Minimum okuma uzunluğu bp (Chopper) |
| `--max_length` | `0` | Maksimum okuma uzunluğu (0 = sınırsız) |
| `--bracken_readlen` | `150` | Bracken okuma uzunluğu parametresi |
| `--bracken_threshold` | `10` | Bracken minimum okuma eşiği |
| `--kraken2_confidence` | `0.0` | Kraken2 güven skoru (0.0–1.0) |
| `--top_taxa` | `30` | Grafiklerde gösterilecek maksimum taksa sayısı |

---

## Docker İmajları

| Adım | İmaj |
|------|------|
| NanoStat | `staphb/nanostat:1.6.0` |
| Chopper | `quay.io/biocontainers/chopper:0.8.0--hd83dbe4_0` |
| Host Removal | `quay.io/biocontainers/mulled-v2-ac74a7f02cebcfbc0119723439a5b0ab73e1a7e8` |
| Kraken2 | `staphb/kraken2:2.1.3` |
| Bracken | `staphb/bracken:2.9` |
| MultiQC | `quay.io/biocontainers/multiqc:1.21--pyhdfd78af_0` |
| İstatistik | `kanatli-mikrobiyom-stats:1.0` (yerel derleme) |

---

## Sorun Giderme

**Kraken2 bellek hatası:**  
`--memory-mapping` varsayılan olarak aktiftir. Veritabanının SSD üzerinde olduğundan emin olun.

**Çalışma yarıda kesilirse:**  
`-r` veya `--resume` ile kaldığı yerden devam eder:
```bash
bash run_pipeline.sh -i samplesheet.csv -g gallus.fa.gz -k kraken2_db/ -r
```

**Barcode klasöründe fastq bulunamıyor:**  
Klasörün `.fastq` veya `.fastq.gz` uzantılı dosyalar içerdiğini kontrol edin:
```bash
find /barcode/klasoru -maxdepth 1 -name "*.fastq" -o -name "*.fastq.gz"
```

**Stats Docker imajı bulunamıyor:**  
```bash
docker build -t kanatli-mikrobiyom-stats:1.0 -f docker/stats/Dockerfile .
```

---

## Araçlar ve Referanslar

- **Nextflow** — Di Tommaso et al., *Nature Biotechnology* (2017)
- **Kraken2** — Wood et al., *Genome Biology* (2019)
- **Bracken** — Lu et al., *PeerJ Computer Science* (2017)
- **Minimap2** — Li, *Bioinformatics* (2018)
- **Chopper** — De Coster & Rademakers, *Bioinformatics* (2023)
- **NanoStat** — De Coster et al., *Bioinformatics* (2018)
- **MultiQC** — Ewels et al., *Bioinformatics* (2016)

---

## Lisans

MIT License — Detaylar için `LICENSE` dosyasına bakın.
