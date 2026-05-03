nextflow.enable.dsl = 2

// ─── Parametre Tanımları ────────────────────────────────────────────────────
params.input              = null          // CSV: sample_id,barcode_dir
params.host_genome        = null          // Gallus gallus referans genomu (.fa/.fa.gz)
params.kraken2_db         = null          // Kraken2 veritabanı dizini (30 GB PlusPF)
params.outdir             = 'results'
params.min_quality        = 8             // Chopper minimum Phred kalitesi
params.min_length         = 500           // Chopper minimum okuma uzunluğu (bp)
params.max_length         = 0             // 0 = limit yok
params.bracken_readlen    = 150           // Bracken okuma uzunluğu (veritabanı ile eşleşmeli)
params.bracken_threshold  = 10            // Minimum okuma sayısı eşiği
params.kraken2_confidence = 0.0           // Kraken2 güven skoru (0.0-1.0)
params.top_taxa           = 30            // Bolluk grafiklerinde gösterilecek taksa sayısı
params.threads            = 8

// ─── Modüller ───────────────────────────────────────────────────────────────
include { CAT_FASTQ                      } from './modules/cat_fastq'
include { NANOSTAT as NANOSTAT_RAW      } from './modules/nanostat'
include { CHOPPER                        } from './modules/chopper'
include { NANOSTAT as NANOSTAT_FILTERED } from './modules/nanostat'
include { HOST_REMOVAL                   } from './modules/host_removal'
include { KRAKEN2                        } from './modules/kraken2'
include { BRACKEN                        } from './modules/bracken'
include { ABUNDANCE_ANALYSIS             } from './modules/stats'
include { MULTIQC                        } from './modules/multiqc'

// ─── Yardımcı Fonksiyonlar ──────────────────────────────────────────────────
def validateParams() {
    if (!params.input)       exit 1, "HATA: --input parametresi zorunlu (ör: samplesheet.csv)"
    if (!params.host_genome) exit 1, "HATA: --host_genome parametresi zorunlu (Gallus gallus .fa)"
    if (!params.kraken2_db)  exit 1, "HATA: --kraken2_db parametresi zorunlu (Kraken2 DB dizini)"
}

// ─── Ana İş Akışı ───────────────────────────────────────────────────────────
workflow {
    validateParams()

    log.info """
    ╔══════════════════════════════════════════════════════════╗
    ║   Kanatlı Mikrobiyom Analiz Pipeline - Nanopore DSL2    ║
    ╚══════════════════════════════════════════════════════════╝
    Girdi samplesheet : ${params.input}
    Konak genomu      : ${params.host_genome}
    Kraken2 DB        : ${params.kraken2_db}
    Çıktı dizini      : ${params.outdir}
    Min kalite (Q)    : ${params.min_quality}
    Min uzunluk (bp)  : ${params.min_length}
    Thread sayısı     : ${params.threads}
    """.stripIndent()

    // Samplesheet okuma — her satır bir barcode klasörüne işaret eder
    ch_samples = Channel
        .fromPath(params.input, checkIfExists: true)
        .splitCsv(header: true, sep: ',', strip: true)
        .map { row ->
            if (!row.sample_id || !row.barcode_dir)
                error "Samplesheet hatası: 'sample_id' ve 'barcode_dir' sütunları zorunlu"
            def bdir = file(row.barcode_dir, checkIfExists: true)
            [ row.sample_id.trim(), bdir ]
        }

    ch_host_genome = file(params.host_genome, checkIfExists: true)
    ch_kraken2_db  = file(params.kraken2_db,  checkIfExists: true)

    // 1) Barcode klasörünü tek fastq.gz'ye birleştir
    CAT_FASTQ(ch_samples)

    // 2) Ham okuma QC
    NANOSTAT_RAW(CAT_FASTQ.out.fastq, 'raw')

    // 3) Kalite filtresi
    CHOPPER(CAT_FASTQ.out.fastq)

    // 4) Filtre sonrası QC
    NANOSTAT_FILTERED(CHOPPER.out.fastq, 'filtered')

    // 5) Konak DNA temizliği
    HOST_REMOVAL(CHOPPER.out.fastq, ch_host_genome)

    // 6) Kraken2 taksonomik sınıflandırma
    KRAKEN2(HOST_REMOVAL.out.fastq, ch_kraken2_db)

    // 7) Bracken bolluk tahmini
    BRACKEN(KRAKEN2.out.report, ch_kraken2_db)

    // 8) İstatistiksel analiz
    ch_species_reports = BRACKEN.out.species.map { id, f -> f }.collect()
    ch_genus_reports   = BRACKEN.out.genus.map   { id, f -> f }.collect()
    ch_kraken_reports  = KRAKEN2.out.report.map  { id, f -> f }.collect()

    ABUNDANCE_ANALYSIS(ch_species_reports, ch_genus_reports, ch_kraken_reports)

    // 9) MultiQC raporu
    ch_multiqc_files = Channel.empty()
        .mix(NANOSTAT_RAW.out.txt.map     { id, f -> f })
        .mix(NANOSTAT_FILTERED.out.txt.map{ id, f -> f })
        .mix(KRAKEN2.out.report.map       { id, f -> f })
        .collect()

    MULTIQC(ch_multiqc_files)
}

workflow.onComplete {
    log.info """
    ═══════════════════════════════════════════════
    Pipeline tamamlandı!
    Durum   : ${workflow.success ? 'BAŞARILI' : 'BAŞARISIZ'}
    Süre    : ${workflow.duration}
    Çıktılar: ${params.outdir}/
    ═══════════════════════════════════════════════
    """.stripIndent()
}
