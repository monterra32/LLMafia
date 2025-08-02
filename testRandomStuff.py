import classifierAccuracyAnalysis


# rawStats: list[dict[{"total_games", int}, {"single_match", int}, {"exact_match", int}]] = []
# rawStats.append()
# print(rawStats)




transcripts = classifierAccuracyAnalysis.prepareTranscripts("0631")
for transcript in transcripts:
    print(transcript + "\n" + "BIG BREAK")