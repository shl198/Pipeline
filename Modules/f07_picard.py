import subprocess

def read_group(ID,sample,platform,library,platunit):
    return ('@RG\\tID:'+ID+'\\tSM:'+sample+'\\tPL:'+platform+'\\tLB:'+library
            +'\\tPU:'+platunit)
    #@RG\\tID:chosgroup1\\tSM:sample1\\tPL:illumina\\tLB:lib1\\tPU:unit1
def sam2sortbam(picard,samfiles):
    """
    this function change samfile to sorted bam file
    """
    SortSam = picard + '/' + 'SortSam.jar'
    sorted_files = []
    for sam in samfiles:
        sort_bam = sam[:-3] + 'sort.bam'
        sorted_files.append(sort_bam)
        cmd = ('java -jar {SortSam} INPUT={input} OUTPUT={output} '
               'SORT_ORDER=coordinate').format(SortSam=SortSam,
                input=sam,output=sort_bam)
        subprocess.call(cmd,shell=True)
    return sorted_files

def markduplicates(picard,sortBams):
    """
    this function mark duplicates of the sorted bam file
    """
    mark = picard + '/' + 'MarkDuplicates.jar'
    dedup_files = []
    cmd = ''
    for bam in sortBams:
        dedup = bam[:-8] + 'dedup.bam'
        dedup_files.append(dedup)
        cmd = cmd + ('java -jar {mark} I={input} O={output} CREATE_INDEX=true '
        'METRICS_FILE=metrics.txt MAX_RECORDS_IN_RAM=8000000 '
        'MAX_FILE_HANDLES_FOR_READ_ENDS_MAP=1000 '
        'VALIDATION_STRINGENCY=LENIENT && ').format(mark=mark,input=bam,
        output=dedup)
    subprocess.call(cmd[:-3],shell=True)
    return dedup_files

def addReadGroup(picard,sortBamFiles,readgroups):
    """
    This function add readgroup to a list of samfiles
    """
    add = picard + '/' + 'AddOrReplaceReadGroups.jar'
    sortBams = []
    cmd = ''
    for sam,rg in zip(sortBamFiles,readgroups):
        sortbam = sam[:-3] + 'sort.bam'
        sortBams.append(sortbam)
        readgroup = rg.split('\\t')
        ID = readgroup[1][3:-1]
        SM = readgroup[2][3:-1]
        PL = readgroup[3][3:-1]
        LB = readgroup[4][3:-1]
        PU = readgroup[5][3:]
        cmd = cmd + ('java -jar {addGp} I={input} O={sortbam} '
                     'RGID={ID} RGSM={SM} RGPL={PL} RGLB={LB} RGPU={PU} & ').format(
                    addGp=add,input=sam,sortbam=sortbam,ID=ID,SM=SM,PL=PL,LB=LB,
                    PU=PU)
    subprocess.call(cmd[:-3],shell=True)
    # the file name in sortBams is filename.sort.sort.bam, need to change to filename.sort.bam
    final_sort_bams = []
    for bam in sortBams:
        finalSortBam = bam[:-13] + 'sort.bam'
        final_sort_bams.append(finalSortBam)
        renameCmd = ('mv {sortBam} {finalSortBam}').format(sortBam=bam,finalSortBam=finalSortBam)
        subprocess.call(renameCmd,shell=True)
    
    return final_sort_bams    