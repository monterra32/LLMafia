


from colorsys import TWO_THIRD


TWO_LINES_QUESTION_NORMAL = "How do the lengths of the blue and orange line compare?"

def get_two_lines_question(num_people):
    if num_people == "0":
        return TWO_LINES_QUESTION_NORMAL
    else:
        return f"How do the lengths of the blue and orange line compare? {num_people} people have previously said that they are the same length."