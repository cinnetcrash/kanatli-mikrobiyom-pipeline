// Chopper - Nanopore okumalarını kalite ve uzunluğa göre filtrele
process CHOPPER {
    tag "${sample_id}"
    label 'process_medium'

    container 'quay.io/biocontainers/chopper:0.7.0--hdcf5f25_0'

    publishDir "${params.outdir}/filtered", mode: 'copy',
        pattern: "*.fastq.gz"

    input:
    tuple val(sample_id), path(fastq)

    output:
    tuple val(sample_id), path("${sample_id}_filtered.fastq.gz"), emit: fastq
    path "${sample_id}_chopper.log",                               emit: log

    script:
    def max_len_opt = params.max_length > 0 ? "--maxlength ${params.max_length}" : ""
    """
    gunzip -c ${fastq} 2>/dev/null || cat ${fastq} | \\
        chopper \\
            --quality ${params.min_quality} \\
            --minlength ${params.min_length} \\
            ${max_len_opt} \\
            --threads ${task.cpus} \\
        2>${sample_id}_chopper.log | \\
        gzip > ${sample_id}_filtered.fastq.gz

    echo "Filtre sonrası okuma sayısı: \$(zcat ${sample_id}_filtered.fastq.gz | wc -l | awk '{print \$1/4}')" >> ${sample_id}_chopper.log
    """
}
