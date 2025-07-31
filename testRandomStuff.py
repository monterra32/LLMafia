import classifierAccuracyAnalysis

transcripts = classifierAccuracyAnalysis.prepareTranscript("0140")
for transcript in transcripts:
    print(transcript + "\n" + "BIG BREAK")