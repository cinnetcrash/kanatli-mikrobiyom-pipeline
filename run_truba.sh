#!/usr/bin/env bash
# ─── TRUBA (TÜBİTAK HPC) Çalıştırma Scripti ─────────────────────────────────
# Kullanım: bash run_truba.sh -i samplesheet.csv -g gallus.fa.gz -k kraken2_db/

set -uo pipefail

INPUT=""
HOST_GENOME=""
KRAKEN2_DB=""
OUTDIR="results"
ACCOUNT=""

usage() {
cat << EOF
Kullanım: $(basename "$0") [seçenekler]

Zorunlu:
  -i, --input       Samplesheet CSV (sample_id,barcode_dir)
  -g, --host-genome Gallus gallus genomu
  -k, --kraken2-db  Kraken2 veritabanı dizini
  -a, --account     TRUBA proje hesabı (ör: k2-123456)

Opsiyonel:
  -o, --outdir      Çıktı dizini (varsayılan: results)
  -r, --resume      Kaldığı yerden devam et
EOF
}

RESUME_FLAG=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--input)       INPUT="$2";       shift 2 ;;
        -g|--host-genome) HOST_GENOME="$2"; shift 2 ;;
        -k|--kraken2-db)  KRAKEN2_DB="$2";  shift 2 ;;
        -a|--account)     ACCOUNT="$2";     shift 2 ;;
        -o|--outdir)      OUTDIR="$2";      shift 2 ;;
        -r|--resume)      RESUME_FLAG="-resume"; shift ;;
        -h|--help)        usage; exit 0 ;;
        *) echo "Bilinmeyen argüman: $1"; exit 1 ;;
    esac
done

if [[ -z "$INPUT" || -z "$HOST_GENOME" || -z "$KRAKEN2_DB" ]]; then
    echo "HATA: -i, -g ve -k zorunlu."; usage; exit 1
fi

# TRUBA'da Nextflow modülü yükle
module load nextflow 2>/dev/null || true

PIPELINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# clusterOptions içine hesap bilgisini ekle
CLUSTER_OPT=""
[[ -n "$ACCOUNT" ]] && CLUSTER_OPT="--clusterOptions '--account=${ACCOUNT}'"

echo "TRUBA pipeline başlatılıyor..."
echo "  Samplesheet : $INPUT"
echo "  Çıktı       : $OUTDIR"
echo ""

nextflow run "${PIPELINE_DIR}/main.nf" \
    -profile truba \
    $RESUME_FLAG \
    --input          "$INPUT" \
    --host_genome    "$HOST_GENOME" \
    --kraken2_db     "$KRAKEN2_DB" \
    --outdir         "$OUTDIR" \
    --kraken2_memory_mapping false \
    --threads        16 \
    $CLUSTER_OPT \
    -with-report  "${OUTDIR}/pipeline_info/report.html" \
    -with-timeline "${OUTDIR}/pipeline_info/timeline.html"
