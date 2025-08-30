import classifierAccuracyAnalysis
import classifierAccuracyAnalysis_noVote
import classifierAccuracyAnalysis_onlyVote
import classifierAccuracyAnalysis_human
import pandas as pd
import numpy as np


# rawStats: list[dict[{"total_games", int}, {"single_match", int}, {"exact_match", int}]] = []
# rawStats.append()
# print(rawStats)

classifierAccuracyAnalysis.removeAnalysis()

""" 
# 0631 - 0665
transcripts = classifierAccuracyAnalysis.prepareTranscripts("0635")
for transcript in transcripts:
    print(transcript + "\n\n\n" + "BIG BREAK" + "\n\n\n")
print (len(transcripts)) """

""" transcripts = classifierAccuracyAnalysis_noVote.prepareTranscripts("0635")
for transcript in transcripts:
    print(transcript + "\n\n\n" + "BIG BREAK" + "\n\n\n")
print (len(transcripts)) """

""" transcripts = classifierAccuracyAnalysis_onlyVote.prepareTranscripts("0635")
for transcript in transcripts:
    print(transcript + "\n\n\n" + "BIG BREAK" + "\n\n\n")
print (len(transcripts)) """

""" transcripts = classifierAccuracyAnalysis_human.prepareTranscripts("0714")
for transcript in transcripts:
    print(transcript + "\n\n\n" + "BIG BREAK" + "\n\n\n")
print (len(transcripts)) """

# print(classifierAccuracyAnalysis_human.getMafiaNames("0714"))

""" from numbers import Number
template = "hi my name i{}s"
dayNumber = 5
print(template.format(dayNumber)) """

# classifierAccuracyAnalysis_human.analyzeAccuracy()

""" df = pd.read_csv("games\\0714\\info.csv", encoding="utf-8")
df_numpy = df.to_numpy()
# print(df_numpy)

for i, row in df.iterrows():
    contents = row['contents']
    if "Phase Change to Daytime" in contents:
        print(df['contents'][i]) """