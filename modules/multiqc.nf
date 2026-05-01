// MultiQC - Tüm QC çıktılarını birleştir
process MULTIQC {
    label 'process_low'

    container 'quay.io/biocontainers/multiqc:1.21--pyhdfd78af_0'

    publishDir "${params.outdir}/multiqc", mode: 'copy'

    input:
    path qc_files

    output:
    path "multiqc_report.html", emit: report
    path "multiqc_data/",       emit: data

    script:
    """
    multiqc \\
        --force \\
        --title "Kanatlı Mikrobiyom QC Raporu" \\
        --comment "Nanopore sekans verileri - Mikrobiyom analizi" \\
        . \\
        -o .
    """
}
