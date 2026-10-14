"""
DreamMV Story Planner

音楽を解析してMVの設計図を作る。
"""

PROMPT_STAGES = [
    {
        "until_scene": 3,
        "prompt": "A quiet night sky filled with distant stars, cinematic anime style"
    },
    {
        "until_scene": 6,
        "prompt": "A magical journey beneath glowing stars, cinematic anime style"
    },
    {
        "until_scene": None,
        "prompt": "A radiant star illuminating the horizon, hopeful cinematic anime style"
    }
]


class StoryPlanner:
    def get_prompt(self, scene_index):
        scene_number = scene_index + 1

        for stage in PROMPT_STAGES:
            if stage["until_scene"] is None or scene_number <= stage["until_scene"]:
                return stage["prompt"]

        return PROMPT_STAGES[-1]["prompt"]

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