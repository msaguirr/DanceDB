class Dance:

    levels = {      "absolute beginner"   : 0,
                    "beginner"            : 2,
                    "improver"            : 4,
                    "intermediate"        : 6,
                    "advanced"            : 8 }

    keywords = {    "easy"      : -1, 
                    "low"       : -1,
                    "high"      :  1,
                    "plus"      :  1,
                    "phrased"   :  1 }

    categories = {  "learn next"                :   "blue",
                    "learn soon"                :   "green",
                    "learn later"               :   "yellow",
                    "old dances to practice"    :   "purple",
                    "old dances I didn't know"  :   "pink" }

    def __init__(self):
        self.name
        self.level
        self.keywords
        self.counts
        self.walls
        self.tags = 0
        self.restarts = 0

        self.songs
        self.stepsheet_link
        self.choreographer

        self.priority
        self.known
        self.category
        self.difficulty_score
        self.play_frequency

    def set_name(self, name):
        self.name = name

    def set_level(self, level):
        self.level = level

    def set_difficulty_score(self):
        keyword_score = 0
        for key in keywords:
            #if keyword contained in self.keywords ? add to sum
            if key in self.keywords:
                keyword_score += keywords[key]
        score = levels[self.level] + keyword_score

    def add_song(self, song):
        self.songs.append(song)


