"""
DreamMV Story Planner

音楽を解析してMVの設計図を作る。
"""

class StoryPlanner:
    def create_plan(self, song_length):
        scene_count = max(1, (song_length + 9) // 10)

        return {
            "length": song_length,
            "scene_count": scene_count,
            "status": "planning"
        }