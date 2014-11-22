import subprocess

def RealignerTargetCreator(gatk,dedupbams,reference,thread):
    """
    This function creates interval files for realigning.
    Input is deduplicated sorted bam files. reference is 
    fasta file.
    """
    interval_files = []
    cmd = ''
    for dedupbam in dedupbams:  #file name is name.dedup.bam
        interval = dedupbam[:-9] + 'interval.list'
        interval_files.append(interval)
        singleCmd =  ('java -jar {gatk} -T RealignerTargetCreator '
               '-R {ref_fa} -I {dedup} -o {output} -nt {thread}').format(
                gatk=gatk,ref_fa=reference,dedup=dedupbam,output=interval,
                thread=thread)
        cmd = cmd + singleCmd + ' && '
    subprocess.call(cmd[:-3],shell=True)
    return interval_files

def IndelRealigner(gatk,dedupbams,reference,intervals):
    """
    This function realigns the deduped bam file to intervals
    reference is fasta file, target is target interval file.
    """
    realigned_files = []
    cmd = ''
    for dedupbam,interval in zip(dedupbams,intervals):
        realign = dedupbam[:-9] + 'reali.bam'
        realigned_files.append(realign)
        cmd = cmd + ('java -jar {gatk} -T IndelRealigner -R {ref_fa} '
               '-I {input} -targetIntervals {target} '
               '-o {output} & ').format(gatk=gatk,ref_fa=reference,
                input=dedupbam,target=interval,output=realign)
    subprocess.call(cmd[:-3],shell=True)
    return realigned_files

def HaplotypeCaller_DNA_VCF(gatk,recal_files,reference,thread):
    """
    this function use HaplotypeCaller to call the variant
    """
    vcf_files = []
    for recal in recal_files:
        vcf = recal[:-9] + 'raw.vcf'
        vcf_files.append(vcf)
        cmd = ('java -jar {gatk} -T HaplotypeCaller -R {ref_fa} '
               '-I {input} -nct {thread} --genotyping_mode DISCOVERY -stand_emit_conf 15 ' 
               '-stand_call_conf 30 -o {output}').format(gatk=gatk,
                ref_fa=reference,input=recal,output=vcf,thread='2')
        subprocess.call(cmd,shell=True)
    return vcf_files
    
def HaplotypeCaller_DNA_gVCF(gatk,recal_files,reference,thread):
    """
    this function does calling variant and stores the result 
    into the gVCF file.
    """
    vcf_files = []
    cmd = ''
    for recal in recal_files:
        vcf = recal[:-9] + 'raw.g.vcf'
        vcf_files.append(vcf)
        cmd = cmd + ('java -jar {gatk} -T HaplotypeCaller -R {ref_fa} '
               '-I {input} --emitRefConfidence GVCF ' 
               '--variant_index_type LINEAR --variant_index_parameter 128000 ' 
               '-o {output} & ').format(gatk=gatk,
                ref_fa=reference,input=recal,output=vcf)
    subprocess.call(cmd[:-3],shell=True)
    return vcf_files

def JointGenotype(gatk,gvcf_files,reference,samplename,thread):
    """
    this function combine all the gVCF files into one
    """
    output = samplename + '.raw.g.vcf'
    vcf = ''
    for gvcf in gvcf_files:  # use for loop to generate a set of --variant 
        vcf = vcf + '--variant ' + gvcf + ' '
    cmd = ('java -Xmx100g -jar {gatk} -R {ref_fa} -T GenotypeGVCFs {vcf}'
           '-o {output} -nt {thread}').format(gatk=gatk,ref_fa=reference,
            vcf=vcf,output=output,thread=thread)
    subprocess.call(cmd,shell=True)
    return output

def SelectVariants(gatk,joint_variant,reference,extract_type,thread):
    """
    this function can extract either SNP or indel from the
    vcf file
    """
    output = joint_variant[:-5] + extract_type.lower() + '.vcf'  # sample.raw.snp.vcf
    cmd = ('java -jar {gatk} -T SelectVariants -R {ref_fa} -V {input} '
           '-selectType {type} -o {output} -nt {thread}').format(gatk=gatk, 
            ref_fa=reference,input=joint_variant,type=extract_type,
            output=output,thread=thread)
    subprocess.call(cmd,shell=True)
    return output

