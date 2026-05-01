// CAT_FASTQ - Barcode klasöründeki tüm fastq dosyalarını birleştir
process CAT_FASTQ {
    tag "${sample_id}"
    label 'process_low'

    container 'ubuntu:22.04'

    publishDir "${params.outdir}/concat", mode: 'copy', pattern: "*.fastq.gz"

    input:
    tuple val(sample_id), path(barcode_dir)

    output:
    tuple val(sample_id), path("${sample_id}_concat.fastq.gz"), emit: fastq
    path "${sample_id}_concat.log",                              emit: log

    script:
    """
    N_FASTQ=\$(find -L ${barcode_dir} -maxdepth 1 \\( -name "*.fastq" -o -name "*.fastq.gz" \\) | wc -l)

    if [ "\$N_FASTQ" -eq 0 ]; then
        echo "HATA: ${barcode_dir} içinde fastq dosyası bulunamadı!" >&2
        exit 1
    fi

    echo "Birleştiriliyor: \$N_FASTQ dosya → ${sample_id}_concat.fastq.gz" | tee ${sample_id}_concat.log

    # .fastq.gz ve .fastq dosyalarını ayrı ayrı işle
    (
        find -L ${barcode_dir} -maxdepth 1 -name "*.fastq.gz" | sort | xargs -r zcat
        find -L ${barcode_dir} -maxdepth 1 -name "*.fastq"    | sort | xargs -r cat
    ) | gzip > ${sample_id}_concat.fastq.gz

    TOTAL_READS=\$(zcat ${sample_id}_concat.fastq.gz | awk 'NR%4==1' | wc -l)
    echo "Toplam okuma: \$TOTAL_READS" | tee -a ${sample_id}_concat.log
    """
}
