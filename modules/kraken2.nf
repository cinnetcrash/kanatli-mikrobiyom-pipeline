// Kraken2 - Taksonomik sınıflandırma (30 GB PlusPF, memory-mapping ile 16GB RAM'de çalışır)
process KRAKEN2 {
    tag "${sample_id}"
    label 'process_high_memory'

    container 'staphb/kraken2:2.1.3'

    publishDir "${params.outdir}/kraken2",      mode: 'copy', pattern: "*.report"
    publishDir "${params.outdir}/kraken2",      mode: 'copy', pattern: "*.output.gz"
    publishDir "${params.outdir}/qc/kraken2",   mode: 'copy', pattern: "*.log"

    input:
    tuple val(sample_id), path(fastq)
    path  kraken2_db

    output:
    tuple val(sample_id), path("${sample_id}_kraken2.report"),    emit: report
    tuple val(sample_id), path("${sample_id}_kraken2.output.gz"), emit: output
    path "${sample_id}_kraken2.log",                               emit: log

    script:
    """
    kraken2 \\
        --db ${kraken2_db} \\
        --memory-mapping \\
        --threads ${task.cpus} \\
        --report ${sample_id}_kraken2.report \\
        --report-minimizer-data \\
        --confidence ${params.kraken2_confidence} \\
        --output >(gzip > ${sample_id}_kraken2.output.gz) \\
        --gzip-compressed \\
        ${fastq} \\
        2>&1 | tee ${sample_id}_kraken2.log

    # Sınıflandırma özeti
    echo "=== Sınıflandırma Özeti ===" >> ${sample_id}_kraken2.log
    grep "sequences classified"   ${sample_id}_kraken2.log || true
    grep "sequences unclassified" ${sample_id}_kraken2.log || true
    """
}
