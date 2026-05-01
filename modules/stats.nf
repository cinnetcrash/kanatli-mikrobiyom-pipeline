// İstatistiksel Analiz - Bolluk, diversite, karşılaştırmalı grafikler
process ABUNDANCE_ANALYSIS {
    label 'process_medium'

    container 'kanatli-mikrobiyom-stats:1.0'

    publishDir "${params.outdir}/statistics",  mode: 'copy'

    input:
    path species_files
    path genus_files
    path kraken_reports

    output:
    path "abundance_analysis/",  emit: results
    path "report/",              emit: report

    script:
    """
    mkdir -p abundance_analysis report

    python /scripts/abundance_analysis.py \\
        --species-dir   ./ \\
        --genus-dir     ./ \\
        --kraken-dir    ./ \\
        --outdir        abundance_analysis/ \\
        --top-taxa      ${params.top_taxa} \\
        --threads       ${task.cpus}

    python /scripts/generate_html_report.py \\
        --analysis-dir  abundance_analysis/ \\
        --outdir        report/
    """
}
