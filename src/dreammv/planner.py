"""
DreamMV Story Planner

音楽を解析してMVの設計図を作る。
"""

PROMPT_STAGES = [
    {
        "until_scene": 3,
        "name": "星降る夜",
        "description": "静かな夜空に星々が輝き、物語が始まる。",
        "prompt": "A quiet night sky filled with distant stars, cinematic anime style"
    },
    {
        "until_scene": 6,
        "name": "星の旅",
        "description": "主人公が星明かりに導かれ、幻想的な旅へ踏み出す。",
        "prompt": "A magical journey beneath glowing stars, cinematic anime style"
    },
    {
        "until_scene": None,
        "name": "夜明けの光",
        "description": "輝く星が地平線を照らし、希望に満ちた結末を迎える。",
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
               "description": stage["description"],
               "prompt": stage["prompt"]
        })
        return {
            "length": song_length,
            "scene_count": scene_count,
            "status": "planning",
            "scenes": scenes
        }