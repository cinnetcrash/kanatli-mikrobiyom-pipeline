#!/usr/bin/env bash
# ─── Kanatlı Mikrobiyom Pipeline - Çalıştırma Scripti ─────────────────────
# Kullanım:
#   bash run_pipeline.sh -i samplesheet.csv -g gallus.fa.gz -k kraken2_db/ [seçenekler]
#
# Örnek:
#   bash run_pipeline.sh \
#       -i assets/samplesheet_example.csv \
#       -g /data/databases/gallus_gallus/gallus_gallus.fa.gz \
#       -k /data/databases/kraken2_plusPF \
#       -o results \
#       -t 16

set -euo pipefail

# ─── Varsayılanlar ────────────────────────────────────────────────────────────
INPUT=""
HOST_GENOME=""
KRAKEN2_DB=""
OUTDIR="results"
THREADS=8
MIN_QUALITY=8
MIN_LENGTH=500
BRACKEN_READLEN=150
RESUME=false
DRY_RUN=false
PROFILE="docker"

usage() {
cat << EOF
Kullanım: $(basename "$0") [seçenekler]

Zorunlu:
  -i, --input        Samplesheet CSV dosyası — sütunlar: sample_id,barcode_dir
                     Her satır bir barcode klasörüne işaret eder (içindeki fastq'lar otomatik birleştirilir)
                     Örnek: assets/samplesheet_example.csv
  -g, --host-genome  Gallus gallus referans genomu (.fa veya .fa.gz)
  -k, --kraken2-db   Kraken2 veritabanı dizini

Opsiyonel:
  -o, --outdir       Çıktı dizini (varsayılan: results)
  -t, --threads      Thread sayısı (varsayılan: 8)
  -q, --min-quality  Minimum okuma kalitesi Q (varsayılan: 8)
  -l, --min-length   Minimum okuma uzunluğu bp (varsayılan: 500)
  -b, --bracken-len  Bracken okuma uzunluğu (varsayılan: 150)
  -p, --profile      Nextflow profili: docker|singularity|conda (varsayılan: docker)
  -r, --resume       Kaldığı yerden devam et
  -n, --dry-run      Sadece iş akışını kontrol et, çalıştırma
  -h, --help         Bu yardım mesajını göster

EOF
}

# ─── Argüman Ayrıştırma ───────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--input)        INPUT="$2";          shift 2 ;;
        -g|--host-genome)  HOST_GENOME="$2";    shift 2 ;;
        -k|--kraken2-db)   KRAKEN2_DB="$2";     shift 2 ;;
        -o|--outdir)       OUTDIR="$2";         shift 2 ;;
        -t|--threads)      THREADS="$2";        shift 2 ;;
        -q|--min-quality)  MIN_QUALITY="$2";    shift 2 ;;
        -l|--min-length)   MIN_LENGTH="$2";     shift 2 ;;
        -b|--bracken-len)  BRACKEN_READLEN="$2";shift 2 ;;
        -p|--profile)      PROFILE="$2";        shift 2 ;;
        -r|--resume)       RESUME=true;         shift ;;
        -n|--dry-run)      DRY_RUN=true;        shift ;;
        -h|--help)         usage; exit 0 ;;
        *) echo "Bilinmeyen argüman: $1"; usage; exit 1 ;;
    esac
done

# ─── Doğrulama ────────────────────────────────────────────────────────────────
if [[ -z "$INPUT" || -z "$HOST_GENOME" || -z "$KRAKEN2_DB" ]]; then
    echo "HATA: -i, -g ve -k parametreleri zorunlu."
    usage
    exit 1
fi

# Nextflow'u bul: önce conda env, sonra PATH
NEXTFLOW_CMD=""
if conda run -n nextflow nextflow -version &>/dev/null 2>&1; then
    NEXTFLOW_CMD="conda run -n nextflow nextflow"
elif command -v nextflow &>/dev/null; then
    NEXTFLOW_CMD="nextflow"
else
    echo "HATA: Nextflow bulunamadı."
    echo "  conda env 'nextflow' mevcut değilse: conda create -n nextflow -c bioconda nextflow"
    exit 1
fi
echo "  Nextflow   : $($NEXTFLOW_CMD -version 2>&1 | grep 'version' | head -1 | xargs)"

if [[ "$PROFILE" == "docker" ]] && ! command -v docker &>/dev/null; then
    echo "HATA: Docker bulunamadı veya çalışmıyor."
    exit 1
fi

# ─── Stats Docker İmajını Derle ──────────────────────────────────────────────
STATS_IMAGE="kanatli-mikrobiyom-stats:1.0"
if ! docker image inspect "$STATS_IMAGE" &>/dev/null; then
    echo "Stats Docker imajı derleniyor: ${STATS_IMAGE}..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    docker build \
        -t "$STATS_IMAGE" \
        -f "${SCRIPT_DIR}/docker/stats/Dockerfile" \
        "${SCRIPT_DIR}"
fi

# ─── Nextflow Çalıştır ───────────────────────────────────────────────────────
RESUME_FLAG=""
$RESUME && RESUME_FLAG="-resume"

DRY_FLAG=""
$DRY_RUN && DRY_FLAG="-dry-run"

PIPELINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Kanatlı Mikrobiyom Pipeline Başlatılıyor              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo "  Samplesheet : $INPUT"
echo "  Konak genomu: $HOST_GENOME"
echo "  Kraken2 DB  : $KRAKEN2_DB"
echo "  Çıktı       : $OUTDIR"
echo "  Profil      : $PROFILE"
echo "  Thread      : $THREADS"
echo ""

${NEXTFLOW_CMD} run "${PIPELINE_DIR}/main.nf" \
    -profile "$PROFILE" \
    $RESUME_FLAG \
    $DRY_FLAG \
    --input       "$INPUT" \
    --host_genome "$HOST_GENOME" \
    --kraken2_db  "$KRAKEN2_DB" \
    --outdir      "$OUTDIR" \
    --threads     "$THREADS" \
    --min_quality "$MIN_QUALITY" \
    --min_length  "$MIN_LENGTH" \
    --bracken_readlen "$BRACKEN_READLEN"

echo ""
echo "Pipeline tamamlandı! Çıktılar: ${OUTDIR}/"
echo ""
echo "Önemli çıktı dosyaları:"
echo "  ${OUTDIR}/multiqc/multiqc_report.html    - Kalite raporu"
echo "  ${OUTDIR}/statistics/report/mikrobiyom_raporu.html - Analiz raporu"
echo "  ${OUTDIR}/statistics/abundance_analysis/ - Tablolar ve grafikler"
echo "  ${OUTDIR}/bracken/                        - Bracken çıktıları"
echo "  ${OUTDIR}/kraken2/                        - Kraken2 çıktıları"
