// NanoStat - Nanopore okuma kalite istatistikleri
process NANOSTAT {
    tag "${sample_id} (${stage})"
    label 'process_low'

    container 'quay.io/biocontainers/nanostat:1.6.0--pyhdfd78af_0'

    publishDir "${params.outdir}/qc/nanostat", mode: 'copy'

    input:
    tuple val(sample_id), path(fastq)
    val stage

    output:
    tuple val(sample_id), path("${sample_id}_${stage}_nanostat.txt"), emit: txt

    script:
    """
    NanoStat \\
        --fastq ${fastq} \\
        --outdir . \\
        --name ${sample_id}_${stage}_nanostat.txt \\
        --threads ${task.cpus} \\
        2>&1 | tee nanostat.log
    """
}
