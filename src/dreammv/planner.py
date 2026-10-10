"""
DreamMV Story Planner

音楽を解析してMVの設計図を作る。
"""

class StoryPlanner:
    def create_plan(self, song_length):
        scene_count = max(1, int((song_length + 9) // 10))

        scenes = []

        for i in range(scene_count):
            start = i * 10
            end = min(start + 10, song_length)


            scenes.append({
                "id": i + 1,
                "start": start,
                "end": end,
                "prompt": "A cinematic scene"
        })


        return {
            "length": song_length,
            "scene_count": scene_count,
            "status": "planning",
            "scenes": scenes
        }