def snpHardFilter(gatk,snp_file,reference):
    """
    this function will filter the snps, output a gold standard snp database
    """
    output = snp_file[:-11] + 'gold.snp.vcf'
    filtercmd = ('QD < 3.0 || FS > 50.0 || MQ < 50.0 || HaplotypeScore > 10.0 '
                 '|| MappingQualityRankSum < -12.5 || ReadPosRankSum < -8.0')
    filtercmd = """'{filter}'""".format(filter=filtercmd)
    filtername = """'snp_filter'"""
    cmd = ('java -jar {gatk} -T VariantFiltration -R {ref_fa} -V {input} '
           '--filterExpression {filter} --filterName {filtername} '
           '-o {output}').format(gatk=gatk,ref_fa=reference,input=snp_file,
                filter = filtercmd,filtername=filtername,output=output)
    subprocess.call(cmd,shell=True)
    return output

def indelHardFilter(gatk,indel_file,reference):
    """
    this function filter the indels,output a gold standard indel database
    """
    output = indel_file[:-13] + 'gold.indel.vcf'
    filtercmd = ("QD < 2.0 || FS > 200.0 || ReadPosRankSum < -15.0")
    filtercmd = """'{filter}'""".format(filter=filtercmd)
    filtername = """'indel_filter'"""
    cmd = ('java -jar {gatk} -T VariantFiltration -R {ref_fa} -V {input} '
           '--filterExpression {filter} --filterName {filtername} '
           '-o {output}').format(gatk=gatk,ref_fa=reference,input=indel_file,
            filter = filtercmd,filtername=filtername,output=output)
    subprocess.call(cmd,shell=True)
    return output

def HardFilter(gatk,raw_gvcf,reference,thread):
    """
    this function will apply artificial filter for snp and indel
    """
    raw_snp = SelectVariants(gatk,raw_gvcf,reference,'SNP',thread)
    raw_indel= SelectVariants(gatk,raw_gvcf,reference,'INDEL',thread)
    gold_snp = snpHardFilter(gatk,raw_snp,reference)
    gold_indel = indelHardFilter(gatk,raw_indel,reference)
    return [gold_snp,gold_indel]

def BaseRecalibrator(gatk,realignbams,reference,gold_snp,gold_indel,roundNum,thread):
    """
    this function do base recalibration
    """
    # 1. Analyze patterns of covariation in the sequence dataset
    cmd = ''
    recal_tables = []
    for realign in realignbams:
        table = realign[:-9] + 'recal.table'
        recal_tables.append(table)
        cmd = cmd + ('java -jar {gatk} -T BaseRecalibrator -R {ref_fa} '
           '-I {realignbam} -knownSites {snp} -knownSites {indel} '
           '-o {output} -nct {thread} && ').format(gatk=gatk,ref_fa=reference,
            realignbam=realign,snp=gold_snp,indel=gold_indel,
            output=table,thread=thread)
    subprocess.call(cmd[:-3],shell=True)
    
    # 2. Do a second pass to analyze covariation remaining after recalibration
    cmd = ''
    recal_post_tables = []
    for realign,table in zip(realignbams,recal_tables):
        post_table = realign[:-9] + 'post_recal.table'
        recal_post_tables.append(post_table)
        cmd = cmd + ('java -jar {gatk} -T BaseRecalibrator -R {ref_fa} '
           '-I {realignbam} -knownSites {snp} -knownSites {indel} -BQSR {table} '
           '-o {output} -nct {thread} && ').format(gatk=gatk,
            ref_fa=reference,realignbam=realign,snp=gold_snp,
            indel=gold_indel,output=post_table,table=table,
            thread=thread)
    subprocess.call(cmd[:-3],shell=True)
    
    # 3. Generate before/after plots
    cmd = ''
    for table,post_table in zip(recal_tables,recal_post_tables):
        plot = table[:-11] + str(roundNum) + 'recal_plots.pdf'
        cmd = cmd + ('java -jar {gatk} -T AnalyzeCovariates -R {ref_fa} '
                     '-before {table} -after {post_table} -plots {output} && ').format(
                    gatk=gatk,ref_fa=reference,table=table,post_table=post_table,
                    output=plot)
    subprocess.call(cmd[:-3],shell=True)
    
    # 4. Apply the recalibration to your sequence data
    cmd = ''
    recal_bams = []
    for realign,table in zip(realignbams,recal_tables):
        recal_bam = realign[:-9] + 'recal.bam'
        recal_bams.append(recal_bam)
        cmd = cmd + ('java -jar {gatk} -T PrintReads -R {ref_fa} '
        '-I {input} -BQSR {table} -o {output} -nct {thread} && ').format(gatk=gatk,
        ref_fa=reference,input=realign,table=table,output=recal_bam,
        thread=thread)
    subprocess.call(cmd[:-3],shell=True)
    return recal_bams
  
