// Host Removal - Gallus gallus konak DNA'sını Minimap2 ile çıkar
process HOST_REMOVAL {
    tag "${sample_id}"
    label 'process_high'

    container 'kanatli-host-removal:1.0'

    publishDir "${params.outdir}/host_removed", mode: 'copy',
        pattern: "*.fastq.gz"
    publishDir "${params.outdir}/qc/host_removal", mode: 'copy',
        pattern: "*.stats"

    input:
    tuple val(sample_id), path(fastq)
    path  host_genome

    output:
    tuple val(sample_id), path("${sample_id}_host_removed.fastq.gz"), emit: fastq
    path "${sample_id}_host_removal.stats",                            emit: stats

    script:
    """
    # Konak genomuna hizala (Nanopore preset: map-ont)
    minimap2 \\
        -ax map-ont \\
        -t ${task.cpus} \\
        --secondary=no \\
        ${host_genome} \\
        ${fastq} \\
        2>${sample_id}_minimap2.log | \\
    samtools view -bS -@ ${task.cpus} | \\
    samtools sort  -@ ${task.cpus} -n -o ${sample_id}_aligned.bam -

    # Hizalanmamış okumaları (konak DNA'sı çıkarılmış) çıkar
    samtools view -@ ${task.cpus} -b -f 4 ${sample_id}_aligned.bam | \\
    samtools fastq -@ ${task.cpus} - | \\
    gzip > ${sample_id}_host_removed.fastq.gz

    # Hizalama istatistikleri
    samtools flagstat -@ ${task.cpus} ${sample_id}_aligned.bam > ${sample_id}_host_removal.stats

    # Özet bilgi
    TOTAL=\$(samtools view -c ${sample_id}_aligned.bam)
    HOST=\$(samtools view  -c -F 4 ${sample_id}_aligned.bam)
    UNMAPPED=\$(samtools view -c -f 4 ${sample_id}_aligned.bam)

    echo "Örnek: ${sample_id}" >> ${sample_id}_host_removal.stats
    echo "Toplam okuma: \$TOTAL" >> ${sample_id}_host_removal.stats
    echo "Konak (Gallus gallus): \$HOST" >> ${sample_id}_host_removal.stats
    echo "Konak-sız okuma: \$UNMAPPED" >> ${sample_id}_host_removal.stats

    rm -f ${sample_id}_aligned.bam
    """
}
