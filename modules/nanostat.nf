// NanoStat - Nanopore okuma kalite istatistikleri
process NANOSTAT {
    tag "${sample_id}"
    label 'process_low'

    container 'quay.io/biocontainers/nanostat:1.6.0--pyhdfd78af_0'

    publishDir "${params.outdir}/qc/nanostat", mode: 'copy',
        saveAs: { filename -> "${sample_id}_${filename}" }

    input:
    tuple val(sample_id), path(fastq)

    output:
    tuple val(sample_id), path("nanostat_summary.txt"), emit: txt

    script:
    """
    NanoStat \\
        --fastq ${fastq} \\
        --outdir . \\
        --name nanostat_summary.txt \\
        --threads ${task.cpus} \\
        2>&1 | tee nanostat.log
    """
}
