"""
DreamMV Story Planner

音楽を解析してMVの設計図を作る。
"""

class StoryPlanner:
    def get_prompt(self, scene_index):
        if scene_index < 3:
            return "A quiet night sky filled with distant stars, cinematic anime style"
        elif scene_index < 6:
            return "A magical journey beneath glowing stars, cinematic anime style"
        else:
            return "A radiant star illuminating the horizon, hopeful cinematic anime style"

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
                "prompt": self.get_prompt(i)
            })

        return {
            "length": song_length,
            "scene_count": scene_count,
            "status": "planning",
            "scenes": scenes
        }