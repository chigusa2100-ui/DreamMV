"""
DreamMV Story Planner

音楽を解析してMVの設計図を作る。
"""


PROMPT_STAGES = [
    {
        "until_scene": 3,
        "name": "星降る夜",
        "prompt": "A quiet night sky filled with distant stars, cinematic anime style"
    },
    {
        "until_scene": 6,
        "name": "星の旅",
        "prompt": "A magical journey beneath glowing stars, cinematic anime style"
    },
    {
        "until_scene": None,
        "name": "夜明けの光",
        "prompt": "A radiant star illuminating the horizon, hopeful cinematic anime style"
    }
]

class StoryPlanner:
    def get_scene_stage(self, scene_index):
        scene_number = scene_index + 1

        for stage in PROMPT_STAGES:
            if stage["until_scene"] is None or scene_number <= stage["until_scene"]:
                return stage

        return PROMPT_STAGES[-1]

    def create_plan(self, song_length):
        scene_count = max(1, int((song_length + 9) // 10))

        scenes = []

        for i in range(scene_count):
            start = i * 10
            end = min(start + 10, song_length)
            stage = self.get_scene_stage(i)

            scenes.append({
                "id": i + 1,
                "start": start,
                "end": end,
                "name": stage["name"],
                "prompt": stage["prompt"]
            })

        return {
            "length": song_length,
            "scene_count": scene_count,
            "status": "planning",
            "scenes": scenes
        }