def VQSR(gatk,raw_gvcf,gold_snp,gold_indel,reference,thread):
    """
    this file does variant qulity score recalibration and filter snps and 
    indels automatically.
    """
    # 1. build recalibration model for snp
    recal_snp = raw_gvcf[:-9] + 'SNP.recal'
    tranch_snp = raw_gvcf[:-9] + 'SNP.tranches'
    rplot_snp = raw_gvcf[:-9] + 'SNP_plots.R'
    cmd = ('java -jar {gatk} -T VariantRecalibrator -R {ref_fa} -input {input} '
           '-resource:dbsnp,known=false,training=true,truth=true,prior=10.0 '
           '{gold} -an DP -an QD -an FS -an MQRankSum -an ReadPosRankSum '
           '-mode SNP -tranche 100.0 -tranche 99.9 -tranche 99.0 -tranche 90.0 '
           '-recalFile {recal} -tranchesFile {tranch} -rscriptFile {rplot} '
           '-nt {thread}').format(
            gatk=gatk,ref_fa=reference,input=raw_gvcf,gold=gold_snp,
            recal=recal_snp,tranch=tranch_snp,rplot=rplot_snp,
            thread=thread)
    subprocess.call(cmd,shell=True)
    
    # 2. apply the desired level of recalibration to the SNPs in the call set
    recalSnp_rawIndel = raw_gvcf[:-9] + 'recalSnp_rawIndel.vcf'
    cmd = ('java -jar {gatk} -T ApplyRecalibration -R {ref_fa} -input {input} '
           '-mode SNP --ts_filter_level 99.0 -recalFile {recal} '
           '-tranchesFile {tranch} -o {output}').format(gatk=gatk,ref_fa=reference,
            input=raw_gvcf,recal=recal_snp,tranch=tranch_snp,
            output=recalSnp_rawIndel)
    subprocess.call(cmd,shell=True)
    
    # 3. build recalibration model for indel
    recal_indel = raw_gvcf[:-9] + 'indel.recal'
    tranch_indel = raw_gvcf[:-9] + 'indel.tranches'
    rplot_indel = raw_gvcf[:-9] + 'indel_plots.R'
    cmd = ('java -jar {gatk} -T VariantRecalibrator -R {ref_fa} -input {input} '
           '-resource:indel,known=false,training=true,truth=true,prior=10.0 '
           '{gold} -an DP -an FS -an MQRankSum -an ReadPosRankSum '
           '-mode INDEL -tranche 100.0 -tranche 99.9 -tranche 99.0 -tranche 90.0 '
           '-recalFile {recal} -tranchesFile {tranch} -rscriptFile {rplot} ' 
           '-nt {thread}').format(
            gatk=gatk,ref_fa=reference,input=raw_gvcf,gold=gold_indel,
            recal=recal_indel,tranch=tranch_indel,rplot=rplot_indel,
            thread=thread)
    subprocess.call(cmd,shell=True)
    
    # 4. apply the desired level of recalibration to the Indels in the call set
    recal_variant = raw_gvcf[:-9] + 'recal_variant.vcf'
    cmd = ('java -jar {gatk} -T ApplyRecalibration -R {ref_fa} -input {input} '
           '-mode INDEL --ts_filter_level 99.0 -recalFile {recal} '
           '-tranchesFile {tranch} -o {output}').format(gatk=gatk,ref_fa=reference,
            input=recalSnp_rawIndel,recal=recal_indel,tranch=tranch_indel,
            output=recal_variant)
    subprocess.call(cmd,shell=True)
    return recal_variant

##***************** RNA specific **************************
def splitN(gatk,dedupBams,ref_fa):
    """
    This function splits reads due to wrong splicing by STAR
    """
    splitBams = []
    cmd = ''
    for dedup in dedupBams:
        split = dedup[:-9] + 'split.bam'
        splitBams.append(split)
        cmd = cmd + ('java -jar {gatk} -T SplitNCigarReads -R {ref_fa} '
                     '-I {input} -o {output} -rf ReassignOneMappingQuality '
                     '-RMQF 255 -RMQT 60 -U ALLOW_N_CIGAR_READS && ').format(
                    gatk=gatk,ref_fa=ref_fa,input=dedup,output=split)
    subprocess.call(cmd[:-3],shell=True)
    return splitBams

