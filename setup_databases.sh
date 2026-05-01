#!/usr/bin/env bash
# ─── Veritabanı ve Referans Dosyaları Kurulum Scripti ──────────────────────
# Gallus gallus referans genomu ve Kraken2 PlusPF veritabanını indirir.
# Çalıştırmadan önce: bash setup_databases.sh

set -uo pipefail

DB_DIR="${1:-/data/databases}"
THREADS="${2:-8}"

echo "=============================================="
echo "  Kanatlı Mikrobiyom Pipeline - DB Kurulumu  "
echo "=============================================="
echo "Hedef dizin: ${DB_DIR}"
echo "Thread sayısı: ${THREADS}"
echo ""

mkdir -p "${DB_DIR}/gallus_gallus" "${DB_DIR}/kraken2_plusPF"

# ─── 1) Gallus gallus Referans Genomu ────────────────────────────────────────
echo "[1/3] Gallus gallus referans genomu indiriliyor..."
GALLUS_DIR="${DB_DIR}/gallus_gallus"
GALLUS_GENOME="${GALLUS_DIR}/GCF_016699485.2_bGalGal1.mat.broiler.GRCg7b_genomic.fna.gz"

if [ ! -f "${GALLUS_DIR}/gallus_gallus.fa.gz" ]; then
    # NCBI RefSeq - Gallus gallus bGalGal1 (GCF_016699485.2)
    wget -c \
        "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/016/699/485/GCF_016699485.2_bGalGal1.mat.broiler.GRCg7b/GCF_016699485.2_bGalGal1.mat.broiler.GRCg7b_genomic.fna.gz" \
        -O "${GALLUS_DIR}/gallus_gallus.fa.gz"
    echo "  Genom indirildi: ${GALLUS_DIR}/gallus_gallus.fa.gz"
else
    echo "  Gallus gallus genomu zaten mevcut, atlanıyor."
fi

# Minimap2 indeksi oluştur (pipeline çalışırken otomatik oluşturulur, burada opsiyonel)
if [ ! -f "${GALLUS_DIR}/gallus_gallus.mmi" ]; then
    echo "  Minimap2 indeksi oluşturuluyor (map-ont preset)..."
    if docker run --rm \
        -v "${GALLUS_DIR}:/ref" \
        "staphb/minimap2:2.26" \
        minimap2 -d /ref/gallus_gallus.mmi /ref/gallus_gallus.fa.gz -t "${THREADS}"; then
        echo "  Minimap2 indeksi oluşturuldu."
    else
        echo "  UYARI: Minimap2 indeksi oluşturulamadı — pipeline çalışırken otomatik oluşturulacak."
    fi
else
    echo "  Minimap2 indeksi zaten mevcut, atlanıyor."
fi

# ─── 2) Kraken2 PlusPF Veritabanı (30 GB) ────────────────────────────────────
echo ""
echo "[2/3] Kraken2 PlusPF veritabanı indiriliyor (~30 GB)..."
KRAKEN_DIR="${DB_DIR}/kraken2_plusPF"

# Güncel PlusPF veritabanı (bacteria, archaea, viral, plasmid, human, fungi, protozoa)
# Kaynak: https://benlangmead.github.io/aws-indexes/k2
K2_URL="https://genome-idx.s3.amazonaws.com/kraken/k2_pluspf_20240904.tar.gz"

if [ ! -f "${KRAKEN_DIR}/hash.k2d" ]; then
    echo "  PlusPF veritabanı indiriliyor (~30 GB, bu işlem uzun sürebilir)..."
    # aria2c varsa çok daha hızlı indirir (paralel bağlantı)
    if command -v aria2c &>/dev/null; then
        aria2c -x 16 -s 16 -d "${KRAKEN_DIR}" -o k2_pluspf.tar.gz "${K2_URL}"
    else
        wget -c "${K2_URL}" -O "${KRAKEN_DIR}/k2_pluspf.tar.gz" --progress=bar:force
    fi

    echo "  Veritabanı açılıyor..."
    tar -xzf "${KRAKEN_DIR}/k2_pluspf.tar.gz" -C "${KRAKEN_DIR}"
    rm -f "${KRAKEN_DIR}/k2_pluspf.tar.gz"
    echo "  Kraken2 veritabanı hazır."
else
    echo "  Kraken2 veritabanı zaten mevcut, atlanıyor."
fi

# ─── 3) Bracken tabloları kontrolü ───────────────────────────────────────────
echo ""
echo "[3/3] Bracken kmer tabloları kontrol ediliyor..."
# PlusPF içinde Bracken tabloları (*.kmer_distrib) zaten hazır gelir
if ls "${KRAKEN_DIR}"/*.kmer_distrib &>/dev/null; then
    echo "  Bracken tabloları mevcut:"
    ls "${KRAKEN_DIR}"/*.kmer_distrib | xargs -I{} basename {}
else
    echo "  UYARI: Bracken tabloları bulunamadı — veritabanı indirmesini kontrol edin."
fi

echo ""
echo "=============================================="
echo "  Kurulum tamamlandı!"
echo "  Gallus gallus : ${GALLUS_DIR}/gallus_gallus.fa.gz"
echo "  Kraken2 DB    : ${KRAKEN_DIR}/"
echo ""
echo "  Pipeline çalıştırmak için:"
echo "  bash run_pipeline.sh \\"
echo "    --host_genome ${GALLUS_DIR}/gallus_gallus.fa.gz \\"
echo "    --kraken2_db ${KRAKEN_DIR}"
echo "=============================================="
