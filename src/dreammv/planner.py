"""
DreamMV Story Planner

音楽を解析してMVの設計図を作る。
"""

class StoryPlanner:
    def create_plan(self, song_length):
        return {
            "length": song_length,
            "status": "planning"
        }