def HaplotypeCaller_RNA_VCF(gatk,recal_files,reference):
    """
    This function calls variants in RNAseq
    """
    vcf_files = []
    cmd = ''
    for recal in recal_files:
        vcf = recal[:-9] + 'vcf'
        vcf_files.append(vcf)
        cmd = cmd + ('java -jar {gatk} -T HaplotypeCaller -R {ref_fa} '
        '-I {input} -dontUseSoftClippedBases ' 
        '-stand_call_conf 20.0 -stand_emit_conf 20.0 -o {output} '
        '& ').format(
        gatk=gatk,ref_fa=reference,input=recal,output=vcf)
    subprocess.call(cmd[:-3],shell=True)
    return vcf_files

def RNA_Vari_Filter(gatk,vcfs,ref_fa):
    """
    This function filter out the results of the vari call 
    """
    filter_files = []
    cmd = ''
    for vcf in vcfs:
        filter_vcf = vcf[:-3] + 'filter.vcf'
        filter_files.append(filter_vcf)
        FS = """'FS > 30.0'"""
        QD = """'QD < 2.0'"""
        cmd = cmd + ('java -jar {gatk} -T VariantFiltration -R {ref_fa} '
                     '-V {input} -window 35 -cluster 3 -filterName FS '
                     '-filter {FS} -filterName QD -filter {QD} '
                     '-o {output} && ').format(gatk=gatk,ref_fa=ref_fa,
                    input=vcf,FS=FS,QD=QD,output=filter_vcf)
    subprocess.call(cmd[:-3],shell=True)
    return filter_files

def RNA_BaseRecalibrator(gatk,realignbams,reference,gold_vcfs,roundNum,thread):
    """
    this function do base recalibration
    """
    # 1. Analyze patterns of covariation in the sequence dataset
    cmd = ''
    recal_tables = []
    for realign,gold in zip(realignbams,gold_vcfs):
        table = realign[:-9] + 'recal.table'
        recal_tables.append(table)
        cmd = cmd + ('java -jar {gatk} -T BaseRecalibrator -R {ref_fa} '
           '-I {realignbam} -knownSites {gold} '
           '-o {output} -nct {thread} && ').format(gatk=gatk,ref_fa=reference,
            realignbam=realign,gold=gold,
            output=table,thread=thread)
    subprocess.call(cmd[:-3],shell=True)
    
    # 2. Do a second pass to analyze covariation remaining after recalibration
    cmd = ''
    recal_post_tables = []
    for realign,table,gold in zip(realignbams,recal_tables,gold_vcfs):
        post_table = realign[:-9] + 'post_recal.table'
        recal_post_tables.append(post_table)
        cmd = cmd + ('java -jar {gatk} -T BaseRecalibrator -R {ref_fa} '
           '-I {realignbam} -knownSites {gold} -BQSR {table} '
           '-o {output} -nct {thread} && ').format(gatk=gatk,
            ref_fa=reference,realignbam=realign,gold=gold,
            output=post_table,table=table,
            thread=thread)
    subprocess.call(cmd[:-3],shell=True)
    
    # 3. Generate before/after plots
    cmd = ''
    for table,post_table in zip(recal_tables,recal_post_tables):
        plot = table[:-11] + str(roundNum) + 'recal_plots.pdf'
        cmd = cmd + ('java -jar {gatk} -T AnalyzeCovariates -R {ref_fa} '
                     '-before {table} -after {post_table} -plots {output} && ').format(
                    gatk=gatk,ref_fa=reference,table=table,post_table=post_table,
                    output=plot)
    subprocess.call(cmd[:-3],shell=True)
    
    # 4. Apply the recalibration to your sequence data
    cmd = ''
    recal_bams = []
    for realign,table in zip(realignbams,recal_tables):
        recal_bam = realign[:-9] + 'recal.bam'
        recal_bams.append(recal_bam)
        cmd = cmd + ('java -jar {gatk} -T PrintReads -R {ref_fa} '
        '-I {input} -BQSR {table} -o {output} -nct {thread} && ').format(gatk=gatk,
        ref_fa=reference,input=realign,table=table,output=recal_bam,
        thread=thread)
    subprocess.call(cmd[:-3],shell=True)
    return recal_bams
    