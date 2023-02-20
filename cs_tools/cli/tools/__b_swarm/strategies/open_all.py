import random

from horde.delay import between
from horde import task

from .. import zombie


class ScopedOpenAllZombie(zombie.ThoughtSpotZombie):
    task_delay = between(1)

    def draw_down_content_pool(self, *, content_type: str):
        allowed = self.horde.shared_state.all_guids
        filtered = [content for content in self.my_content[content_type] if content["id"] in allowed]
        return random.choice(filtered)

    @task(weight=0.2)
    async def visit_random_answer(self) -> None:
        answer = self.get_random_worksheet_dependent(content_type="answers")
        await self.v1_answer(guid=answer["id"])

    @task(weight=0.8)
    async def visit_random_liveboard(self) -> None:
        liveboard = self.get_random_worksheet_dependent(content_type="liveboards")
        await self.v1_liveboard(guid=liveboard["id"])
