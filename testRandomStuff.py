import classifierAccuracyAnalysis
import classifierAccuracyAnalysis_noVote
import classifierAccuracyAnalysis_onlyVote


# rawStats: list[dict[{"total_games", int}, {"single_match", int}, {"exact_match", int}]] = []
# rawStats.append()
# print(rawStats)




""" transcripts = classifierAccuracyAnalysis.prepareTranscripts("0635")
for transcript in transcripts:
    print(transcript + "\n\n\n" + "BIG BREAK" + "\n\n\n")
print (len(transcripts)) """

""" transcripts = classifierAccuracyAnalysis_noVote.prepareTranscripts("0635")
for transcript in transcripts:
    print(transcript + "\n\n\n" + "BIG BREAK" + "\n\n\n")
print (len(transcripts)) """

transcripts = classifierAccuracyAnalysis_onlyVote.prepareTranscripts("0635")
for transcript in transcripts:
    print(transcript + "\n\n\n" + "BIG BREAK" + "\n\n\n")
print (len(transcripts))