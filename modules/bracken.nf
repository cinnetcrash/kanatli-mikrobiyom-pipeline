// Bracken - Tür ve cins düzeyinde bolluk tahmini + KrakenTools diversite
process BRACKEN {
    tag "${sample_id}"
    label 'process_medium'

    container 'staphb/bracken:2.9'

    publishDir "${params.outdir}/bracken",     mode: 'copy', pattern: "*.bracken"
    publishDir "${params.outdir}/bracken",     mode: 'copy', pattern: "*_bracken_*.txt"
    publishDir "${params.outdir}/diversity",   mode: 'copy', pattern: "*_diversity.txt"

    input:
    tuple val(sample_id), path(kraken2_report)
    path  kraken2_db

    output:
    tuple val(sample_id), path("${sample_id}_species.bracken"),  emit: species
    tuple val(sample_id), path("${sample_id}_genus.bracken"),    emit: genus
    tuple val(sample_id), path("${sample_id}_family.bracken"),   emit: family
    path "${sample_id}_diversity.txt",                           emit: diversity

    script:
    """
    # Tür düzeyi (Species)
    bracken \\
        -d ${kraken2_db} \\
        -i ${kraken2_report} \\
        -o ${sample_id}_species.bracken \\
        -w ${sample_id}_bracken_species.report \\
        -r ${params.bracken_readlen} \\
        -l S \\
        -t ${params.bracken_threshold}

    # Cins düzeyi (Genus)
    bracken \\
        -d ${kraken2_db} \\
        -i ${kraken2_report} \\
        -o ${sample_id}_genus.bracken \\
        -w ${sample_id}_bracken_genus.report \\
        -r ${params.bracken_readlen} \\
        -l G \\
        -t ${params.bracken_threshold}

    # Aile düzeyi (Family)
    bracken \\
        -d ${kraken2_db} \\
        -i ${kraken2_report} \\
        -o ${sample_id}_family.bracken \\
        -w ${sample_id}_bracken_family.report \\
        -r ${params.bracken_readlen} \\
        -l F \\
        -t ${params.bracken_threshold}

    # KrakenTools ile alfa diversite hesaplama
    echo "Örnek: ${sample_id}" > ${sample_id}_diversity.txt
    echo "=========================" >> ${sample_id}_diversity.txt
    echo "" >> ${sample_id}_diversity.txt

    for METRIC in Sh BP Si Ni Fi; do
        METRIC_NAME=""
        case \$METRIC in
            Sh) METRIC_NAME="Shannon Entropisi" ;;
            BP) METRIC_NAME="Berger-Parker İndeksi" ;;
            Si) METRIC_NAME="Simpson İndeksi" ;;
            Ni) METRIC_NAME="Zenginlik (Gözlemlenen Tür)" ;;
            Fi) METRIC_NAME="Fisher Alfa" ;;
        esac
        echo -n "\${METRIC_NAME}: " >> ${sample_id}_diversity.txt
        alpha_diversity.py \\
            -f ${sample_id}_species.bracken \\
            -a \$METRIC >> ${sample_id}_diversity.txt 2>/dev/null || echo "N/A" >> ${sample_id}_diversity.txt
    done
    """
}
